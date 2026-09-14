import pytest

from tiktok_client import TikTokLiveManager


def test_tiktok_manager_strips_at_and_forwards_comment_shape():
    manager = TikTokLiveManager("@creator")
    received = []
    manager.on_event("comment", received.append)
    event = {"user": "viewer", "user_id": "42", "comment": "w fire"}
    manager._trigger_callbacks("comment", event)
    assert manager.username == "creator"
    assert received == [event]


def test_tiktok_manager_rejects_unused_event_types():
    manager = TikTokLiveManager("creator")
    with pytest.raises(ValueError):
        manager.on_event("gift", lambda _: None)
