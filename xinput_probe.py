"""Read-only XInput probe used after HIDMaestro creates a virtual pad."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json


class XInputGamepad(ctypes.Structure):
    _fields_ = [
        ("buttons", wintypes.WORD),
        ("left_trigger", ctypes.c_ubyte),
        ("right_trigger", ctypes.c_ubyte),
        ("left_x", ctypes.c_short),
        ("left_y", ctypes.c_short),
        ("right_x", ctypes.c_short),
        ("right_y", ctypes.c_short),
    ]


class XInputState(ctypes.Structure):
    _fields_ = [("packet", wintypes.DWORD), ("gamepad", XInputGamepad)]


def connected_states() -> list[dict]:
    library = ctypes.WinDLL("xinput1_4")
    states = []
    for index in range(4):
        state = XInputState()
        result = library.XInputGetState(index, ctypes.byref(state))
        if result == 0:
            states.append({
                "index": index,
                "packet": state.packet,
                "buttons": state.gamepad.buttons,
                "left_trigger": state.gamepad.left_trigger,
                "right_trigger": state.gamepad.right_trigger,
                "left_x": state.gamepad.left_x,
                "left_y": state.gamepad.left_y,
                "right_x": state.gamepad.right_x,
                "right_y": state.gamepad.right_y,
            })
    return states


if __name__ == "__main__":
    print(json.dumps({"connected_xinput_controllers": connected_states()}, indent=2))
