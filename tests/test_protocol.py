from controller.state import ControllerState
from ipc.protocol import decode_message, encode_state


def test_state_protocol_is_newline_delimited_json():
    payload = encode_state(ControllerState(ly=1, buttons=frozenset({"l3"})), 42)
    assert payload.endswith(b"\n")
    message = decode_message(payload)
    assert message["type"] == "state"
    assert message["seq"] == 42
    assert message["buttons"] == ["l3"]
