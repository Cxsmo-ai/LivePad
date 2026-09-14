from chat.parser import CommandParser


def test_compound_command_is_parsed_concurrently():
    result = CommandParser().parse("w sprint ads fire right 35")
    assert [command.action for command in result.commands] == [
        "move_forward", "button_l3", "left_trigger", "right_trigger", "look_right"
    ]
    assert result.commands[-1].strength == 0.35
    assert result.invalid_tokens == ()


def test_duration_and_invalid_tokens_are_bounded():
    result = CommandParser().parse("right 100 1500 banana left 999")
    assert result.commands[0].duration_ms == 1500
    assert len(result.commands) == 1
    assert result.invalid_tokens == ("banana", "999")


def test_single_buttons_have_short_default_lease():
    result = CommandParser().parse("jump reload")
    assert [(c.action, c.duration_ms) for c in result.commands] == [
        ("button_a", 120), ("button_x", 120)
    ]


def test_default_strengths_and_durations_match_cod_profile():
    commands = CommandParser().parse("right fire ads sprint").commands
    assert [(command.strength, command.duration_ms) for command in commands] == [
        (0.4, 150), (1.0, 180), (1.0, 600), (1.0, 500)
    ]


def test_chat_analog_arguments_are_percentages_including_one_percent():
    commands = CommandParser().parse("right 1 25 fire 50 180").commands
    assert commands[0].strength == 0.01
    assert commands[0].duration_ms == 25
    assert commands[1].strength == 0.5
    assert commands[1].duration_ms == 180


def test_custom_command_profile_is_used():
    parser = CommandParser({
        "go": {
            "action": "move_forward",
            "strength": 0.5,
            "duration_ms": 250,
            "enabled": True,
        }
    })
    result = parser.parse("go w")
    assert result.commands == (parser.parse("go").commands[0],)
    assert result.commands[0].strength == 0.5
    assert result.invalid_tokens == ("w",)


def test_cod_zombies_interact_and_movement_aliases():
    result = CommandParser().parse("interact buy revive x 1000 slide knife switch")
    actions = [c.action for c in result.commands]
    assert actions == [
        "button_x", "button_x", "button_x", "button_x", "button_b", "button_r3", "button_y"
    ]
    assert result.commands[2].duration_ms == 1500
    assert result.commands[3].duration_ms == 1000


def test_each_combo_action_has_independent_strength_and_duration():
    result = CommandParser().parse(
        "w 70% 900ms right 35% 250ms ads 80% 1200ms fire 100% 300ms jump 200ms"
    )
    assert [(c.action, c.strength, c.duration_ms) for c in result.commands] == [
        ("move_forward", 0.70, 900),
        ("look_right", 0.35, 250),
        ("left_trigger", 0.80, 1200),
        ("right_trigger", 1.00, 300),
        ("button_a", 1.00, 200),
    ]
    assert result.invalid_tokens == ()


def test_seconds_duration_suffix_and_legacy_bare_numbers():
    result = CommandParser().parse("left 25 400 interact 1.2s")
    assert [(c.action, c.strength, c.duration_ms) for c in result.commands] == [
        ("look_left", 0.25, 400),
        ("button_x", 1.0, 1200),
    ]


def test_every_extra_xbox_control_has_a_chat_command():
    result = CommandParser().parse(
        "start view guide dpadup dpaddown dpadleft dpadright"
    )
    assert [command.action for command in result.commands] == [
        "button_start",
        "button_back",
        "button_guide",
        "button_dpad_up",
        "button_dpad_down",
        "button_dpad_left",
        "button_dpad_right",
    ]
    assert result.invalid_tokens == ()
