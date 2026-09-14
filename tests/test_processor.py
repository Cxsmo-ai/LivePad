from chat.normalized_event import ChatEvent
from chat.processor import ChatCommandProcessor
from controller.state_engine import StateEngine


def test_processor_accepts_compound_comment_and_tracks_invalid_tokens():
    engine = StateEngine()
    processor = ChatCommandProcessor(engine)
    result = processor.process(ChatEvent("viewer", "id-1", "w sprint ads fire right 35 banana", 0), 1)
    assert len(result.accepted) == 5
    assert result.invalid_tokens == ("banana",)
    state = engine.resolve(2)
    assert state.ly == 1
    assert state.rx == 0.35
    assert state.lt == 1
    assert state.rt == 1
    assert state.buttons == frozenset({"l3"})
