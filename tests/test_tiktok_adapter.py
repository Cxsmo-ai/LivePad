from chat.tiktok_adapter import TikTokCommentAdapter
from controller.state_engine import StateEngine
from chat.processor import ChatCommandProcessor


def test_tiktok_callback_is_normalized_without_mutating_text():
    adapter = TikTokCommentAdapter(ChatCommandProcessor(StateEngine()))
    result = adapter.handle({"user": "Luke", "user_id": "42", "comment": "W SPRINT"})
    assert [command.action for command in result.accepted] == ["move_forward", "button_l3"]
