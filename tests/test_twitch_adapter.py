from app_config import DEFAULT_CONFIG
from runtime import ControllerRuntime


def test_runtime_handles_twitch_with_platform_scoped_identity():
    runtime = ControllerRuntime(config=DEFAULT_CONFIG)
    seen_user_ids: list[str] = []
    original_process = runtime.processor.process

    def capture(event, now_ns=None):
        seen_user_ids.append(event.user_id)
        return original_process(event, now_ns)

    runtime.processor.process = capture
    result = runtime.handle_comment({
        "platform": "twitch",
        "user": "Viewer",
        "display_name": "Viewer",
        "user_id": "123",
        "comment": "!w fire",
    })
    assert [command.action for command in result.accepted] == [
        "move_forward", "right_trigger"
    ]
    assert seen_user_ids == ["tw:123"]
