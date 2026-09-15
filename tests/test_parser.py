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


def test_short_command_duration_floor_is_ten_milliseconds():
    accepted = CommandParser().parse("right 1 10ms")
    assert accepted.commands[0].duration_ms == 10
    rejected = CommandParser().parse("right 1 9ms")
    assert rejected.commands == ()
    assert rejected.invalid_tokens == ("9ms",)


def test_invalid_direct_analog_duration_is_reported_without_scheduling_command():
    result = CommandParser().parse("right 9ms")
    assert result.commands == ()
    assert result.invalid_tokens == ("9ms",)


def test_long_compound_commands_have_no_queue_delay():
    result = CommandParser().parse("w 80 10s sprint")
    assert [(command.action, command.strength, command.duration_ms) for command in result.commands] == [
        ("move_forward", 0.8, 10000), ("button_l3", 1.0, 500)
    ]


def test_digital_commands_accept_uniform_strength_and_duration_modifiers():
    result = CommandParser().parse("w 75 900ms sprint 100 500ms ads 80 1200ms fire 100 300ms")
    assert [(command.action, command.strength, command.duration_ms) for command in result.commands] == [
        ("move_forward", 0.75, 900),
        ("button_l3", 1.0, 500),
        ("left_trigger", 0.8, 1200),
        ("right_trigger", 1.0, 300),
    ]
    assert result.invalid_tokens == ()


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


def test_bare_numbers_without_percent_and_direct_duration_without_strength():
    parser = CommandParser(allow_seconds=True)

    # Strength + duration in seconds + action
    res1 = parser.parse("w 80 1.2s sprint")
    assert [(c.action, c.strength, c.duration_ms) for c in res1.commands] == [
        ("move_forward", 0.8, 1200), ("button_l3", 1.0, 500)
    ]
    assert res1.invalid_tokens == ()

    # Omitted strength with seconds duration -> default strength
    res2 = parser.parse("w 1.2s sprint")
    assert [(c.action, c.strength, c.duration_ms) for c in res2.commands] == [
        ("move_forward", 1.0, 1200), ("button_l3", 1.0, 500)
    ]
    assert res2.invalid_tokens == ()

    # Omitted strength with ms duration -> default strength
    res3 = parser.parse("w 500ms sprint")
    assert [(c.action, c.strength, c.duration_ms) for c in res3.commands] == [
        ("move_forward", 1.0, 500), ("button_l3", 1.0, 500)
    ]

    # Bare number <= 100 with no % -> strength only, default duration
    res5 = parser.parse("w 80 sprint")
    assert [(c.action, c.strength, c.duration_ms) for c in res5.commands] == [
        ("move_forward", 0.8, 400), ("button_l3", 1.0, 500)
    ]

    # Camera with direct duration vs strength
    res6 = parser.parse("right 250ms")
    assert [(c.action, c.strength, c.duration_ms) for c in res6.commands] == [
        ("look_right", 0.4, 250)
    ]

    res7 = parser.parse("right 35")
    assert [(c.action, c.strength, c.duration_ms) for c in res7.commands] == [
        ("look_right", 0.35, 150)
    ]


def test_one_word_macros_expand_to_concurrent_commands_and_accept_modifiers():
    result = CommandParser().parse("run 80 1.2s")
    assert [(command.action, command.strength, command.duration_ms) for command in result.commands] == [
        ("move_forward", 0.8, 1200),
        ("button_l3", 1.0, 500),
    ]
    assert result.invalid_tokens == ()

    result = CommandParser().parse("runaimfire")
    assert [command.action for command in result.commands] == [
        "move_forward", "button_l3", "left_trigger", "right_trigger"
    ]


def test_chat_friendly_short_forms_prefixes_and_plus_separators():
    result = CommandParser().parse("!fwd+sp+lt+rt+facea+du")
    assert [command.action for command in result.commands] == [
        "move_forward", "button_l3", "left_trigger", "right_trigger",
        "button_a", "button_dpad_up",
    ]
    assert result.invalid_tokens == ()


def test_natural_language_aliases_and_fast_macros_are_chat_friendly():
    result = CommandParser().parse("walk duck attack frag monkey go 75 900ms aimfire")
    assert [command.action for command in result.commands] == [
        "move_forward", "button_b", "right_trigger", "button_rb", "button_lb",
        "move_forward", "button_l3", "left_trigger", "right_trigger",
    ]
    assert result.commands[5].strength == 0.75
    assert result.commands[5].duration_ms == 900
    assert result.invalid_tokens == ()


def test_seconds_toggle_disables_seconds_syntax():
    parser_ms_only = CommandParser(allow_seconds=False)

    # 1.2s should be rejected when seconds toggle is disabled
    res1 = parser_ms_only.parse("w 1.2s sprint")
    assert [(c.action, c.strength, c.duration_ms) for c in res1.commands] == [
        ("button_l3", 1.0, 500)
    ]
    assert res1.invalid_tokens == ("1.2s",)

    # ms syntax still works
    res2 = parser_ms_only.parse("w 500ms sprint")
    assert [(c.action, c.strength, c.duration_ms) for c in res2.commands] == [
        ("move_forward", 1.0, 500), ("button_l3", 1.0, 500)
    ]
    assert res2.invalid_tokens == ()
