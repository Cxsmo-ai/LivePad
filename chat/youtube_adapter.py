"""Adapter from YouTube comment shape to normalized ChatEvent."""

from typing import Any

from .normalized_event import ChatEvent
from .processor import ChatCommandProcessor, ProcessingResult


class YouTubeCommentAdapter:
    def __init__(self, processor: ChatCommandProcessor):
        self.processor = processor

    def handle(self, event_data: dict[str, Any]) -> ProcessingResult:
        username = str(event_data.get("user", "unknown"))
        user_id = f"yt:{str(event_data.get('user_id') or username)}"
        message = str(event_data.get("comment", ""))
        return self.processor.process(
            ChatEvent.now(username, user_id, message, platform="youtube")
        )

