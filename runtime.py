"""Runtime glue for chat events, state resolution, and the optional bridge."""

from __future__ import annotations

import time
from typing import Any, Mapping

from chat.normalized_event import ChatEvent
from chat.processor import ChatCommandProcessor, ProcessingResult
from chat.tiktok_adapter import TikTokCommentAdapter
from controller.safety import SafetyWatchdog
from controller.state_engine import StateEngine, Submission
from ipc.named_pipe import NamedPipeClient


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
            parser = CommandParser(config.get("commands"))
        self.processor = ChatCommandProcessor(self.engine, parser=parser)
        self.comments = TikTokCommentAdapter(self.processor)
        self.watchdog = SafetyWatchdog()
        self.pipe = pipe
        self.sequence = 0

    def start(self) -> None:
        if self.pipe is not None:
            self.pipe.connect()
            ready = self.pipe.receive()
            if ready.get("type") != "ready":
                raise RuntimeError(f"unexpected bridge handshake: {ready}")
        self.watchdog.heartbeat()

    def handle_comment(self, event_data: dict) -> ProcessingResult:
        result = self.comments.handle(event_data)
        self.watchdog.heartbeat()
        self.flush()
        return result

    def handle_event(self, event: ChatEvent) -> ProcessingResult:
        result = self.processor.process(event)
        self.watchdog.heartbeat()
        self.flush()
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
                self.pipe.send({"type": "state", **submission.state.to_wire(self.sequence)})
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
