"""Minimal TikTok LIVE comment client used by the chat-gamepad worker."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable
from urllib.parse import urlparse

from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TikTokLiveManager:
    """Connect to one creator and forward only lifecycle and comment events."""

    _MAX_SEEN_EVENT_IDS = 4096
    _SEEN_EVENT_TTL_SECONDS = 30.0

    def __init__(self, username: str):
        self.username = self.normalize_username(username)
        self.client = TikTokLiveClient(unique_id=f"@{self.username}")
        self.is_connected = False
        self.event_callbacks: dict[str, list[Callable[[dict[str, Any]], None]]] = {
            "comment": [],
            "connect": [],
            "disconnect": [],
        }
        # TikTokLive normally delivers each comment once, but reconnects can
        # replay an event.  Only deduplicate when the upstream event contains
        # an explicit ID; identical text from a viewer is still allowed.
        self._seen_event_ids: dict[str, float] = {}
        self._setup_event_handlers()

    @staticmethod
    def normalize_username(value: str) -> str:
        """Accept a handle, @handle, or TikTok profile/live URL."""
        raw = str(value or "").strip()
        if "://" in raw:
            path = urlparse(raw).path
            raw = path.split("/", 2)[1] if path.startswith("/") and path.count("/") >= 1 else path
        raw = raw.split("?", 1)[0].split("#", 1)[0].strip().strip("/")
        return raw.lstrip("@").split("/", 1)[0].strip()

    @staticmethod
    def _safe_attr(value: Any, name: str) -> Any:
        try:
            return getattr(value, name, None)
        except Exception:
            return None

    @classmethod
    def _first_value(cls, value: Any, *names: str) -> Any:
        for name in names:
            candidate = cls._safe_attr(value, name)
            if candidate is not None and str(candidate).strip():
                return candidate
        return None

    @classmethod
    def normalize_comment_event(cls, event: CommentEvent) -> dict[str, Any] | None:
        """Convert TikTokLive's changing event shape into our stable payload.

        TikTokLive has exposed both ``comment`` and ``content`` over time, and
        user metadata can be absent on malformed/partial events.  Keeping this
        normalization at the boundary prevents one bad event from killing the
        worker callback.
        """
        user = cls._safe_attr(event, "user")
        user_id = cls._first_value(user, "unique_id", "user_id", "display_id")
        user_id = user_id or cls._first_value(event, "user_id", "unique_id", "display_id")
        user_id = str(user_id or "unknown")

        display_name = cls._first_value(user, "nickname", "display_name", "unique_id", "display_id")
        display_name = str(display_name or user_id)

        message = cls._first_value(event, "comment", "content", "text")
        if message is None:
            return None
        message = str(message).strip()
        if not message:
            return None

        common = cls._safe_attr(event, "common")
        event_id = cls._first_value(
            event,
            "message_id",
            "msg_id",
            "event_id",
            "eventId",
        ) or cls._first_value(common, "message_id", "msg_id", "event_id", "eventId")

        payload: dict[str, Any] = {
            "user": display_name,
            "user_id": user_id,
            "comment": message,
        }
        if event_id is not None:
            payload["_event_id"] = str(event_id)
        return payload

    def _is_duplicate_event(self, event_id: str | None) -> bool:
        if not event_id:
            return False
        now = time.monotonic()
        cutoff = now - self._SEEN_EVENT_TTL_SECONDS
        self._seen_event_ids = {
            key: seen_at for key, seen_at in self._seen_event_ids.items() if seen_at >= cutoff
        }
        if event_id in self._seen_event_ids:
            return True
        self._seen_event_ids[event_id] = now
        if len(self._seen_event_ids) > self._MAX_SEEN_EVENT_IDS:
            oldest = min(self._seen_event_ids, key=self._seen_event_ids.get)
            self._seen_event_ids.pop(oldest, None)
        return False

    def _mark_disconnected(self) -> None:
        was_connected = self.is_connected
        self.is_connected = False
        if was_connected:
            self._trigger_callbacks("disconnect", {})

    def _setup_event_handlers(self) -> None:
        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent) -> None:
            self.is_connected = True
            unique_id = self._first_value(event, "unique_id") or self.username
            self._trigger_callbacks("connect", {"unique_id": str(unique_id)})

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent) -> None:
            payload = self.normalize_comment_event(event)
            if payload is None or self._is_duplicate_event(payload.get("_event_id")):
                return
            self._trigger_callbacks("comment", payload)

        @self.client.on(DisconnectEvent)
        async def on_disconnect(_: DisconnectEvent) -> None:
            self._mark_disconnected()

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
        try:
            await self.client.disconnect()
        finally:
            self._mark_disconnected()
