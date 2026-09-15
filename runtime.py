"""Runtime glue for chat events, state resolution, and the optional bridge."""

from __future__ import annotations

import time
from typing import Any, Mapping

from chat.normalized_event import ChatEvent
from chat.processor import ChatCommandProcessor, ProcessingResult
from chat.tiktok_adapter import TikTokCommentAdapter
from chat.twitch_adapter import TwitchCommentAdapter
from chat.youtube_adapter import YouTubeCommentAdapter
from controller.safety import SafetyWatchdog
from controller.state_engine import StateEngine, Submission
from ipc.named_pipe import NamedPipeClient
from runtime_latency import LatencyMetrics


class ControllerRuntime:
    """Own the Python side of the controller lifecycle.

    The runtime is usable without a pipe for local tests. When a pipe is
    supplied, only changed states are sent and all clear paths send neutral.
    """

    def __init__(self, pipe: NamedPipeClient | None = None,
                 config: Mapping[str, Any] | None = None):
        self.engine = StateEngine()
        parser = None
        if config is not None:
            from chat.parser import CommandParser
            allow_seconds = bool(config.get("controller", {}).get("allow_seconds", True))
            parser = CommandParser(config.get("commands"), allow_seconds=allow_seconds)
        self.processor = ChatCommandProcessor(self.engine, parser=parser)
        self.tiktok_comments = TikTokCommentAdapter(self.processor)
        self.youtube_comments = YouTubeCommentAdapter(self.processor)
        self.twitch_comments = TwitchCommentAdapter(self.processor)
        self.comments = self.tiktok_comments
        self.watchdog = SafetyWatchdog()
        self.pipe = pipe
        self.sequence = 0
        self.latency = LatencyMetrics()

    def start(self) -> None:
        if self.pipe is not None:
            # HIDMaestro may initialize its driver/shared-memory mapping before
            # opening the pipe. Give a fresh packaged install enough time for
            # that one-time setup instead of incorrectly falling back to local
            # test mode after the old three-second window.
            self.pipe.connect(timeout_seconds=12.0)
            ready = self.pipe.receive()
            if ready.get("type") != "ready":
                raise RuntimeError(f"unexpected bridge handshake: {ready}")
        self.watchdog.heartbeat()

    def handle_comment(self, event_data: dict, platform: str | None = None) -> ProcessingResult:
        started_ns = time.monotonic_ns()
        received_ns = event_data.get("_received_monotonic_ns")
        source = platform or event_data.get("platform", "tiktok")
        if source == "youtube":
            result = self.youtube_comments.handle(event_data)
        elif source == "twitch":
            result = self.twitch_comments.handle(event_data)
        else:
            result = self.tiktok_comments.handle(event_data)
        self.watchdog.heartbeat()
        self.flush()
        finished_ns = time.monotonic_ns()
        if received_ns is not None:
            self.latency.observe_ns("chat_to_bridge_write", finished_ns - int(received_ns))
        self.latency.observe_ns("runtime_processing", finished_ns - started_ns)
        return result

    def handle_event(self, event: ChatEvent) -> ProcessingResult:
        started_ns = time.monotonic_ns()
        result = self.processor.process(event)
        self.watchdog.heartbeat()
        self.flush()
        self.latency.observe_ns("chat_to_bridge_write", time.monotonic_ns() - event.timestamp_ns)
        self.latency.observe_ns("runtime_processing", time.monotonic_ns() - started_ns)
        return result

    def heartbeat(self, now_ns: int | None = None) -> None:
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        self.watchdog.heartbeat(now_ns)
        if self.pipe is not None:
            self.pipe.send({"type": "heartbeat", "seq": self.sequence})

    def flush(self, now_ns: int | None = None) -> Submission | None:
        submission = self.engine.tick(now_ns)
        if submission is not None:
            self.sequence = max(self.sequence + 1, submission.sequence)
            if self.pipe is not None:
                self.pipe.send(submission.state.to_wire(self.sequence))
        return submission

    def clear(self) -> None:
        self.engine.clear_all()
        self.sequence += 1
        if self.pipe is not None:
            self.pipe.send({"type": "clear", "seq": self.sequence})

    def close(self) -> None:
        self.clear()
        if self.pipe is not None:
            self.pipe.send({"type": "shutdown"})
            self.pipe.close()
