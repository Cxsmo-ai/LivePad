"""Read-only live TikTok comment ingestion and latency smoke test."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

from runtime import ControllerRuntime
from tiktok_client import TikTokLiveManager


async def run_live_test(username: str, duration_seconds: float) -> dict:
    manager = TikTokLiveManager(username)
    runtime = ControllerRuntime()
    connected = asyncio.Event()
    comments = 0
    accepted = 0
    rate_limited = 0
    users: set[str] = set()
    latencies_ms: list[float] = []

    def on_connect(_: dict) -> None:
        connected.set()

    def on_comment(event: dict) -> None:
        nonlocal comments, accepted, rate_limited
        started = time.perf_counter_ns()
        result = runtime.handle_comment(event)
        latencies_ms.append((time.perf_counter_ns() - started) / 1_000_000)
        comments += 1
        accepted += len(result.accepted)
        rate_limited += len(result.rate_limited)
        users.add(str(event.get("user_id") or event.get("user") or "unknown"))

    manager.on_event("connect", on_connect)
    manager.on_event("comment", on_comment)
    connect_started = time.perf_counter()
    connection = asyncio.create_task(manager.connect())
    try:
        while not connected.is_set() and not connection.done():
            if time.perf_counter() - connect_started > 20:
                raise TimeoutError("TikTok connection was not ready within 20 seconds")
            await asyncio.sleep(0.05)
        if connection.done():
            await connection
            raise RuntimeError("TikTok stream disconnected before the test began")

        connection_ms = (time.perf_counter() - connect_started) * 1000
        await asyncio.sleep(duration_seconds)
    finally:
        await manager.disconnect()
        runtime.clear()
        if not connection.done():
            try:
                await asyncio.wait_for(connection, timeout=5)
            except asyncio.TimeoutError:
                connection.cancel()

    sorted_latency = sorted(latencies_ms)
    p95_index = max(0, min(len(sorted_latency) - 1, round(len(sorted_latency) * 0.95) - 1))
    return {
        "username": username.lstrip("@"),
        "duration_seconds": duration_seconds,
        "connection_ms": round(connection_ms, 2),
        "comments_received": comments,
        "unique_viewers": len(users),
        "recognized_commands": accepted,
        "rate_limited_commands": rate_limited,
        "processing_p50_ms": round(statistics.median(latencies_ms), 4) if latencies_ms else None,
        "processing_p95_ms": round(sorted_latency[p95_index], 4) if sorted_latency else None,
        "passed": comments > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--duration", type=float, default=30.0)
    args = parser.parse_args()
    result = asyncio.run(run_live_test(args.username, args.duration))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
