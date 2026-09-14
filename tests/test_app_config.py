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
