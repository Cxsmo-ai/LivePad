"""End-to-end Python/C# named-pipe smoke and throughput test."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from ipc.named_pipe import NamedPipeClient


def main() -> int:
    root = Path(__file__).resolve().parent
    published = root / "build" / "bridge" / "TikForever.HIDMaestro.exe"
    assembly = root / "bridge" / "bin" / "Release" / "net10.0-windows" / "TikForever.HIDMaestro.dll"
    dotnet = root / ".dotnet" / "dotnet.exe"
    dotnet_command = str(dotnet) if dotnet.exists() else shutil.which("dotnet")
    # Source verification must exercise the assembly just produced by
    # `dotnet build`, never a potentially stale published executable.
    if assembly.exists() and dotnet_command:
        command = [dotnet_command, str(assembly), "--mock"]
        working_directory = assembly.parent
    elif published.exists():
        command = [str(published), "--mock"]
        working_directory = published.parent
    else:
        raise FileNotFoundError(f"Build the bridge first: {assembly}")

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=working_directory,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=flags,
    )
    pipe = NamedPipeClient()
    try:
        for attempt in range(100):
            try:
                pipe.connect()
                break
            except FileNotFoundError:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    raise RuntimeError(f"bridge exited before opening pipe\n{stdout}\n{stderr}")
                time.sleep(0.02)
        else:
            raise TimeoutError("bridge named pipe was not ready within two seconds")

        ready = pipe.receive()
        if ready.get("type") != "ready" or not ready.get("mock"):
            raise RuntimeError(f"unexpected bridge handshake: {ready}")

        pipe.send({"unexpected": True})
        error = pipe.receive()
        if error.get("type") != "error":
            raise RuntimeError(f"bridge did not reject malformed packet: {error}")

        packet = {
            "type": "state", "seq": 0, "lx": 0.0, "ly": 1.0,
            "rx": 0.35, "ry": 0.0, "lt": 1.0, "rt": 1.0,
            "buttons": ["l3"],
        }
        started = time.perf_counter()
        for sequence in range(1, 1001):
            packet["seq"] = sequence
            pipe.send(packet)
        elapsed_ms = (time.perf_counter() - started) * 1000
        pipe.send({"type": "clear", "seq": 1001})
        # Leave the pipe connected but silent long enough to force the C#
        # watchdog's one-shot neutral state.
        time.sleep(1.35)
        pipe.send({"type": "shutdown"})
        pipe.close()
        stdout, stderr = process.communicate(timeout=5)
        neutral_match = re.search(r"neutralizations: (\d+)", stdout)
        if (process.returncode != 0 or "Mock frames received: 1000" not in stdout
                or neutral_match is None or int(neutral_match.group(1)) < 3):
            raise RuntimeError(f"bridge smoke failed ({process.returncode})\n{stdout}\n{stderr}")
        result = {
            "frames": 1000,
            "send_ms": round(elapsed_ms, 3),
            "frames_per_second": round(1000 / max(elapsed_ms / 1000, 1e-9)),
            "bridge_output": stdout.strip().splitlines(),
        }
        print(json.dumps(result, indent=2))
        return 0
    finally:
        pipe.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
