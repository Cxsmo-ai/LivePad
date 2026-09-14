import json

import pytest

from app_config import AppConfig


def test_config_saves_atomically_and_retains_backup(tmp_path):
    path = tmp_path / "chat_gamepad.json"
    config = AppConfig(path)
    config.load()
    config.data["tiktok"]["username"] = "first"
    config.save()
    config.data["tiktok"]["username"] = "second"
    config.save()
    assert json.loads(path.read_text())["tiktok"]["username"] == "second"
    assert json.loads(config.backup_path.read_text())["tiktok"]["username"] == "first"
    assert not path.with_suffix(".json.tmp").exists()


def test_config_rejects_unsafe_duration(tmp_path):
    config = AppConfig(tmp_path / "chat_gamepad.json")
    config.data["commands"]["w"]["duration_ms"] = 99999
    with pytest.raises(ValueError):
        config.save()


def test_invalid_primary_recovers_from_backup_without_losing_it(tmp_path):
    path = tmp_path / "chat_gamepad.json"
    config = AppConfig(path)
    config.load()
    config.data["tiktok"]["username"] = "known-good"
    config.save()
    config.save()
    path.write_text("{not json", encoding="utf-8")

    recovered = AppConfig(path)
    data = recovered.load()

    assert data["tiktok"]["username"] == "known-good"
    assert recovered.last_recovery is not None
    assert (tmp_path / "chat_gamepad.invalid.json").read_text(encoding="utf-8") == "{not json"


def test_v1_config_migrates_modifier_capabilities_without_losing_edits(tmp_path):
    path = tmp_path / "chat_gamepad.json"
    config = AppConfig(path)
    config.load()
    old = config.data
    old["schema_version"] = 1
    old["commands"]["w"]["strength"] = 0.65
    old["commands"]["w"]["duration_ms"] = 777
    old["commands"]["w"]["enabled"] = False
    old["commands"]["w"]["allow_strength_argument"] = False
    old["commands"]["w"]["allow_duration_argument"] = False
    path.write_text(json.dumps(old), encoding="utf-8")

    migrated = AppConfig(path)
    data = migrated.load()

    assert data["schema_version"] == 2
    assert data["commands"]["w"]["strength"] == 0.65
    assert data["commands"]["w"]["duration_ms"] == 777
    assert data["commands"]["w"]["enabled"] is False
    assert data["commands"]["w"]["allow_strength_argument"] is True
    assert data["commands"]["w"]["allow_duration_argument"] is True
