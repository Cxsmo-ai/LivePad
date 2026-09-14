"""Controlled real-HIDMaestro smoke: create, submit, clear, dispose."""

from __future__ import annotations

import json
import time

from bridge_process import BridgeProcess
from ipc.named_pipe import NamedPipeClient
from runtime import ControllerRuntime


def main() -> int:
    bridge = BridgeProcess()
    runtime = ControllerRuntime(NamedPipeClient())
    try:
        bridge.launch(mock=False)
        runtime.start()
        result = runtime.handle_comment({
            "user": "hardware-smoke",
            "user_id": "hardware-smoke",
            "comment": "w sprint ads fire right 35",
        })
        time.sleep(0.1)
        runtime.clear()
        runtime.close()
        bridge.stop()
        print(json.dumps({
            "status": "passed",
            "accepted": [command.action for command in result.accepted],
            "controller": "xbox-360-wired",
            "neutralized": True,
        }, indent=2))
        return 0
    except Exception as error:
        details = bridge.failure_details()
        print(json.dumps({"status": "failed", "error": str(error), "bridge": details}, indent=2))
        return 1
    finally:
        try:
            runtime.clear()
        except Exception:
            pass
        bridge.stop()


if __name__ == "__main__":
    raise SystemExit(main())
