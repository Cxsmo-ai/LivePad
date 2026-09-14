"""Parser for the compact crowd-controller command language."""

from dataclasses import dataclass
from copy import deepcopy
import re
from typing import Any, Iterable, Mapping

from .commands import DEFAULT_COMMANDS


@dataclass(frozen=True, slots=True)
class Command:
    action: str
    strength: float = 1.0
    duration_ms: int = 400


@dataclass(frozen=True, slots=True)
class ParseResult:
    commands: tuple[Command, ...]
    invalid_tokens: tuple[str, ...]


class CommandParser:
    """Parse all recognized commands in one comment; never stop at the first match."""

    _number = re.compile(r"^(\d+(?:\.\d+)?)%?$")

    def __init__(self, command_specs: Mapping[str, Mapping[str, Any]] | None = None):
        self.command_specs = deepcopy(dict(command_specs or DEFAULT_COMMANDS))

    def parse(self, text: str) -> ParseResult:
        tokens = re.findall(r"[^\s,;]+", text.casefold())
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
                if spec.get("allow_strength_argument") and i + 1 < len(tokens):
                    parsed = self._parse_number(tokens[i + 1])
                    if parsed is not None:
                        consumed = 1
                        if not 1 <= parsed <= 100:
                            invalid.append(tokens[i + 1])
                            reject_command = True
                        else:
                            strength = parsed / 100.0
                if spec.get("allow_duration_argument") and i + 2 < len(tokens) and consumed:
                    parsed_duration = self._parse_integer(tokens[i + 2])
                    if parsed_duration is not None:
                        duration = parsed_duration
                        consumed = 2
                    elif self._parse_number(tokens[i + 2]) is not None:
                        invalid.append(tokens[i + 2])
                        reject_command = True
                        consumed = 2
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

    @staticmethod
    def _parse_integer(token: str) -> int | None:
        try:
            value = int(token)
        except ValueError:
            return None
        return value if 25 <= value <= 1500 else None

    @staticmethod
    def _clamp_strength(value: float) -> float:
        return max(0.0, min(1.0, value))


def parse_commands(text: str) -> Iterable[Command]:
    """Convenience API for callers that only need the recognized commands."""

    return CommandParser().parse(text).commands
