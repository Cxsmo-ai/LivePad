"""Provider-independent chat events."""

from dataclasses import dataclass
import time


@dataclass(frozen=True, slots=True)
class ChatEvent:
    """A normalized comment that is safe to hand to the command pipeline."""

    username: str
    user_id: str
    message: str
    timestamp_ns: int
    platform: str = "tiktok"

    @classmethod
    def now(cls, username: str, user_id: str, message: str, platform: str = "tiktok") -> "ChatEvent":
        return cls(username, user_id, message, time.monotonic_ns(), platform)

