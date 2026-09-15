"""Parser for the compact crowd-controller command language."""

from dataclasses import dataclass
from copy import deepcopy
import re
from typing import Any, Iterable, Mapping

from .commands import DEFAULT_COMMANDS
from .pad_protocol import PadFrame, parse_pad_frame


@dataclass(frozen=True, slots=True)
class Command:
    action: str
    strength: float = 1.0
    duration_ms: int = 400


@dataclass(frozen=True, slots=True)
class ParseResult:
    commands: tuple[Command, ...]
    invalid_tokens: tuple[str, ...]
    pad_frame: PadFrame | None = None


class CommandParser:
    """Parse all recognized commands in one comment; never stop at the first match."""

    _tokenize = re.compile(r"[^\s,;]+")
    _number = re.compile(r"^(\d+(?:\.\d+)?)%?$")
    _milliseconds = re.compile(r"^(\d+)ms$")
    _seconds = re.compile(r"^(\d+(?:\.\d+)?)s$")
    MIN_DURATION_MS = 10
    MAX_DURATION_MS = 10000

    def __init__(
        self,
        command_specs: Mapping[str, Mapping[str, Any]] | None = None,
        *,
        allow_seconds: bool = True,
    ):
        self.command_specs = deepcopy(dict(command_specs or DEFAULT_COMMANDS))
        self.allow_seconds = allow_seconds

    def parse(self, text: str) -> ParseResult:
        try:
            pad_frame = parse_pad_frame(text)
        except ValueError:
            return ParseResult((), ("invalid-controller-frame",))
        if pad_frame is not None:
            return ParseResult((), (), pad_frame)

        tokens = self._tokenize.findall(text.casefold())
        commands: list[Command] = []
        invalid: list[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            spec = self.command_specs.get(token)
            if spec is not None and spec.get("enabled", True):
                action = str(spec["action"])
                strength = float(spec.get("strength", 1.0))
                duration = int(spec.get("duration_ms", 400))
                consumed = 0
                reject_command = False

                # Digital buttons normally take a duration; they also accept
                # an optional ignored strength for uniform mixed combos.
                if action.startswith("button_") and spec.get("allow_duration_argument"):
                    arg1 = tokens[i + 1] if i + 1 < len(tokens) else None
                    arg2 = tokens[i + 2] if i + 2 < len(tokens) else None
                    # Accept the same readable strength+duration shape as
                    # analog commands. Digital controls ignore strength, but
                    # accepting it keeps mixed combos uniform, e.g.
                    # "w 75 900ms sprint 100 500ms".
                    if (
                        arg1 is not None
                        and arg2 is not None
                        and self._parse_strength(arg1) is not None
                    ):
                        parsed_dur = self._parse_duration(arg2)
                        if parsed_dur is not None:
                            duration = parsed_dur
                            consumed = 2
                        else:
                            invalid.append(arg2)
                            reject_command = True
                            consumed = 2
                    elif arg1 is not None:
                        parsed_dur = self._parse_duration(arg1)
                        if parsed_dur is not None:
                            duration = parsed_dur
                            consumed = 1
                        elif self._looks_numeric(arg1):
                            invalid.append(arg1)
                            reject_command = True
                            consumed = 1

                # Analog controls take strength then duration, or direct duration if strength is omitted.
                else:
                    arg1 = tokens[i + 1] if i + 1 < len(tokens) else None
                    if arg1 is not None:
                        if self._is_explicit_duration(arg1) and spec.get("allow_duration_argument"):
                            parsed_dur = self._parse_duration(arg1)
                            if parsed_dur is not None:
                                duration = parsed_dur
                                consumed = 1
                            elif self._looks_numeric(arg1):
                                invalid.append(arg1)
                                reject_command = True
                                consumed = 1
                        elif spec.get("allow_strength_argument"):
                            parsed = self._parse_strength(arg1)
                            if parsed is not None:
                                consumed = 1
                                strength = parsed
                                if spec.get("allow_duration_argument") and i + 2 < len(tokens):
                                    arg2 = tokens[i + 2]
                                    parsed_duration = self._parse_duration(arg2)
                                    if parsed_duration is not None:
                                        duration = parsed_duration
                                        consumed = 2
                                    elif self._looks_numeric(arg2):
                                        invalid.append(arg2)
                                        reject_command = True
                                        consumed = 2
                            elif self._looks_numeric(arg1):
                                invalid.append(arg1)
                                reject_command = True
                                consumed = 1

                if not reject_command:
                    commands.append(Command(action, self._clamp_strength(strength), duration))
                i += consumed + 1
                continue

            invalid.append(token)
            i += 1
        return ParseResult(tuple(commands), tuple(invalid))

    @classmethod
    def _parse_number(cls, token: str) -> float | None:
        match = cls._number.match(token)
        return float(match.group(1)) if match else None

    @classmethod
    def _parse_strength(cls, token: str) -> float | None:
        value = cls._parse_number(token)
        if value is None or not 1 <= value <= 100:
            return None
        return value / 100.0

    def _parse_duration(self, token: str) -> int | None:
        milliseconds = self._milliseconds.match(token)
        if milliseconds:
            value = int(milliseconds.group(1))
        elif self.allow_seconds:
            seconds = self._seconds.match(token)
            if seconds:
                value = round(float(seconds.group(1)) * 1000)
            else:
                try:
                    value = int(token)
                except ValueError:
                    return None
        else:
            try:
                value = int(token)
            except ValueError:
                return None
        return value if self.MIN_DURATION_MS <= value <= self.MAX_DURATION_MS else None

    def _looks_numeric(self, token: str) -> bool:
        return bool(
            self._number.match(token)
            or self._milliseconds.match(token)
            or self._seconds.match(token)
        )

    def _is_explicit_duration(self, token: str) -> bool:
        if self._milliseconds.match(token):
            return True
        if self.allow_seconds and self._seconds.match(token):
            return True
        return False

    @staticmethod
    def _clamp_strength(value: float) -> float:
        return max(0.0, min(1.0, value))


def parse_commands(text: str) -> Iterable[Command]:
    """Convenience API for callers that only need the recognized commands."""
    return CommandParser().parse(text).commands
