import pytest

from tiktok_client import TikTokLiveManager


class _User:
    def __init__(self, **values):
        self.__dict__.update(values)


class _Event:
    def __init__(self, **values):
        self.__dict__.update(values)


def test_tiktok_manager_strips_at_and_forwards_comment_shape():
    manager = TikTokLiveManager("@creator")
    received = []
    manager.on_event("comment", received.append)
    event = {"user": "viewer", "user_id": "42", "comment": "w fire"}
    manager._trigger_callbacks("comment", event)
    assert manager.username == "creator"
    assert received == [event]


def test_tiktok_manager_accepts_profile_or_live_urls():
    assert TikTokLiveManager.normalize_username("@creator") == "creator"
    assert TikTokLiveManager.normalize_username("https://www.tiktok.com/@creator/live") == "creator"


def test_tiktok_manager_rejects_unused_event_types():
    manager = TikTokLiveManager("creator")
    with pytest.raises(ValueError):
        manager.on_event("gift", lambda _: None)


def test_tiktok_comment_normalization_handles_current_content_field():
    event = _Event(
        user=_User(display_name="Viewer", display_id="viewer-7"),
        content="run 80 1.2s",
        common=_Event(msg_id="message-1"),
    )
    assert TikTokLiveManager.normalize_comment_event(event) == {
        "user": "Viewer",
        "user_id": "viewer-7",
        "comment": "run 80 1.2s",
        "_event_id": "message-1",
    }


def test_tiktok_comment_normalization_survives_missing_user_and_empty_text():
    assert TikTokLiveManager.normalize_comment_event(_Event(content="w")) == {
        "user": "unknown",
        "user_id": "unknown",
        "comment": "w",
    }
    assert TikTokLiveManager.normalize_comment_event(_Event(content="   ")) is None


def test_tiktok_explicit_event_ids_are_deduplicated_without_blocking_same_text():
    manager = TikTokLiveManager("creator")
    assert manager._is_duplicate_event("message-1") is False
    assert manager._is_duplicate_event("message-1") is True
    assert manager._is_duplicate_event(None) is False
