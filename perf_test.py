"""Repeatable local throughput/latency check for the controller core."""

from __future__ import annotations

import json
import statistics
import time

from chat.normalized_event import ChatEvent
from chat.processor import ChatCommandProcessor
from controller.state_engine import StateEngine


def run(viewers: int = 1000) -> dict[str, float | int]:
    engine = StateEngine()
    processor = ChatCommandProcessor(engine)
    message = "w sprint ads fire right 35"
    latencies: list[float] = []

    start = time.perf_counter()
    for index in range(viewers):
        event_start = time.perf_counter_ns()
        processor.process(ChatEvent(f"viewer-{index}", str(index), message, time.monotonic_ns()))
        latencies.append((time.perf_counter_ns() - event_start) / 1_000_000)
    ingest_ms = (time.perf_counter() - start) * 1000

    tick_start = time.perf_counter()
    for index in range(1000):
        engine.tick(time.monotonic_ns() + index * 1_000_000)
    tick_ms = (time.perf_counter() - tick_start) * 1000
    return {
        "viewers": viewers,
        "commands": viewers * 5,
        "ingest_ms": round(ingest_ms, 3),
        "ingest_events_per_second": round(viewers / max(ingest_ms / 1000, 1e-9)),
        "event_p50_ms": round(statistics.median(latencies), 4),
        "event_p95_ms": round(statistics.quantiles(latencies, n=20)[18], 4),
        "tick_1000_ms": round(tick_ms, 3),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
