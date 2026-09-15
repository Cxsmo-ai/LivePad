"""Timed input leases and deterministic state resolution."""

from dataclasses import dataclass
import math
import time

from chat.parser import Command
from chat.pad_protocol import PadFrame
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
        "button_guide": "guide",
        "button_dpad_up": "dpad_up", "button_dpad_down": "dpad_down",
        "button_dpad_left": "dpad_left", "button_dpad_right": "dpad_right",
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

    def replace_owner_frame(
        self, frame: PadFrame, owner: str, now_ns: int | None = None
    ) -> int:
        """Atomically replace one viewer's full-state frame leases.

        Held controls use the frame lease. Rising-edge taps are separate short leases so
        a quick press and release between two platform-limited chat sends is not lost.
        """

        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        frame_prefix = "@frame:"
        self._leases = {
            key: lease for key, lease in self._leases.items()
            if not (key[0] == owner and key[1].startswith(frame_prefix))
        }
        self._sequence += 1
        expires_ns = now_ns + frame.lease_ms * 1_000_000

        values = {
            "lx": frame.lx, "ly": frame.ly, "rx": frame.rx, "ry": frame.ry,
            "lt": frame.lt, "rt": frame.rt,
        }
        for control, value in values.items():
            if value:
                self._leases[(owner, f"{frame_prefix}{control}")] = _Lease(
                    control, value, expires_ns, owner, self._sequence
                )
        for button in frame.held_buttons:
            self._leases[(owner, f"{frame_prefix}button:{button}")] = _Lease(
                "buttons", button, expires_ns, owner, self._sequence
            )

        tap_expires_ns = now_ns + 120 * 1_000_000
        for button in frame.tap_buttons - frame.held_buttons:
            tap_key = f"@tap:{frame.session:x}:{frame.sequence:x}:{button}"
            self._leases[(owner, tap_key)] = _Lease(
                "buttons", button, tap_expires_ns, owner, self._sequence
            )
        return self._sequence

    def resolve(self, now_ns: int | None = None) -> ControllerState:
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        self._leases = {
            key: lease for key, lease in self._leases.items()
            if lease.expires_ns > now_ns
        }
        lx = ly = rx = ry = 0.0
        lt = rt = 0.0
        buttons: set[str] = set()
        for lease in self._leases.values():
            if lease.control == "lx":
                lx += float(lease.value)
            elif lease.control == "ly":
                ly += float(lease.value)
            elif lease.control == "rx":
                rx += float(lease.value)
            elif lease.control == "ry":
                ry += float(lease.value)
            elif lease.control == "lt":
                lt = max(lt, float(lease.value))
            elif lease.control == "rt":
                rt = max(rt, float(lease.value))
            elif lease.control == "buttons":
                buttons.add(str(lease.value))
        movement_magnitude = math.hypot(lx, ly)
        if movement_magnitude > 1.0:
            lx /= movement_magnitude
            ly /= movement_magnitude
        return ControllerState(lx, ly, rx, ry, lt, rt, frozenset(buttons)).clamped()

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

    @property
    def next_expiry_ns(self) -> int | None:
        """Return the next lease deadline for event-driven scheduling."""
        if not self._leases:
            return None
        return min(lease.expires_ns for lease in self._leases.values())
