import pytest

from chat.pad_protocol import BUTTON_BITS, parse_pad_frame
from chat.parser import CommandParser


def test_compact_pad_frame_parses_all_controller_domains():
    frame = parse_pad_frame("hm1 mfr5z7k0 2f -20,80,35,-10,75,100 41 5 1200")
    assert frame is not None
    assert frame.sequence == int("2f", 36)
    assert (frame.lx, frame.ly, frame.rx, frame.ry) == (-0.2, 0.8, 0.35, -0.1)
    assert (frame.lt, frame.rt) == (0.75, 1.0)
    assert frame.held_buttons == frozenset({"a", "l3"})
    assert frame.tap_buttons == frozenset({"a", "x"})
    assert frame.lease_ms == 1200


def test_optional_twitch_prefix_and_neutral_frame():
    result = CommandParser().parse("!hm1 abc 0 0,0,0,0,0,0 0 0 500")
    assert result.invalid_tokens == ()
    assert result.commands == ()
    assert result.pad_frame is not None and result.pad_frame.is_neutral


@pytest.mark.parametrize("message", [
    "hm1 abc 1 101,0,0,0,0,0 0 0 500",
    "hm1 abc 1 0,0,0,0,-1,0 0 0 500",
    "hm1 abc 1 0,0,0,0,0,0 8000 0 500",
    "hm1 abc 1 0,0,0,0,0,0 0 0 49",
    "hm1 abc 1 0,0,0,0,0 0 0 500",
])
def test_malformed_or_out_of_range_frames_are_rejected_atomically(message):
    result = CommandParser().parse(message)
    assert result.commands == ()
    assert result.pad_frame is None
    assert result.invalid_tokens == ("invalid-controller-frame",)


def test_button_bit_layout_is_stable():
    assert BUTTON_BITS["a"] == 0x0001
    assert BUTTON_BITS["x"] == 0x0004
    assert BUTTON_BITS["l3"] == 0x0040
    assert BUTTON_BITS["dpad_right"] == 0x4000


def test_chat_friendly_tiktok_frame_has_the_same_full_state_semantics():
    result = CommandParser().parse(
        "pad mu1k4879 q2f e1ao w80 a20 lr35 ld10 lt75 rt100 h41 t5"
    )
    frame = result.pad_frame
    assert result.invalid_tokens == ()
    assert frame is not None
    assert frame.sequence == int("2f", 36)
    assert frame.lease_ms == int("1ao", 36)
    assert (frame.lx, frame.ly, frame.rx, frame.ry) == (-0.2, 0.8, 0.35, -0.1)
    assert (frame.lt, frame.rt) == (0.75, 1.0)
    assert frame.held_buttons == frozenset({"a", "l3"})
    assert frame.tap_buttons == frozenset({"a", "x"})


@pytest.mark.parametrize("message", [
    "pad abc q1 e1ao w101",
    "pad abc q1 e1ao w80 s20",
    "pad abc q1 e1ao unknown1",
    "pad abc q1 e1ao h8000",
    "pad abc q1 e1 w80",
])
def test_invalid_friendly_frames_are_rejected_atomically(message):
    result = CommandParser().parse(message)
    assert result.pad_frame is None
    assert result.invalid_tokens == ("invalid-controller-frame",)
