"""Low-latency, read-only Twitch IRC client over secure WebSockets.

Twitch currently accepts anonymous ``justinfan`` readers, although its public
documentation only guarantees authenticated IRC clients.  This module keeps
that detail isolated so the GUI can remain username-only while reporting a
clear error if Twitch changes the anonymous policy.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import logging
import random
import re
from typing import Any, Callable

import websockets
from websockets.exceptions import ConnectionClosed


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

TWITCH_IRC_WEBSOCKET = "wss://irc-ws.chat.twitch.tv:443"
_CHANNEL_PATTERN = re.compile(r"^[a-zA-Z0-9_]{1,25}$")
_TAG_ESCAPES = {"s": " ", ":": ";", "\\": "\\", "r": "\r", "n": "\n"}


class TwitchProtocolError(RuntimeError):
    """The server rejected the IRC session or channel."""


class TwitchReconnectRequested(RuntimeError):
    """Twitch explicitly requested a fresh IRC connection."""


@dataclass(frozen=True)
class IRCMessage:
    tags: dict[str, str]
    prefix: str | None
    command: str
    params: tuple[str, ...]
    raw: str


def normalize_channel(channel: str) -> str:
    normalized = channel.strip().lower().lstrip("#@").removeprefix("twitch.tv/")
    if not _CHANNEL_PATTERN.fullmatch(normalized):
        raise ValueError("Twitch channel must be a 1-25 character username")
    return normalized


def _unescape_tag(value: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            result.append(_TAG_ESCAPES.get(value[index + 1], value[index + 1]))
            index += 2
        else:
            result.append(value[index])
            index += 1
    return "".join(result)


def parse_irc_line(line: str) -> IRCMessage:
    """Parse one IRCv3 line without assuming a fixed Twitch tag order."""
    raw = line.rstrip("\r\n")
    if not raw:
        raise ValueError("IRC line is empty")
    rest = raw
    tags: dict[str, str] = {}
    prefix: str | None = None

    if rest.startswith("@"):
        tag_block, separator, rest = rest[1:].partition(" ")
        if not separator:
            raise ValueError("IRC tags were not followed by a command")
        for item in tag_block.split(";"):
            key, equals, value = item.partition("=")
            if key:
                tags[key] = _unescape_tag(value) if equals else ""

    if rest.startswith(":"):
        prefix, separator, rest = rest[1:].partition(" ")
        if not separator:
            raise ValueError("IRC prefix was not followed by a command")

    trailing: str | None = None
    middle, separator, possible_trailing = rest.partition(" :")
    if separator:
        trailing = possible_trailing
    parts = middle.split()
    if not parts:
        raise ValueError("IRC command is missing")
    command = parts[0].upper()
    params = parts[1:]
    if trailing is not None:
        params.append(trailing)
    return IRCMessage(tags, prefix, command, tuple(params), raw)


def parse_badges(value: str) -> dict[str, str]:
    badges: dict[str, str] = {}
    for badge in filter(None, value.split(",")):
        name, separator, version = badge.partition("/")
        if name:
            badges[name] = version if separator else ""
    return badges


def normalize_privmsg(message: IRCMessage) -> dict[str, Any] | None:
    """Convert a Twitch PRIVMSG into the app's normalized comment shape."""
    if message.command != "PRIVMSG" or len(message.params) < 2:
        return None
    username = (message.prefix or "unknown").split("!", 1)[0]
    display_name = message.tags.get("display-name") or username
    badges = parse_badges(message.tags.get("badges", ""))
    sent_timestamp = message.tags.get("tmi-sent-ts", "0")
    try:
        timestamp_ms = int(sent_timestamp)
    except ValueError:
        timestamp_ms = 0
    comment = message.params[-1]
    if comment.startswith("\x01ACTION ") and comment.endswith("\x01"):
        comment = comment[8:-1]
    return {
        "platform": "twitch",
        "message_id": message.tags.get("id", ""),
        "user": display_name,
        "user_id": message.tags.get("user-id") or username,
        "username": username,
        "display_name": display_name,
        "comment": comment,
        "channel": message.params[0].lstrip("#"),
        "badges": badges,
        "moderator": message.tags.get("mod") == "1" or bool(
            {"broadcaster", "moderator"}.intersection(badges)
        ),
        "subscriber": message.tags.get("subscriber") == "1" or bool(
            {"subscriber", "founder"}.intersection(badges)
        ),
        "vip": message.tags.get("vip") == "1" or "vip" in badges,
        "first_message": message.tags.get("first-msg") == "1",
        "timestamp_ms": timestamp_ms,
    }


class TwitchLiveManager:
    """Receive public Twitch chat through the IRC-over-WebSocket endpoint."""

    _EVENT_TYPES = {
        "comment", "connect", "disconnect", "error", "roomstate",
        "usernotice", "clearchat", "clearmsg", "notice",
    }

    def __init__(
        self,
        channel: str,
        *,
        websocket_url: str = TWITCH_IRC_WEBSOCKET,
        dedupe_capacity: int = 4096,
    ):
        self.channel = normalize_channel(channel)
        self.websocket_url = websocket_url
        self.dedupe_capacity = max(64, dedupe_capacity)
        self.is_connected = False
        self.stop_requested = False
        self._websocket: Any | None = None
        self._seen_ids: OrderedDict[str, None] = OrderedDict()
        self.event_callbacks: dict[str, list[Callable[[dict[str, Any]], None]]] = {
            event_type: [] for event_type in self._EVENT_TYPES
        }

    def on_event(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
        if event_type not in self.event_callbacks:
            raise ValueError(f"unsupported Twitch event type: {event_type}")
        self.event_callbacks[event_type].append(callback)

    def _trigger_callbacks(self, event_type: str, event_data: dict[str, Any]) -> None:
        for callback in tuple(self.event_callbacks.get(event_type, ())):
            try:
                callback(event_data)
            except Exception:
                logger.exception("Twitch %s callback failed", event_type)

    def _remember(self, key: str) -> bool:
        if key in self._seen_ids:
            self._seen_ids.move_to_end(key)
            return False
        self._seen_ids[key] = None
        while len(self._seen_ids) > self.dedupe_capacity:
            self._seen_ids.popitem(last=False)
        return True

    async def _send(self, line: str) -> None:
        if self._websocket is None:
            raise ConnectionError("Twitch WebSocket is not connected")
        await self._websocket.send(line + "\r\n")

    async def _handle_line(self, line: str) -> None:
        message = parse_irc_line(line)
        if message.command == "PING":
            payload = message.params[-1] if message.params else "tmi.twitch.tv"
            await self._send(f"PONG :{payload}")
            return
        if message.command == "RECONNECT":
            raise TwitchReconnectRequested("Twitch requested reconnection")
        if message.command == "NOTICE":
            event = {
                "platform": "twitch",
                "message_id": message.tags.get("msg-id", ""),
                "message": message.params[-1] if message.params else "",
            }
            self._trigger_callbacks("notice", event)
            lower_message = event["message"].lower()
            if "authentication failed" in lower_message:
                raise TwitchProtocolError(
                    "Twitch rejected anonymous chat access; authenticated chat:read access is required"
                )
            if message.tags.get("msg-id") in {"msg_channel_suspended", "msg_banned"}:
                raise TwitchProtocolError(event["message"] or "Twitch channel is unavailable")
            return
        if message.command == "ROOMSTATE":
            event = {
                "platform": "twitch",
                "channel": message.params[0].lstrip("#") if message.params else self.channel,
                "tags": dict(message.tags),
            }
            self._trigger_callbacks("roomstate", event)
            if not self.is_connected and event["channel"].casefold() == self.channel.casefold():
                self.is_connected = True
                self._trigger_callbacks("connect", event)
            return
        if message.command == "PRIVMSG":
            event = normalize_privmsg(message)
            if event is None:
                return
            message_key = event["message_id"] or hashlib.blake2s(
                message.raw.encode("utf-8"), digest_size=16
            ).hexdigest()
            if self._remember(message_key):
                self._trigger_callbacks("comment", event)
            return
        event_name = message.command.lower()
        if event_name in {"usernotice", "clearchat", "clearmsg"}:
            self._trigger_callbacks(event_name, {
                "platform": "twitch",
                "channel": message.params[0].lstrip("#") if message.params else self.channel,
                "message": message.params[-1] if len(message.params) > 1 else "",
                "tags": dict(message.tags),
            })

    async def connect(self) -> None:
        self.stop_requested = False
        disconnect_reason = "connection closed"
        nickname = f"justinfan{random.randint(10_000, 99_999)}"
        try:
            async with websockets.connect(
                self.websocket_url,
                open_timeout=10,
                close_timeout=2,
                ping_interval=None,
                # IRC chat frames are tiny. Skip per-message deflate
                # negotiation and compression work; correctness is unchanged
                # and the socket still uses TLS/WebSocket framing.
                compression=None,
                max_size=2 * 1024 * 1024,
            ) as websocket:
                self._websocket = websocket
                await self._send("PASS SCHMOOPIIE")
                await self._send(f"NICK {nickname}")
                await self._send("CAP REQ :twitch.tv/tags twitch.tv/commands")
                await self._send(f"JOIN #{self.channel}")

                while not self.stop_requested:
                    timeout = 15.0 if not self.is_connected else 90.0
                    try:
                        payload = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    except asyncio.TimeoutError as error:
                        if not self.is_connected:
                            raise TwitchProtocolError(
                                f"Twitch did not confirm channel #{self.channel}"
                            ) from error
                        await self._send("PING :hidmaestro-streamer-edition")
                        continue
                    if isinstance(payload, bytes):
                        payload = payload.decode("utf-8", errors="replace")
                    for line in payload.splitlines():
                        if line:
                            await self._handle_line(line)
        except TwitchReconnectRequested:
            disconnect_reason = "server requested reconnect"
            raise
        except ConnectionClosed as error:
            close_code = error.rcvd.code if error.rcvd is not None else "unknown"
            disconnect_reason = f"WebSocket closed ({close_code})"
            if not self.stop_requested:
                raise
        except Exception as error:
            disconnect_reason = str(error)
            self._trigger_callbacks("error", {"platform": "twitch", "error": str(error)})
            raise
        finally:
            was_connected = self.is_connected
            self.is_connected = False
            self._websocket = None
            if was_connected:
                self._trigger_callbacks("disconnect", {
                    "platform": "twitch", "reason": disconnect_reason,
                })

    async def disconnect(self) -> None:
        self.stop_requested = True
        websocket = self._websocket
        if websocket is not None:
            await websocket.close(code=1000, reason="user stopped")
