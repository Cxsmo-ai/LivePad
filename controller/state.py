"""Resolved logical Xbox controller state."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ControllerState:
    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    lt: float = 0.0
    rt: float = 0.0
    buttons: frozenset[str] = field(default_factory=frozenset)

    def clamped(self) -> "ControllerState":
        return ControllerState(
            lx=max(-1.0, min(1.0, self.lx)),
            ly=max(-1.0, min(1.0, self.ly)),
            rx=max(-1.0, min(1.0, self.rx)),
            ry=max(-1.0, min(1.0, self.ry)),
            lt=max(0.0, min(1.0, self.lt)),
            rt=max(0.0, min(1.0, self.rt)),
            buttons=frozenset(self.buttons),
        )

    def to_wire(self, sequence: int) -> dict:
        return {
            "type": "state",
            "seq": sequence,
            "lx": self.lx,
            "ly": self.ly,
            "rx": self.rx,
            "ry": self.ry,
            "lt": self.lt,
            "rt": self.rt,
            "buttons": sorted(self.buttons),
        }
