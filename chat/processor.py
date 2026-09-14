"""Bridge normalized chat events into the parser, limiter, and state engine."""

from dataclasses import dataclass
import time

from controller.state_engine import StateEngine
from .normalized_event import ChatEvent
from .parser import Command, CommandParser
from .rate_limiter import PerUserRateLimiter


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    accepted: tuple[Command, ...]
    rate_limited: tuple[Command, ...]
    invalid_tokens: tuple[str, ...]


class ChatCommandProcessor:
    def __init__(self, engine: StateEngine, parser: CommandParser | None = None,
                 limiter: PerUserRateLimiter | None = None):
        self.engine = engine
        self.parser = parser or CommandParser()
        self.limiter = limiter or PerUserRateLimiter()

    def process(self, event: ChatEvent, now_ns: int | None = None) -> ProcessingResult:
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        parsed = self.parser.parse(event.message)
        accepted: list[Command] = []
        rate_limited: list[Command] = []
        for command in parsed.commands:
            category = self._category(command)
            if self.limiter.allow(event.user_id, category, now_ns):
                self.engine.schedule(command, event.user_id, now_ns)
                accepted.append(command)
            else:
                rate_limited.append(command)
        return ProcessingResult(tuple(accepted), tuple(rate_limited), parsed.invalid_tokens)

    @staticmethod
    def _category(command: Command) -> str:
        if command.action.startswith(("move_", "strafe_")):
            return "movement"
        if command.action.startswith("look_"):
            return "camera"
        if command.action.startswith("button_"):
            return "button"
        if command.action.endswith("_trigger"):
            return "trigger"
        raise ValueError(f"unknown command category: {command.action}")
