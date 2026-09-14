"""Default chat command profile and supported controller actions."""

from __future__ import annotations


SUPPORTED_ACTIONS = frozenset({
    "move_forward", "move_backward", "strafe_left", "strafe_right",
    "look_left", "look_right", "look_up", "look_down",
    "left_trigger", "right_trigger",
    "button_a", "button_b", "button_x", "button_y",
    "button_lb", "button_rb", "button_l3", "button_r3",
    "button_start", "button_back",
})


def _command(action: str, strength: float, duration_ms: int,
             *, analog_argument: bool = False) -> dict:
    return {
        "action": action,
        "strength": strength,
        "duration_ms": duration_ms,
        "allow_strength_argument": analog_argument,
        "allow_duration_argument": analog_argument,
        "enabled": True,
    }


DEFAULT_COMMANDS = {
    "w": _command("move_forward", 1.0, 400),
    "forward": _command("move_forward", 1.0, 400),
    "s": _command("move_backward", 1.0, 400),
    "back": _command("move_backward", 1.0, 400),
    "backward": _command("move_backward", 1.0, 400),
    "a": _command("strafe_left", 1.0, 350),
    "d": _command("strafe_right", 1.0, 350),
    "left": _command("look_left", 0.4, 150, analog_argument=True),
    "right": _command("look_right", 0.4, 150, analog_argument=True),
    "up": _command("look_up", 0.4, 150, analog_argument=True),
    "down": _command("look_down", 0.4, 150, analog_argument=True),
    "fire": _command("right_trigger", 1.0, 180, analog_argument=True),
    "shoot": _command("right_trigger", 1.0, 180, analog_argument=True),
    "ads": _command("left_trigger", 1.0, 600, analog_argument=True),
    "aim": _command("left_trigger", 1.0, 600, analog_argument=True),
    "jump": _command("button_a", 1.0, 120),
    "crouch": _command("button_b", 1.0, 120),
    "reload": _command("button_x", 1.0, 120),
    "swap": _command("button_y", 1.0, 120),
    "sprint": _command("button_l3", 1.0, 500),
    "melee": _command("button_r3", 1.0, 120),
    "tac": _command("button_lb", 1.0, 120),
    "tactical": _command("button_lb", 1.0, 120),
    "nade": _command("button_rb", 1.0, 120),
    "grenade": _command("button_rb", 1.0, 120),
    "menu": _command("button_start", 1.0, 120),
    "view": _command("button_back", 1.0, 120),
}
