from live_hardware_smoke_test import _is_compound_state, _is_neutral


def test_compound_xinput_state_detection():
    state = {
        "buttons": 0x0040,
        "left_trigger": 255,
        "right_trigger": 255,
        "left_x": 0,
        "left_y": -32768,
        "right_x": 11468,
        "right_y": 0,
    }
    assert _is_compound_state(state)
    assert not _is_neutral(state)


def test_neutral_xinput_state_detection_allows_rounding():
    state = {
        "buttons": 0,
        "left_trigger": 0,
        "right_trigger": 0,
        "left_x": -1,
        "left_y": 0,
        "right_x": -1,
        "right_y": 0,
    }
    assert _is_neutral(state)
    assert not _is_compound_state(state)
