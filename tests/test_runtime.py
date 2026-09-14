from runtime import ControllerRuntime
from app_config import DEFAULT_CONFIG


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
