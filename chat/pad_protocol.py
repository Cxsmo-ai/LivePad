"""Compact, versioned controller snapshots transported entirely through chat."""

from __future__ import annotations

from dataclasses import dataclass
import re


BUTTON_ORDER = (
    "a", "b", "x", "y", "lb", "rb", "l3", "r3",
    "back", "start", "guide", "dpad_up", "dpad_down", "dpad_left", "dpad_right",
)
BUTTON_BITS = {name: 1 << index for index, name in enumerate(BUTTON_ORDER)}
VALID_BUTTON_MASK = (1 << len(BUTTON_ORDER)) - 1

_BASE36 = re.compile(r"^[0-9a-z]+$")
_HEX = re.compile(r"^[0-9a-f]{1,4}$")


@dataclass(frozen=True, slots=True)
class PadFrame:
    """One complete viewer-controller state plus button edges that occurred between frames."""

    session: int
    sequence: int
    lx: float
    ly: float
    rx: float
    ry: float
    lt: float
    rt: float
    held_mask: int
    tap_mask: int
    lease_ms: int

    @property
    def action(self) -> str:
        return "controller_frame"

    @property
    def held_buttons(self) -> frozenset[str]:
        return _decode_buttons(self.held_mask)

    @property
    def tap_buttons(self) -> frozenset[str]:
        return _decode_buttons(self.tap_mask)

    @property
    def is_neutral(self) -> bool:
        return not any((
            self.lx, self.ly, self.rx, self.ry, self.lt, self.rt,
            self.held_mask, self.tap_mask,
        ))


def _decode_buttons(mask: int) -> frozenset[str]:
    return frozenset(name for name, bit in BUTTON_BITS.items() if mask & bit)


def _base36(value: str, *, maximum: int) -> int:
    if not _BASE36.fullmatch(value):
        raise ValueError("invalid base36 field")
    parsed = int(value, 36)
    if not 0 <= parsed <= maximum:
        raise ValueError("base36 field out of range")
    return parsed


def parse_pad_frame(text: str) -> PadFrame | None:
    """Parse ``hm1 session seq axes held taps lease`` or return None if not a frame.

    Axes are signed integer percentages in browser-independent coordinates. Forward and
    right-stick up are positive. Trigger values are unsigned percentages. A leading ``!``
    is accepted because Twitch viewers often use command-prefix conventions.
    """

    candidate = text.strip().casefold()
    if candidate.startswith("!"):
        candidate = candidate[1:]
    if candidate == "pad" or candidate.startswith("pad "):
        return _parse_friendly_pad_frame(candidate)
    if not (candidate == "hm1" or candidate.startswith("hm1 ")):
        return None
    if len(candidate) > 160:
        raise ValueError("controller frame is too long")

    parts = candidate.split()
    if len(parts) != 7 or parts[0] != "hm1":
        raise ValueError("controller frame must have seven fields")

    session = _base36(parts[1], maximum=(1 << 63) - 1)
    sequence = _base36(parts[2], maximum=(1 << 31) - 1)
    values = parts[3].split(",")
    if len(values) != 6:
        raise ValueError("controller frame must contain six analog values")
    try:
        lx_i, ly_i, rx_i, ry_i, lt_i, rt_i = (int(value) for value in values)
    except ValueError as error:
        raise ValueError("controller analog values must be integers") from error
    if any(not -100 <= value <= 100 for value in (lx_i, ly_i, rx_i, ry_i)):
        raise ValueError("stick value out of range")
    if any(not 0 <= value <= 100 for value in (lt_i, rt_i)):
        raise ValueError("trigger value out of range")

    if not _HEX.fullmatch(parts[4]) or not _HEX.fullmatch(parts[5]):
        raise ValueError("button masks must be hexadecimal")
    held_mask = int(parts[4], 16)
    tap_mask = int(parts[5], 16)
    if held_mask & ~VALID_BUTTON_MASK or tap_mask & ~VALID_BUTTON_MASK:
        raise ValueError("button mask contains unsupported controls")

    try:
        lease_ms = int(parts[6])
    except ValueError as error:
        raise ValueError("lease must be integer milliseconds") from error
    if not 50 <= lease_ms <= 5000:
        raise ValueError("lease must be between 50 and 5000 milliseconds")

    return PadFrame(
        session=session,
        sequence=sequence,
        lx=lx_i / 100.0,
        ly=ly_i / 100.0,
        rx=rx_i / 100.0,
        ry=ry_i / 100.0,
        lt=lt_i / 100.0,
        rt=rt_i / 100.0,
        held_mask=held_mask,
        tap_mask=tap_mask,
        lease_ms=lease_ms,
    )


def _parse_friendly_pad_frame(candidate: str) -> PadFrame:
    """Parse TikTok-compatible, word-shaped full-state controller packets.

    Example: ``pad mu1k4879 q1 e1ao w80 lr35 rt100 h40 t1``.
    Direction tokens avoid comma-heavy numeric strings that TikTok may silently filter.
    """

    if len(candidate) > 150:
        raise ValueError("controller frame is too long")
    parts = candidate.split()
    if len(parts) < 4 or parts[0] != "pad":
        raise ValueError("friendly controller frame is incomplete")
    session = _base36(parts[1], maximum=(1 << 63) - 1)
    if not parts[2].startswith("q") or not parts[3].startswith("e"):
        raise ValueError("friendly controller frame is missing order fields")
    sequence = _base36(parts[2][1:], maximum=(1 << 31) - 1)
    lease_ms = _base36(parts[3][1:], maximum=5000)
    if lease_ms < 50:
        raise ValueError("lease must be between 50 and 5000 milliseconds")

    values: dict[str, int] = {"lx": 0, "ly": 0, "rx": 0, "ry": 0, "lt": 0, "rt": 0}
    held_mask = 0
    tap_mask = 0
    directions = {
        "w": ("ly", 1), "s": ("ly", -1), "a": ("lx", -1), "d": ("lx", 1),
        "ll": ("rx", -1), "lr": ("rx", 1), "lu": ("ry", 1), "ld": ("ry", -1),
    }
    seen: set[str] = set()
    for token in parts[4:]:
        match = re.fullmatch(r"(ll|lr|lu|ld|lt|rt|w|s|a|d)(\d{1,3})", token)
        if match:
            prefix, amount_text = match.groups()
            amount = int(amount_text)
            if not 1 <= amount <= 100:
                raise ValueError("friendly analog value out of range")
            if prefix in ("lt", "rt"):
                control, value = prefix, amount
            else:
                control, direction = directions[prefix]
                value = amount * direction
            if control in seen:
                raise ValueError("friendly controller frame repeats a control")
            seen.add(control)
            values[control] = value
            continue
        if re.fullmatch(r"[ht][0-9a-f]{1,4}", token):
            control = token[0]
            if control in seen:
                raise ValueError("friendly controller frame repeats a mask")
            seen.add(control)
            mask = int(token[1:], 16)
            if mask & ~VALID_BUTTON_MASK:
                raise ValueError("button mask contains unsupported controls")
            if control == "h":
                held_mask = mask
            else:
                tap_mask = mask
            continue
        raise ValueError("unknown friendly controller token")

    return PadFrame(
        session=session,
        sequence=sequence,
        lx=values["lx"] / 100.0,
        ly=values["ly"] / 100.0,
        rx=values["rx"] / 100.0,
        ry=values["ry"] / 100.0,
        lt=values["lt"] / 100.0,
        rt=values["rt"] / 100.0,
        held_mask=held_mask,
        tap_mask=tap_mask,
        lease_ms=lease_ms,
    )
