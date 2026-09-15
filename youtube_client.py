"""YouTube LIVE chat client inspired by and compatible with youtube-chat-next.

Connects to public YouTube Live streams via the web InnerTube endpoint with
zero API keys, OAuth, or credentials required.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from typing import Any, Callable
import urllib.parse

import httpx

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "SOCS=CAI",
}


def resolve_live_url(target: str) -> str:
    """Resolve a user input (handle, video ID, channel ID, or full URL) into a live watch URL."""
    target = target.strip()
    if not target:
        raise ValueError("Target cannot be empty")
    if target.startswith("http://") or target.startswith("https://"):
        parsed = urllib.parse.urlparse(target)
        if "youtu.be" in parsed.netloc:
            video_id = parsed.path.strip("/")
            return f"https://www.youtube.com/watch?v={video_id}"
        if "/watch" in parsed.path:
            query = urllib.parse.parse_qs(parsed.query)
            if "v" in query:
                return f"https://www.youtube.com/watch?v={query['v'][0]}"
        return target
    if target.startswith("@"):
        return f"https://www.youtube.com/{target}/live"
    if target.startswith("UC") and 20 <= len(target) <= 28 and not any(c.isspace() for c in target):
        return f"https://www.youtube.com/channel/{target}/live"
    if len(target) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", target):
        return f"https://www.youtube.com/watch?v={target}"
    return f"https://www.youtube.com/@{target}/live"


def select_live_view(top_continuation: str) -> str:
    """Flip protobuf selector byte from Top Chat (0x08 0x04) to Live Chat (0x08 0x01)."""
    try:
        decoded = urllib.parse.unquote(top_continuation)
        padding = (4 - len(decoded) % 4) % 4
        raw = base64.urlsafe_b64decode(decoded + "=" * padding)
        b = bytearray(raw)
        offsets = [
            i for i in range(len(b) - 1)
            if b[i] == 0x08 and b[i + 1] == 0x04
        ]
        if len(offsets) == 1:
            b[offsets[0] + 1] = 0x01
            encoded = base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")
            return encoded
    except Exception as error:
        logger.debug("select_live_view fallback to top continuation: %s", error)
    return top_continuation


def parse_action_to_comment(action: dict[str, Any]) -> dict[str, Any] | None:
    """Extract standard comment info from an InnerTube addChatItemAction."""
    item = action.get("addChatItemAction", {}).get("item", {})
    renderer = (
        item.get("liveChatTextMessageRenderer")
        or item.get("liveChatPaidMessageRenderer")
        or item.get("liveChatMembershipItemRenderer")
    )
    if not renderer:
        return None

    author_name = renderer.get("authorName", {}).get("simpleText", "unknown")
    user_id = renderer.get("authorExternalChannelId", author_name)

    message_parts: list[str] = []
    runs = renderer.get("message", {}).get("runs", [])
    if not runs and "headerSubtext" in renderer:
        runs = renderer.get("headerSubtext", {}).get("runs", [])

    for run in runs:
        if "text" in run:
            message_parts.append(run["text"])
        elif "emoji" in run:
            emoji = run["emoji"]
            shortcuts = emoji.get("shortcuts")
            if shortcuts:
                message_parts.append(shortcuts[0])
            else:
                message_parts.append(emoji.get("emojiId", ""))

    full_message = "".join(message_parts)
    timestamp_usec = int(renderer.get("timestampUsec", 0))

    return {
        "user": author_name,
        "user_id": user_id,
        "comment": full_message,
        "platform": "youtube",
        "timestamp_usec": timestamp_usec,
    }


class YouTubeLiveManager:
    """Stream comments from YouTube Live InnerTube API without credentials."""

    def __init__(self, target: str, chat_type: str = "live", interval_seconds: float = 0.1):
        self.target = target
        self.chat_type = chat_type.lower()
        self.interval_seconds = interval_seconds
        self.is_connected = False
        self.stop_requested = False
        self.live_id: str | None = None
        self.event_callbacks: dict[str, list[Callable[[dict[str, Any]], None]]] = {
            "comment": [],
            "connect": [],
            "disconnect": [],
            "error": [],
        }

    def on_event(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
        if event_type not in self.event_callbacks:
            raise ValueError(f"unsupported YouTube event type: {event_type}")
        self.event_callbacks[event_type].append(callback)

    def _trigger_callbacks(self, event_type: str, event_data: dict[str, Any]) -> None:
        for callback in tuple(self.event_callbacks.get(event_type, ())):
            try:
                callback(event_data)
            except Exception:
                logger.exception("YouTube %s callback failed", event_type)

    async def connect(self) -> None:
        """Fetch watch page, acquire continuation token, and enter the polling loop."""
        self.stop_requested = False
        live_url = resolve_live_url(self.target)

        async with httpx.AsyncClient(headers=_HEADERS, timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(live_url)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code} fetching YouTube page: {live_url}")

            page_html = resp.text
            id_match = re.search(r'<link rel="canonical" href="https://www.youtube\.com/watch\?v=(.+?)">', page_html)
            if not id_match:
                id_match = re.search(r'itemprop="videoId"\s+content="(.+?)"', page_html)
            if not id_match:
                raise RuntimeError(f"No live stream canonical link found for {self.target}")
            self.live_id = id_match.group(1)

            if 'isReplay":true' in page_html or '"isReplay": true' in page_html:
                raise RuntimeError(f"Stream {self.live_id} has ended (isReplay)")

            key_match = re.search(r'["\']INNERTUBE_API_KEY["\']:\s*["\'](.+?)["\']', page_html)
            if not key_match:
                raise RuntimeError("Failed to extract INNERTUBE_API_KEY from YouTube watch page")
            api_key = key_match.group(1)

            ver_match = re.search(r'["\']clientVersion["\']:\s*["\']([\d.]+?)["\']', page_html)
            client_version = ver_match.group(1) if ver_match else "2.20260911.01.00"

            scoped_match = re.search(
                r'"liveChatRenderer"\s*:\s*\{.*?"continuations"\s*:\s*\[\s*\{\s*"reloadContinuationData"\s*:\s*\{\s*"continuation"\s*:\s*"([^"]+)"',
                page_html,
                re.DOTALL,
            )
            continuation = scoped_match.group(1) if scoped_match else None
            if not continuation:
                loose_match = re.search(r'["\']continuation["\']:\s*["\'](.+?)["\']', page_html)
                continuation = loose_match.group(1) if loose_match else None

            if not continuation:
                raise RuntimeError("Failed to extract liveChatRenderer continuation token")

            if self.chat_type == "live":
                continuation = select_live_view(continuation)

            self.is_connected = True
            self._trigger_callbacks("connect", {"live_id": self.live_id, "platform": "youtube"})

            post_url = f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={api_key}"
            payload = {
                "context": {
                    "client": {
                        "clientVersion": client_version,
                        "clientName": "WEB",
                    }
                },
                "continuation": continuation,
            }

            consecutive_errors = 0
            while not self.stop_requested:
                delay = self.interval_seconds
                try:
                    chat_resp = await client.post(post_url, json=payload)
                    if chat_resp.status_code == 429 or chat_resp.status_code == 403:
                        retry_after = float(chat_resp.headers.get("retry-after", "10"))
                        delay = max(delay, retry_after)
                        consecutive_errors += 1
                        if consecutive_errors >= 5:
                            raise RuntimeError("Exceeded maximum rate limit retries")
                        await asyncio.sleep(delay)
                        continue

                    chat_resp.raise_for_status()
                    consecutive_errors = 0
                    data = chat_resp.json()

                    cont_contents = data.get("continuationContents", {}).get("liveChatContinuation", {})
                    if not cont_contents:
                        break

                    actions = cont_contents.get("actions", [])
                    for act in actions:
                        comment = parse_action_to_comment(act)
                        if comment:
                            self._trigger_callbacks("comment", comment)

                    continuation_entry = cont_contents.get("continuations", [{}])[0]
                    next_continuation = (
                        continuation_entry.get("invalidationContinuationData", {}).get("continuation")
                        or continuation_entry.get("timedContinuationData", {}).get("continuation")
                    )
                    timeout_ms = (
                        continuation_entry.get("invalidationContinuationData", {}).get("timeoutMs")
                        or continuation_entry.get("timedContinuationData", {}).get("timeoutMs")
                        or 1000
                    )

                    if not next_continuation:
                        break

                    payload["continuation"] = next_continuation
                    delay = max(self.interval_seconds, timeout_ms / 1000.0)

                except asyncio.CancelledError:
                    break
                except Exception as error:
                    consecutive_errors += 1
                    self._trigger_callbacks("error", {"error": str(error), "platform": "youtube"})
                    if consecutive_errors >= 5:
                        raise
                    delay = min(5.0 * consecutive_errors, 30.0)

                await asyncio.sleep(delay)

        self.is_connected = False
        self._trigger_callbacks("disconnect", {"reason": "stream ended", "platform": "youtube"})

    async def disconnect(self) -> None:
        self.stop_requested = True
        self.is_connected = False
        self._trigger_callbacks("disconnect", {"reason": "user stopped", "platform": "youtube"})
