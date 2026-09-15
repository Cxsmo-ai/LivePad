from runtime import ControllerRuntime
from app_config import DEFAULT_CONFIG
from chat.normalized_event import ChatEvent


def test_runtime_flushes_only_changed_state_and_can_clear():
    runtime = ControllerRuntime()
    first = runtime.handle_comment({"user": "viewer", "user_id": "1", "comment": "w fire"})
    assert len(first.accepted) == 2
    submission = runtime.flush(1)
    assert submission is None
    assert runtime.engine.resolve().ly == 1
    runtime.clear()
    assert runtime.engine.resolve().ly == 0


def test_runtime_uses_configured_command_values():
    config = {**DEFAULT_CONFIG, "commands": {
        "go": {"action": "move_forward", "strength": 0.25, "duration_ms": 250}
    }}
    runtime = ControllerRuntime(config=config)
    result = runtime.handle_comment({"user": "viewer", "user_id": "1", "comment": "go"})
    assert result.accepted[0].strength == 0.25
    assert runtime.engine.resolve().ly == 0.25


def test_long_combo_starts_all_inputs_at_the_same_time():
    runtime = ControllerRuntime(config=DEFAULT_CONFIG)
    now_ns = 10_000_000_000
    result = runtime.processor.process(
        ChatEvent("viewer", "1", "w 80 10s sprint", now_ns),
        now_ns,
    )
    state = runtime.engine.resolve(now_ns)
    assert len(result.accepted) == 2
    assert state.ly == 0.8
    assert "l3" in state.buttons


def test_runtime_records_bounded_pipeline_latency_stages():
    runtime = ControllerRuntime(config=DEFAULT_CONFIG)
    now_ns = 10_000_000_000
    runtime.handle_comment({
        "user": "viewer", "user_id": "1", "comment": "w",
        "_received_monotonic_ns": now_ns,
    }, platform="tiktok")
    snapshot = runtime.latency.snapshot("chat_to_bridge_write")
    assert snapshot.samples == 1
    assert snapshot.latest_ms is not None
    assert runtime.latency.snapshot("runtime_processing").samples == 1
