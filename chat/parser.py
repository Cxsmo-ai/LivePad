"""Parser for the compact crowd-controller command language."""

from dataclasses import dataclass
from copy import deepcopy
import re
from typing import Any, Iterable, Mapping

from .commands import COMBO_ALIASES, DEFAULT_COMMANDS
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

    _tokenize = re.compile(r"[^\s,;+]+")
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

        tokens = [
            token[1:] if token.startswith("!") and len(token) > 1 else token
            for token in self._tokenize.findall(text.casefold())
        ]
        commands: list[Command] = []
        invalid: list[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            combo = COMBO_ALIASES.get(token)
            if combo:
                first, consumed, first_invalid = self._parse_one(tokens, i, combo[0])
                invalid.extend(first_invalid)
                if first is not None:
                    commands.append(first)
                    for target in combo[1:]:
                        follow_up, _, follow_up_invalid = self._parse_one(
                            (target,), 0, target, parse_modifiers=False
                        )
                        invalid.extend(follow_up_invalid)
                        if follow_up is not None:
                            commands.append(follow_up)
                i += consumed + 1
                continue

            command, consumed, command_invalid = self._parse_one(tokens, i, token)
            invalid.extend(command_invalid)
            if command is not None:
                commands.append(command)
            i += consumed + 1
        return ParseResult(tuple(commands), tuple(invalid))

    def _parse_one(
        self,
        tokens: tuple[str, ...] | list[str],
        index: int,
        token: str,
        *,
        parse_modifiers: bool = True,
    ) -> tuple[Command | None, int, tuple[str, ...]]:
        """Parse one command and return (command, consumed-after-token, invalid)."""
        spec = self.command_specs.get(token)
        if spec is None or not spec.get("enabled", True):
            return None, 0, (token,)

        action = str(spec["action"])
        strength = float(spec.get("strength", 1.0))
        duration = int(spec.get("duration_ms", 400))
        consumed = 0
        invalid: list[str] = []
        reject_command = False
        if not parse_modifiers:
            return Command(action, self._clamp_strength(strength), duration), 0, ()

        arg1 = tokens[index + 1] if index + 1 < len(tokens) else None
        arg2 = tokens[index + 2] if index + 2 < len(tokens) else None

        # Digital buttons accept an optional duration.  A strength before the
        # duration is accepted and ignored so mixed macros remain predictable.
        if action.startswith("button_") and spec.get("allow_duration_argument"):
            if arg1 is not None and arg2 is not None and self._parse_strength(arg1) is not None:
                parsed_duration = self._parse_duration(arg2)
                if parsed_duration is not None:
                    duration, consumed = parsed_duration, 2
                else:
                    invalid.append(arg2)
                    consumed = 2
                    reject_command = True
            elif arg1 is not None:
                parsed_duration = self._parse_duration(arg1)
                if parsed_duration is not None:
                    duration, consumed = parsed_duration, 1
                elif self._looks_numeric(arg1):
                    invalid.append(arg1)
                    consumed = 1
                    reject_command = True
        # Analog controls and triggers accept strength then duration, or a
        # direct explicit duration. Bare numbers remain strengths so a typo
        # cannot silently turn into a long hold; use 500ms/1.2s for time.
        elif spec.get("allow_strength_argument"):
            if arg1 is not None:
                if self._is_explicit_duration(arg1):
                    parsed_duration = self._parse_duration(arg1)
                    if parsed_duration is not None:
                        duration, consumed = parsed_duration, 1
                    elif self._looks_numeric(arg1):
                        invalid.append(arg1)
                        consumed = 1
                        reject_command = True
                else:
                    parsed_strength = self._parse_strength(arg1)
                    if parsed_strength is not None:
                        strength, consumed = parsed_strength, 1
                        if arg2 is not None and spec.get("allow_duration_argument"):
                            parsed_duration = self._parse_duration(arg2)
                            if parsed_duration is not None:
                                duration, consumed = parsed_duration, 2
                            elif self._looks_numeric(arg2):
                                invalid.append(arg2)
                                consumed = 2
                                reject_command = True
                    elif self._looks_numeric(arg1):
                        invalid.append(arg1)
                        consumed = 1
                        reject_command = True

        if reject_command:
            return None, consumed, tuple(invalid)
        return Command(action, self._clamp_strength(strength), duration), consumed, tuple(invalid)

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
