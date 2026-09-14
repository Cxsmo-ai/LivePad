from chat.youtube_adapter import YouTubeCommentAdapter
from chat.processor import ChatCommandProcessor
from controller.state_engine import StateEngine
from runtime import ControllerRuntime


def test_youtube_adapter_normalized_event():
    engine = StateEngine()
    processor = ChatCommandProcessor(engine)
    adapter = YouTubeCommentAdapter(processor)
    result = adapter.handle({"user": "YTViewer", "user_id": "UC123", "comment": "w ads fire right 35"})
    assert len(result.accepted) == 4
    assert [c.action for c in result.accepted] == ["move_forward", "left_trigger", "right_trigger", "look_right"]


def test_runtime_handles_youtube_and_tiktok_together():
    runtime = ControllerRuntime()
    # TikTok comment
    tt_res = runtime.handle_comment({"user": "TTUser", "user_id": "1", "comment": "w"}, platform="tiktok")
    assert len(tt_res.accepted) == 1
    # YouTube comment
    yt_res = runtime.handle_comment({"user": "YTUser", "user_id": "2", "comment": "ads fire"}, platform="youtube")
    assert len(yt_res.accepted) == 2
    state = runtime.engine.resolve()
    assert state.ly == 1.0
    assert state.lt == 1.0
    assert state.rt == 1.0

