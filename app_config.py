"""Validated, atomic configuration for LivePad."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
from typing import Any

from chat.commands import DEFAULT_COMMANDS, SUPPORTED_ACTIONS


DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 2,
    "app_name": "LivePad",
    "tiktok": {"enabled": True, "username": "", "auto_reconnect": True},
    "youtube": {"enabled": True, "target": "", "chat_type": "live", "auto_reconnect": True},
    "twitch": {"enabled": False, "channel": "", "auto_reconnect": True},
    "controller": {"profile": "xbox-360-wired", "scheduler_hz": 1000, "allow_seconds": True},
    "crowd": {"mode": "balanced", "movement_window_ms": 60},
    "commands": deepcopy(DEFAULT_COMMANDS),
}


class AppConfig:
    def __init__(self, path: str | Path = "chat_gamepad.json"):
        self.path = Path(path)
        self.backup_path = self.path.with_name(f"{self.path.stem}.backup{self.path.suffix}")
        self.data = deepcopy(DEFAULT_CONFIG)
        self.last_recovery: str | None = None

    def load(self) -> dict[str, Any]:
        self.last_recovery = None
        if not self.path.exists():
            self.save()
            return self.data
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            loaded, migrated = self._migrate(loaded)
            self._validate(loaded)
            self.data = self._merge(deepcopy(DEFAULT_CONFIG), loaded)
            if migrated:
                self.save()
                self.last_recovery = "Updated command modifiers to configuration version 2"
            return self.data
        except (json.JSONDecodeError, ValueError, TypeError) as primary_error:
            if self.backup_path.exists():
                try:
                    loaded = json.loads(self.backup_path.read_text(encoding="utf-8"))
                    loaded, _ = self._migrate(loaded)
                    self._validate(loaded)
                    self.data = self._merge(deepcopy(DEFAULT_CONFIG), loaded)
                    invalid_path = self._preserve_invalid_primary()
                    self.save()
                    self.last_recovery = f"Recovered configuration from backup; invalid file kept at {invalid_path.name}"
                    return self.data
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            invalid_path = self._preserve_invalid_primary()
            self.data = deepcopy(DEFAULT_CONFIG)
            self.save()
            self.last_recovery = (
                f"Reset invalid configuration ({primary_error}); old file kept at {invalid_path.name}"
            )
            return self.data

    def _preserve_invalid_primary(self) -> Path:
        candidate = self.path.with_name(f"{self.path.stem}.invalid{self.path.suffix}")
        counter = 1
        while candidate.exists():
            candidate = self.path.with_name(
                f"{self.path.stem}.invalid-{counter}{self.path.suffix}"
            )
            counter += 1
        os.replace(self.path, candidate)
        return candidate

    def save(self) -> None:
        self.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(self.data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if self.path.exists():
            shutil.copy2(self.path, self.backup_path)
        os.replace(temporary, self.path)

    def validate(self, data: dict[str, Any] | None = None) -> None:
        self._validate(self.data if data is None else data)

    @staticmethod
    def _validate(data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("configuration root must be an object")
        if data.get("schema_version") != 2:
            raise ValueError("unsupported config schema_version")
        tiktok = data.get("tiktok", {})
        if not isinstance(tiktok, dict):
            raise ValueError("tiktok must be an object")
        if "enabled" in tiktok and not isinstance(tiktok["enabled"], bool):
            raise ValueError("tiktok.enabled must be a boolean")
        youtube = data.get("youtube", {})
        if not isinstance(youtube, dict):
            raise ValueError("youtube must be an object")
        if "enabled" in youtube and not isinstance(youtube["enabled"], bool):
            raise ValueError("youtube.enabled must be a boolean")
        if "chat_type" in youtube and youtube["chat_type"] not in ("live", "top"):
            raise ValueError("youtube.chat_type must be 'live' or 'top'")
        twitch = data.get("twitch", {})
        if not isinstance(twitch, dict):
            raise ValueError("twitch must be an object")
        if "enabled" in twitch and not isinstance(twitch["enabled"], bool):
            raise ValueError("twitch.enabled must be a boolean")
        controller = data.get("controller", {})
        hz = controller.get("scheduler_hz", 0)
        if not isinstance(hz, int) or not 50 <= hz <= 1000:
            raise ValueError("controller.scheduler_hz must be between 50 and 1000")
        if controller.get("profile") != "xbox-360-wired":
            raise ValueError("only the xbox-360-wired profile is supported")
        if "allow_seconds" in controller and not isinstance(controller["allow_seconds"], bool):
            raise ValueError("controller.allow_seconds must be a boolean")
        commands = data.get("commands", {})
        if not isinstance(commands, dict):
            raise ValueError("commands must be an object")
        for name, command in commands.items():
            if not isinstance(command, dict):
                raise ValueError(f"commands.{name} must be an object")
            if not isinstance(name, str) or not name.strip() or any(character.isspace() for character in name):
                raise ValueError("command names must be non-empty single tokens")
            if command.get("action") not in SUPPORTED_ACTIONS:
                raise ValueError(f"commands.{name}.action is unsupported")
            strength = command.get("strength", 0)
            duration = command.get("duration_ms", 0)
            if not isinstance(strength, (int, float)) or not 0 <= strength <= 1:
                raise ValueError(f"commands.{name}.strength must be in [0, 1]")
            if not isinstance(duration, int) or not 10 <= duration <= 10000:
                raise ValueError(f"commands.{name}.duration_ms must be between 10 and 10000")
            for flag in ("enabled", "allow_strength_argument", "allow_duration_argument"):
                if flag in command and not isinstance(command[flag], bool):
                    raise ValueError(f"commands.{name}.{flag} must be true or false")

    @classmethod
    def _merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = cls._merge(base[key], value)
            else:
                base[key] = value
        return base

    @staticmethod
    def _migrate(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Upgrade v1 configs while preserving edited strengths, durations, and enabled flags."""
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            return data, False
        migrated = deepcopy(data)
        migrated["schema_version"] = 2
        commands = migrated.setdefault("commands", {})
        for name, default in DEFAULT_COMMANDS.items():
            command = commands.setdefault(name, deepcopy(default))
            command["allow_strength_argument"] = default["allow_strength_argument"]
            command["allow_duration_argument"] = default["allow_duration_argument"]
        return migrated, True
