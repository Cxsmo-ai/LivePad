"""Adapter from the legacy TikTokLiveManager callback shape to ChatEvent."""

from typing import Any

from .normalized_event import ChatEvent
from .processor import ChatCommandProcessor, ProcessingResult


class TikTokCommentAdapter:
    def __init__(self, processor: ChatCommandProcessor):
        self.processor = processor

    def handle(self, event_data: dict[str, Any]) -> ProcessingResult:
        username = str(event_data.get("user", "unknown"))
        user_id = str(event_data.get("user_id") or username)
        message = str(event_data.get("comment", ""))
        return self.processor.process(ChatEvent.now(username, user_id, message))
