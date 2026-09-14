"""Per-user token buckets for chat commands."""

from dataclasses import dataclass
import time


@dataclass(frozen=True, slots=True)
class RateLimit:
    rate_per_second: float
    burst: float


class _Bucket:
    def __init__(self, limit: RateLimit, now_ns: int):
        self.limit = limit
        self.tokens = limit.burst
        self.last_ns = now_ns

    def allow(self, now_ns: int) -> bool:
        elapsed = max(0, now_ns - self.last_ns) / 1_000_000_000
        self.tokens = min(self.limit.burst, self.tokens + elapsed * self.limit.rate_per_second)
        self.last_ns = now_ns
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True


class PerUserRateLimiter:
    DEFAULTS = {
        "movement": RateLimit(8, 4),
        "camera": RateLimit(10, 5),
        "button": RateLimit(6, 3),
        "trigger": RateLimit(8, 4),
    }

    def __init__(self, limits: dict[str, RateLimit] | None = None):
        self.limits = {**self.DEFAULTS, **(limits or {})}
        self._buckets: dict[tuple[str, str], _Bucket] = {}

    def allow(self, user_id: str, category: str, now_ns: int | None = None) -> bool:
        limit = self.limits.get(category)
        if limit is None:
            return False
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        key = (user_id, category)
        bucket = self._buckets.setdefault(key, _Bucket(limit, now_ns))
        return bucket.allow(now_ns)

    def clear_user(self, user_id: str) -> None:
        for key in [key for key in self._buckets if key[0] == user_id]:
            del self._buckets[key]
