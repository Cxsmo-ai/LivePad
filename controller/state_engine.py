"""Timed input leases and deterministic state resolution."""

from dataclasses import dataclass
import math
import time

from chat.parser import Command
from .state import ControllerState


@dataclass(frozen=True, slots=True)
class _Lease:
    control: str
    value: float | str
    expires_ns: int
    owner: str
    sequence: int


@dataclass(frozen=True, slots=True)
class Submission:
    sequence: int
    state: ControllerState


class StateEngine:
    """Accept commands immediately and resolve all active leases together."""

    _axis = {
        "move_forward": ("ly", 1.0),
        "move_backward": ("ly", -1.0),
        "strafe_left": ("lx", -1.0),
        "strafe_right": ("lx", 1.0),
        "look_left": ("rx", -1.0),
        "look_right": ("rx", 1.0),
        "look_up": ("ry", 1.0),
        "look_down": ("ry", -1.0),
    }
    _buttons = {
        "button_a": "a", "button_b": "b", "button_x": "x", "button_y": "y",
        "button_lb": "lb", "button_rb": "rb", "button_l3": "l3", "button_r3": "r3",
        "button_start": "start", "button_back": "back",
    }

    def __init__(self):
        self._leases: dict[tuple[str, str], _Lease] = {}
        self._sequence = 0
        self._last_state = ControllerState()

    def schedule(self, command: Command, owner: str, now_ns: int | None = None) -> int:
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        self._sequence += 1
        if command.action in self._axis:
            control, direction = self._axis[command.action]
            value = direction * command.strength
        elif command.action in ("left_trigger", "right_trigger"):
            control, value = ("lt" if command.action == "left_trigger" else "rt"), command.strength
        elif command.action in self._buttons:
            control, value = "buttons", self._buttons[command.action]
        else:
            raise ValueError(f"unsupported command action: {command.action}")
        # A viewer can refresh an intent but cannot multiply its voting weight by
        # repeating the same command inside the lease window.
        self._leases[(owner, command.action)] = _Lease(
            control, value, now_ns + command.duration_ms * 1_000_000, owner, self._sequence
        )
        return self._sequence

    def resolve(self, now_ns: int | None = None) -> ControllerState:
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        self._leases = {
            key: lease for key, lease in self._leases.items()
            if lease.expires_ns > now_ns
        }
        axes = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0}
        triggers = {"lt": 0.0, "rt": 0.0}
        buttons: set[str] = set()
        for lease in self._leases.values():
            if lease.control in axes:
                axes[lease.control] += float(lease.value)
            elif lease.control in triggers:
                triggers[lease.control] = max(triggers[lease.control], float(lease.value))
            elif lease.control == "buttons":
                buttons.add(str(lease.value))
        movement_magnitude = math.hypot(axes["lx"], axes["ly"])
        if movement_magnitude > 1.0:
            axes["lx"] /= movement_magnitude
            axes["ly"] /= movement_magnitude
        return ControllerState(**axes, **triggers, buttons=frozenset(buttons)).clamped()

    def tick(self, now_ns: int | None = None) -> Submission | None:
        state = self.resolve(now_ns)
        if state == self._last_state:
            return None
        self._last_state = state
        return Submission(self._sequence, state)

    def clear_all(self) -> ControllerState:
        self._leases.clear()
        self._last_state = ControllerState()
        return self._last_state

    @property
    def active_lease_count(self) -> int:
        return len(self._leases)
