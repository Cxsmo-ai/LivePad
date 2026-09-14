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


def test_processor_accepts_pad_frame_atomically_and_rejects_replay():
    engine = StateEngine()
    processor = ChatCommandProcessor(engine)
    event = ChatEvent(
        "viewer", "id-1", "hm1 mfr5z7k0 1 20,80,35,0,100,100 40 1 1200", 0,
        platform="twitch",
    )
    first = processor.process(event, 1)
    assert len(first.accepted) == 1
    state = engine.resolve(2)
    assert (state.lx, state.ly, state.rx, state.lt, state.rt) == (0.2, 0.8, 0.35, 1.0, 1.0)
    assert state.buttons == frozenset({"a", "l3"})

    replay = processor.process(event, 3)
    assert replay.accepted == ()
    assert replay.invalid_tokens == ("stale-controller-frame",)


def test_newer_session_wins_and_delayed_old_session_cannot_resurrect():
    engine = StateEngine()
    processor = ChatCommandProcessor(engine)
    base = dict(username="viewer", user_id="id-1", timestamp_ns=0, platform="youtube")
    processor.process(ChatEvent(message="hm1 100 5 0,100,0,0,0,0 0 0 3000", **base), 1)
    processor.process(ChatEvent(message="hm1 101 0 0,0,0,0,0,0 0 0 3000", **base), 1_000_000_001)
    delayed = processor.process(
        ChatEvent(message="hm1 100 6 0,100,0,0,0,0 0 0 3000", **base),
        2_000_000_001,
    )
    assert delayed.invalid_tokens == ("stale-controller-frame",)
    assert engine.resolve(2_000_000_002).ly == 0.0


def test_optional_extension_frames_and_original_typed_commands_coexist():
    engine = StateEngine()
    processor = ChatCommandProcessor(engine)
    frame = ChatEvent(
        "pad-viewer", "pad-1", "hm1 100 1 0,80,35,0,0,100 40 0 1200", 0,
        platform="twitch",
    )
    typed = ChatEvent(
        "typing-viewer", "typed-1", "ads jump", 0, platform="twitch"
    )
    assert len(processor.process(frame, 1).accepted) == 1
    assert [item.action for item in processor.process(typed, 2).accepted] == [
        "left_trigger", "button_a"
    ]
    state = engine.resolve(3)
    assert (state.ly, state.rx, state.lt, state.rt) == (0.8, 0.35, 1.0, 1.0)
    assert state.buttons == frozenset({"a", "l3"})
