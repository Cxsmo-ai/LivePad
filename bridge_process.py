"""Launch and supervise the C# HIDMaestro bridge."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


class BridgeProcess:
    def __init__(self, project_root: Path | None = None):
        self.root = project_root or Path(__file__).resolve().parent
        self.process: subprocess.Popen[str] | None = None

    def launch(self, mock: bool = False) -> None:
        if getattr(sys, "frozen", False):
            resource_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            archive = resource_root / "bridge" / "TikForever.HIDMaestro.zip"
            if not archive.exists():
                raise FileNotFoundError(f"packaged bridge archive is missing: {archive}")

            local_app_data = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
            cache_root = local_app_data / "HIDMaestroStreamerEdition" / "bridge"
            executable = cache_root / "TikForever.HIDMaestro.exe"
            version_marker = cache_root / "bridge.version"
            archive_stat = archive.stat()
            archive_signature = f"{archive_stat.st_size}:{archive_stat.st_mtime_ns}"
            cached_signature = (
                version_marker.read_text(encoding="utf-8").strip()
                if version_marker.exists()
                else ""
            )

            if not executable.exists() or cached_signature != archive_signature:
                cache_root.mkdir(parents=True, exist_ok=True)
                temporary_executable = executable.with_suffix(".exe.tmp")
                with zipfile.ZipFile(archive) as package:
                    with package.open("TikForever.HIDMaestro.exe") as source:
                        with temporary_executable.open("wb") as destination:
                            shutil.copyfileobj(source, destination)
                os.replace(temporary_executable, executable)
                version_marker.write_text(archive_signature, encoding="utf-8")

            command = [str(executable)]
            working_directory = executable.parent
        else:
            assembly = self.root / "bridge" / "bin" / "Release" / "net10.0-windows" / "TikForever.HIDMaestro.dll"
            dotnet = self.root / ".dotnet" / "dotnet.exe"
            if not assembly.exists():
                raise FileNotFoundError(f"bridge build is missing: {assembly}")
            if not dotnet.exists():
                raise FileNotFoundError(f"project-local .NET 10 host is missing: {dotnet}")
            command = [str(dotnet), str(assembly)]
            working_directory = assembly.parent
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        if mock:
            command.append("--mock")
        self.process = subprocess.Popen(
            command,
            cwd=working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=flags,
        )

    def failure_details(self) -> str:
        if self.process is None:
            return "bridge was not launched"
        if self.process.poll() is None:
            return "bridge did not open its pipe"
        stdout, stderr = self.process.communicate()
        details = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
        return details or f"bridge exited with code {self.process.returncode}"

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=2)
        self.process = None
