import asyncio

import pytest
import websockets

from twitch_client import (
    TwitchLiveManager,
    normalize_channel,
    normalize_privmsg,
    parse_badges,
    parse_irc_line,
)


PRIVMSG = (
    "@badge-info=subscriber/12;badges=subscriber/12;display-name=Jeff\\sPlays;"
    "first-msg=0;id=message-123;mod=0;subscriber=1;tmi-sent-ts=1720000000000;"
    "user-id=123456789;vip=0 "
    ":user!user@user.tmi.twitch.tv PRIVMSG #fazeclanluke :w sprint ads fire"
)


def test_irc_parser_handles_tags_prefix_trailing_text_and_escapes():
    parsed = parse_irc_line(PRIVMSG)
    assert parsed.command == "PRIVMSG"
    assert parsed.prefix == "user!user@user.tmi.twitch.tv"
    assert parsed.params == ("#fazeclanluke", "w sprint ads fire")
    assert parsed.tags["display-name"] == "Jeff Plays"


def test_privmsg_normalizes_identity_badges_and_permissions():
    event = normalize_privmsg(parse_irc_line(PRIVMSG))
    assert event == {
        "platform": "twitch",
        "message_id": "message-123",
        "user": "Jeff Plays",
        "user_id": "123456789",
        "username": "user",
        "display_name": "Jeff Plays",
        "comment": "w sprint ads fire",
        "channel": "fazeclanluke",
        "badges": {"subscriber": "12"},
        "moderator": False,
        "subscriber": True,
        "vip": False,
        "first_message": False,
        "timestamp_ms": 1720000000000,
    }


def test_badge_and_channel_parsing_are_bounded():
    assert parse_badges("broadcaster/1,subscriber/24") == {
        "broadcaster": "1", "subscriber": "24"
    }
    assert normalize_channel("@FaZeClanLuke") == "fazeclanluke"
    with pytest.raises(ValueError):
        normalize_channel("not a channel!")


def test_twitch_action_message_wrapper_is_removed():
    action_line = (
        "@display-name=Viewer;id=action-1;user-id=5 "
        ":viewer!viewer@viewer.tmi.twitch.tv PRIVMSG #fazeclanluke "
        ":\x01ACTION !w sprint\x01"
    )
    event = normalize_privmsg(parse_irc_line(action_line))
    assert event is not None
    assert event["comment"] == "!w sprint"


def test_local_websocket_handshake_ping_and_message_deduplication():
    async def scenario() -> None:
        client_lines: list[str] = []
        pong_lines: list[str] = []
        comments: list[dict] = []
        connections: list[dict] = []
        comment_received = asyncio.Event()

        async def handler(websocket) -> None:
            for _ in range(4):
                client_lines.append((await websocket.recv()).strip())
            await websocket.send(
                ":tmi.twitch.tv CAP * ACK :twitch.tv/tags twitch.tv/commands\r\n"
                "@slow=0;room-id=123 :tmi.twitch.tv ROOMSTATE #fazeclanluke\r\n"
                "PING :tmi.twitch.tv\r\n"
            )
            pong_lines.append((await asyncio.wait_for(websocket.recv(), 1)).strip())
            await websocket.send(PRIVMSG + "\r\n" + PRIVMSG + "\r\n")
            await asyncio.wait_for(comment_received.wait(), 1)
            await websocket.wait_closed()

        async with websockets.serve(handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            manager = TwitchLiveManager(
                "FaZeClanLuke", websocket_url=f"ws://127.0.0.1:{port}"
            )
            manager.on_event("connect", connections.append)

            def on_comment(event: dict) -> None:
                comments.append(event)
                comment_received.set()

            manager.on_event("comment", on_comment)
            task = asyncio.create_task(manager.connect())
            await asyncio.wait_for(comment_received.wait(), 2)
            await manager.disconnect()
            await asyncio.wait_for(task, 2)

        assert client_lines[0] == "PASS SCHMOOPIIE"
        assert client_lines[1].startswith("NICK justinfan")
        assert client_lines[2] == "CAP REQ :twitch.tv/tags twitch.tv/commands"
        assert client_lines[3] == "JOIN #fazeclanluke"
        assert pong_lines == ["PONG :tmi.twitch.tv"]
        assert len(connections) == 1
        assert len(comments) == 1
        assert comments[0]["message_id"] == "message-123"

    asyncio.run(scenario())


def test_non_chat_twitch_commands_are_parsed_and_emitted():
    async def scenario() -> None:
        manager = TwitchLiveManager("fazeclanluke")
        user_notices: list[dict] = []
        clear_chats: list[dict] = []
        manager.on_event("usernotice", user_notices.append)
        manager.on_event("clearchat", clear_chats.append)
        await manager._handle_line(
            "@msg-id=sub;user-id=12 :tmi.twitch.tv USERNOTICE #fazeclanluke :Subscribed!"
        )
        await manager._handle_line(
            "@target-user-id=55 :tmi.twitch.tv CLEARCHAT #fazeclanluke :spammer"
        )
        assert user_notices[0]["tags"]["msg-id"] == "sub"
        assert user_notices[0]["message"] == "Subscribed!"
        assert clear_chats[0]["tags"]["target-user-id"] == "55"

    asyncio.run(scenario())
