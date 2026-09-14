"""Minimal TikTok LIVE comment client used by the chat-gamepad worker."""

from __future__ import annotations

import logging
from typing import Any, Callable

from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TikTokLiveManager:
    """Connect to one creator and forward only lifecycle and comment events."""

    def __init__(self, username: str):
        self.username = username.lstrip("@")
        self.client = TikTokLiveClient(unique_id=f"@{self.username}")
        self.is_connected = False
        self.event_callbacks: dict[str, list[Callable[[dict[str, Any]], None]]] = {
            "comment": [],
            "connect": [],
            "disconnect": [],
        }
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent) -> None:
            self.is_connected = True
            self._trigger_callbacks("connect", {"unique_id": event.unique_id})

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent) -> None:
            user_id = str(
                getattr(event.user, "unique_id", None)
                or getattr(event.user, "user_id", None)
                or event.user.nickname
            )
            self._trigger_callbacks("comment", {
                "user": event.user.nickname,
                "user_id": user_id,
                "comment": event.comment,
            })

        @self.client.on(DisconnectEvent)
        async def on_disconnect(_: DisconnectEvent) -> None:
            was_connected = self.is_connected
            self.is_connected = False
            if was_connected:
                self._trigger_callbacks("disconnect", {})

    def _trigger_callbacks(self, event_type: str, event_data: dict[str, Any]) -> None:
        for callback in tuple(self.event_callbacks.get(event_type, ())):
            try:
                callback(event_data)
            except Exception:
                logger.exception("TikTok %s callback failed", event_type)

    def on_event(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
        if event_type not in self.event_callbacks:
            raise ValueError(f"unsupported TikTok event type: {event_type}")
        self.event_callbacks[event_type].append(callback)

    async def connect(self) -> None:
        await self.client.connect()

    async def disconnect(self) -> None:
        await self.client.disconnect()
        if self.is_connected:
            self.is_connected = False
            self._trigger_callbacks("disconnect", {})
