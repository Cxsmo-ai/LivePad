"""Bridge normalized chat events into the parser, limiter, and state engine."""

from dataclasses import dataclass
import time

from controller.state_engine import StateEngine
from .normalized_event import ChatEvent
from .pad_protocol import PadFrame
from .parser import Command, CommandParser
from .rate_limiter import PerUserRateLimiter


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    accepted: tuple[Command | PadFrame, ...]
    rate_limited: tuple[Command | PadFrame, ...]
    invalid_tokens: tuple[str, ...]


class ChatCommandProcessor:
    def __init__(self, engine: StateEngine, parser: CommandParser | None = None,
                 limiter: PerUserRateLimiter | None = None):
        self.engine = engine
        self.parser = parser or CommandParser()
        self.limiter = limiter or PerUserRateLimiter()
        self._frame_order: dict[tuple[str, str], tuple[int, int]] = {}

    def process(self, event: ChatEvent, now_ns: int | None = None) -> ProcessingResult:
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        parsed = self.parser.parse(event.message)
        if parsed.pad_frame is not None:
            return self._process_frame(event, parsed.pad_frame, now_ns)
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

    def _process_frame(
        self, event: ChatEvent, frame: PadFrame, now_ns: int
    ) -> ProcessingResult:
        identity = (event.platform, event.user_id)
        previous = self._frame_order.get(identity)
        if previous is not None:
            previous_session, previous_sequence = previous
            if frame.session < previous_session or (
                frame.session == previous_session and frame.sequence <= previous_sequence
            ):
                return ProcessingResult((), (), ("stale-controller-frame",))

        # Record ordering even for a rate-limited frame so replaying the same public
        # chat message can never refresh a controller lease.
        self._frame_order.pop(identity, None)
        self._frame_order[identity] = (frame.session, frame.sequence)
        if len(self._frame_order) > 20_000:
            del self._frame_order[next(iter(self._frame_order))]
        limiter_identity = f"{event.platform}:{event.user_id}"
        if not self.limiter.allow(limiter_identity, "frame", now_ns):
            return ProcessingResult((), (frame,), ())

        owner = f"frame:{event.platform}:{event.user_id}"
        self.engine.replace_owner_frame(frame, owner, now_ns)
        return ProcessingResult((frame,), (), ())

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
