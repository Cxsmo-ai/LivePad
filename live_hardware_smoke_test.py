"""End-to-end TikTok LIVE -> HIDMaestro -> XInput validation."""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from bridge_process import BridgeProcess
from ipc.named_pipe import NamedPipeClient
from runtime import ControllerRuntime
from tiktok_client import TikTokLiveManager
from xinput_probe import connected_states


TEST_COMMENT = "w sprint ads fire right 35"
EXPECTED_ACTIONS = {
    "move_forward",
    "button_l3",
    "left_trigger",
    "right_trigger",
    "look_right",
}


def _is_compound_state(state: dict) -> bool:
    return (
        state["left_trigger"] >= 200
        and state["right_trigger"] >= 200
        and bool(state["buttons"] & 0x0040)
        and state["left_y"] >= 20_000
        and abs(state["right_x"]) >= 5_000
    )


def _is_neutral(state: dict | None) -> bool:
    return state is not None and (
        state["buttons"] == 0
        and state["left_trigger"] == 0
        and state["right_trigger"] == 0
        and abs(state["left_x"]) <= 1024
        and abs(state["left_y"]) <= 1024
        and abs(state["right_x"]) <= 1024
        and abs(state["right_y"]) <= 1024
    )


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _relaunch_elevated() -> bool:
    if os.name != "nt" or ctypes.windll.shell32.IsUserAnAdmin():
        return False
    project_root = Path(__file__).resolve().parent
    parameters = subprocess.list2cmdline([str(Path(__file__).resolve()), *sys.argv[1:]])
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, parameters, str(project_root), 1
    )
    if result <= 32:
        raise OSError(f"Windows elevation request failed with code {result}")
    return True


async def run_test(username: str, timeout_seconds: float) -> dict:
    report: dict = {
        "test": "tiktok-live-to-hidmaestro-to-xinput",
        "username": username.lstrip("@"),
        "expected_comment": TEST_COMMENT,
        "passed": False,
    }
    bridge = BridgeProcess()
    runtime: ControllerRuntime | None = None
    manager = TikTokLiveManager(username)
    connected = asyncio.Event()
    target_finished = asyncio.Event()
    connection: asyncio.Task | None = None
    comments_received = 0
    target_started = False

    def on_connect(_: dict) -> None:
        connected.set()

    async def sample_target(accepted_actions: list[str], started_ns: int) -> None:
        try:
            await asyncio.sleep(0.05)
            active_states = connected_states()
            matching = [state for state in active_states if _is_compound_state(state)]
            report["accepted_actions"] = accepted_actions
            report["active_observation_ms"] = round(
                (time.perf_counter_ns() - started_ns) / 1_000_000, 3
            )
            report["active"] = active_states
            if not matching:
                report["error"] = "compound state was not visible through XInput"
                return

            controller_index = matching[0]["index"]
            report["controller_index"] = controller_index
            runtime.clear()
            await asyncio.sleep(0.10)
            neutral_states = connected_states()
            report["neutral"] = neutral_states
            neutral = next(
                (state for state in neutral_states if state["index"] == controller_index),
                None,
            )
            report["passed"] = (
                set(accepted_actions) == EXPECTED_ACTIONS and _is_neutral(neutral)
            )
            if not report["passed"]:
                report["error"] = "accepted actions or final neutral state did not match"
        except Exception as error:
            report["error"] = f"XInput observation failed: {error}"
        finally:
            target_finished.set()

    def on_comment(event: dict) -> None:
        nonlocal comments_received, target_started
        comments_received += 1
        message = str(event.get("comment", "")).strip().casefold()
        if target_started or message != TEST_COMMENT:
            return
        target_started = True
        started_ns = time.perf_counter_ns()
        result = runtime.handle_comment(event)
        accepted_actions = [command.action for command in result.accepted]
        asyncio.get_running_loop().create_task(
            sample_target(accepted_actions, started_ns)
        )

    manager.on_event("connect", on_connect)
    manager.on_event("comment", on_comment)
    try:
        bridge.launch(mock=False)
        runtime = ControllerRuntime(NamedPipeClient())
        runtime.start()
        report["initial"] = connected_states()

        connect_started = time.perf_counter()
        connection = asyncio.create_task(manager.connect())
        while not connected.is_set() and not connection.done():
            if time.perf_counter() - connect_started > 20:
                raise TimeoutError("TikTok connection was not ready within 20 seconds")
            await asyncio.sleep(0.05)
        if connection.done():
            await connection
            raise RuntimeError("TikTok LIVE disconnected before the test began")
        report["connection_ms"] = round(
            (time.perf_counter() - connect_started) * 1000, 2
        )

        await asyncio.wait_for(target_finished.wait(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        report["error"] = "exact test comment was not received before timeout"
    except Exception as error:
        report["error"] = str(error)
    finally:
        report["comments_received"] = comments_received
        try:
            await manager.disconnect()
        except Exception:
            pass
        if connection is not None and not connection.done():
            try:
                await asyncio.wait_for(connection, timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                connection.cancel()
        if runtime is not None:
            try:
                runtime.close()
            except OSError:
                pass
        bridge.stop()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(__file__).resolve().parent / "live-hardware-report.json",
    )
    args = parser.parse_args()
    if _relaunch_elevated():
        return 0
    report = asyncio.run(run_test(args.username, args.timeout))
    _write_report(args.report, report)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
