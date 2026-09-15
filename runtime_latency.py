"""Bounded, low-overhead pipeline latency measurements."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import statistics


@dataclass(frozen=True, slots=True)
class LatencySnapshot:
    stage: str
    samples: int
    p50_ms: float | None
    p95_ms: float | None
    latest_ms: float | None


class LatencyMetrics:
    """Keep recent stage timings without adding an unbounded hot-path log."""

    def __init__(self, capacity: int = 256):
        self.capacity = max(32, int(capacity))
        self._samples: dict[str, deque[float]] = {}

    def observe_ns(self, stage: str, elapsed_ns: int) -> None:
        elapsed_ms = max(0.0, int(elapsed_ns) / 1_000_000.0)
        values = self._samples.setdefault(stage, deque(maxlen=self.capacity))
        values.append(elapsed_ms)

    def snapshot(self, stage: str) -> LatencySnapshot:
        values = list(self._samples.get(stage, ()))
        if not values:
            return LatencySnapshot(stage, 0, None, None, None)
        ordered = sorted(values)
        p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
        return LatencySnapshot(
            stage=stage,
            samples=len(values),
            p50_ms=round(statistics.median(ordered), 4),
            p95_ms=round(ordered[p95_index], 4),
            latest_ms=round(values[-1], 4),
        )

    def all_snapshots(self) -> dict[str, LatencySnapshot]:
        return {stage: self.snapshot(stage) for stage in self._samples}
