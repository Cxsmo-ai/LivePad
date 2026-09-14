import pytest
from youtube_client import resolve_live_url, select_live_view, parse_action_to_comment


def test_resolve_live_url():
    assert resolve_live_url("@LofiGirl") == "https://www.youtube.com/@LofiGirl/live"
    assert resolve_live_url("LofiGirl") == "https://www.youtube.com/@LofiGirl/live"
    assert resolve_live_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert resolve_live_url("https://youtu.be/dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert resolve_live_url("UC12345678901234567890123") == "https://www.youtube.com/channel/UC12345678901234567890123/live"
    assert resolve_live_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_parse_action_to_comment_standard():
    action = {
        "addChatItemAction": {
            "item": {
                "liveChatTextMessageRenderer": {
                    "authorName": {"simpleText": "Gamer123"},
                    "authorExternalChannelId": "UC_channel_123",
                    "message": {
                        "runs": [
                            {"text": "w sprint "},
                            {"text": "ads fire"}
                        ]
                    },
                    "timestampUsec": "1726000000000000"
                }
            }
        }
    }
    parsed = parse_action_to_comment(action)
    assert parsed is not None
    assert parsed["user"] == "Gamer123"
    assert parsed["user_id"] == "UC_channel_123"
    assert parsed["comment"] == "w sprint ads fire"
    assert parsed["platform"] == "youtube"


def test_select_live_view_toggle():
    # Sample dummy byte sequence containing 0x08 0x04
    import base64
    raw = b"prefix" + bytes([0x08, 0x04]) + b"suffix"
    encoded = base64.urlsafe_b64encode(raw).decode("ascii")
    modified = select_live_view(encoded)
    decoded_mod = base64.urlsafe_b64decode(modified + "==")
    assert bytes([0x08, 0x01]) in decoded_mod

