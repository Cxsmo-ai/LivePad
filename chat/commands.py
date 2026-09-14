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
             *, allow_strength: bool = False, allow_duration: bool = True) -> dict:
    return {
        "action": action,
        "strength": strength,
        "duration_ms": duration_ms,
        "allow_strength_argument": allow_strength,
        "allow_duration_argument": allow_duration,
        "enabled": True,
    }


DEFAULT_COMMANDS = {
    # Movement (Left Analog Stick: accepts strength % and duration ms)
    "w": _command("move_forward", 1.0, 400, allow_strength=True, allow_duration=True),
    "forward": _command("move_forward", 1.0, 400, allow_strength=True, allow_duration=True),
    "s": _command("move_backward", 1.0, 400, allow_strength=True, allow_duration=True),
    "back": _command("move_backward", 1.0, 400, allow_strength=True, allow_duration=True),
    "backward": _command("move_backward", 1.0, 400, allow_strength=True, allow_duration=True),
    "a": _command("strafe_left", 1.0, 350, allow_strength=True, allow_duration=True),
    "d": _command("strafe_right", 1.0, 350, allow_strength=True, allow_duration=True),

    # Camera / Aiming (Right Analog Stick: accepts strength % and duration ms)
    "left": _command("look_left", 0.4, 150, allow_strength=True, allow_duration=True),
    "right": _command("look_right", 0.4, 150, allow_strength=True, allow_duration=True),
    "up": _command("look_up", 0.4, 150, allow_strength=True, allow_duration=True),
    "down": _command("look_down", 0.4, 150, allow_strength=True, allow_duration=True),

    # Triggers (accept strength % and duration ms)
    "fire": _command("right_trigger", 1.0, 180, allow_strength=True, allow_duration=True),
    "shoot": _command("right_trigger", 1.0, 180, allow_strength=True, allow_duration=True),
    "ads": _command("left_trigger", 1.0, 600, allow_strength=True, allow_duration=True),
    "aim": _command("left_trigger", 1.0, 600, allow_strength=True, allow_duration=True),

    # Face Buttons & Actions (accept custom duration ms)
    "jump": _command("button_a", 1.0, 120, allow_duration=True),
    "crouch": _command("button_b", 1.0, 120, allow_duration=True),
    "slide": _command("button_b", 1.0, 400, allow_duration=True),
    "b": _command("button_b", 1.0, 120, allow_duration=True),
    "reload": _command("button_x", 1.0, 120, allow_duration=True),
    "interact": _command("button_x", 1.0, 800, allow_duration=True),
    "use": _command("button_x", 1.0, 800, allow_duration=True),
    "buy": _command("button_x", 1.0, 800, allow_duration=True),
    "revive": _command("button_x", 1.0, 1500, allow_duration=True),
    "x": _command("button_x", 1.0, 300, allow_duration=True),
    "swap": _command("button_y", 1.0, 120, allow_duration=True),
    "switch": _command("button_y", 1.0, 120, allow_duration=True),
    "y": _command("button_y", 1.0, 120, allow_duration=True),
    "sprint": _command("button_l3", 1.0, 500, allow_duration=True),
    "melee": _command("button_r3", 1.0, 120, allow_duration=True),
    "knife": _command("button_r3", 1.0, 120, allow_duration=True),
    "tac": _command("button_lb", 1.0, 120, allow_duration=True),
    "tactical": _command("button_lb", 1.0, 120, allow_duration=True),
    "nade": _command("button_rb", 1.0, 120, allow_duration=True),
    "grenade": _command("button_rb", 1.0, 120, allow_duration=True),
    "menu": _command("button_start", 1.0, 120, allow_duration=True),
    "view": _command("button_back", 1.0, 120, allow_duration=True),
}
