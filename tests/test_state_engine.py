from chat.parser import Command
from controller.state import ControllerState
from controller.state_engine import StateEngine
import pytest


def test_overlapping_commands_resolve_in_one_state():
    engine = StateEngine()
    now = 1_000_000_000
    for action in ("move_forward", "button_l3", "left_trigger", "right_trigger", "look_right"):
        strength = 0.35 if action == "look_right" else 1.0
        engine.schedule(Command(action, strength, 500), "viewer", now)
    state = engine.resolve(now + 1)
    assert state == ControllerState(ly=1.0, rx=0.35, lt=1.0, rt=1.0, buttons=frozenset({"l3"}))


def test_leases_expire_and_clear():
    engine = StateEngine()
    engine.schedule(Command("button_a", 1, 100), "viewer", 0)
    assert engine.resolve(50_000_000).buttons == frozenset({"a"})
    assert engine.resolve(100_000_000).buttons == frozenset()
    engine.schedule(Command("move_forward", 1, 1000), "viewer", 0)
    assert engine.active_lease_count == 1
    engine.clear_all()
    assert engine.active_lease_count == 0
    assert engine.resolve(1).ly == 0


def test_axis_values_sum_and_clamp():
    engine = StateEngine()
    engine.schedule(Command("look_right", 0.8, 500), "a", 0)
    engine.schedule(Command("look_right", 0.8, 500), "b", 0)
    assert engine.resolve(1).rx == 1.0


def test_repeating_viewer_refreshes_instead_of_multiplying_vote():
    engine = StateEngine()
    engine.schedule(Command("move_forward", 1.0, 500), "viewer-a", 0)
    engine.schedule(Command("move_forward", 1.0, 500), "viewer-a", 1)
    engine.schedule(Command("move_backward", 1.0, 500), "viewer-b", 1)
    assert engine.active_lease_count == 2
    assert engine.resolve(2).ly == 0.0


def test_left_stick_diagonal_is_radially_normalized():
    engine = StateEngine()
    engine.schedule(Command("move_forward", 1.0, 500), "viewer-a", 0)
    engine.schedule(Command("strafe_right", 1.0, 500), "viewer-b", 0)
    state = engine.resolve(1)
    assert state.lx == pytest.approx(2 ** -0.5)
    assert state.ly == pytest.approx(2 ** -0.5)


def test_move_backward_resolves_to_negative_ly():
    engine = StateEngine()
    engine.schedule(Command("move_backward", 1.0, 500), "viewer", 0)
    state = engine.resolve(1)
    assert state.ly == -1.0


def test_dpad_and_guide_are_resolved_like_real_xbox_buttons():
    engine = StateEngine()
    for action in ("button_dpad_up", "button_dpad_right", "button_guide"):
        engine.schedule(Command(action, 1.0, 500), "viewer", 0)
    assert engine.resolve(1).buttons == frozenset({"dpad_up", "dpad_right", "guide"})
