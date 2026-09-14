"""Watchdog policy for neutralizing the controller on lost heartbeats."""

import time


class SafetyWatchdog:
    def __init__(self, timeout_ms: int = 1000):
        self.timeout_ns = timeout_ms * 1_000_000
        self._last_heartbeat_ns: int | None = None

    def heartbeat(self, now_ns: int | None = None) -> None:
        self._last_heartbeat_ns = time.monotonic_ns() if now_ns is None else now_ns

    def expired(self, now_ns: int | None = None) -> bool:
        if self._last_heartbeat_ns is None:
            return True
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        return now_ns - self._last_heartbeat_ns >= self.timeout_ns
