"""Adapter from normalized Twitch IRC comments to ChatEvent."""

from typing import Any

from .normalized_event import ChatEvent
from .processor import ChatCommandProcessor, ProcessingResult


class TwitchCommentAdapter:
    def __init__(self, processor: ChatCommandProcessor):
        self.processor = processor

    def handle(self, event_data: dict[str, Any]) -> ProcessingResult:
        username = str(
            event_data.get("display_name") or event_data.get("user") or "unknown"
        )
        user_id = f"tw:{str(event_data.get('user_id') or event_data.get('username') or username)}"
        message = str(event_data.get("comment", ""))
        if message.startswith("!"):
            message = message[1:]
        return self.processor.process(
            ChatEvent.now(username, user_id, message, platform="twitch")
        )
