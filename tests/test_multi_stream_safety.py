import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

import chat_gamepad_app
from chat.parser import Command
from controller.state import ControllerState


def test_controller_clears_only_after_every_connected_stream_is_gone(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(chat_gamepad_app, "_config_root", lambda: tmp_path)
    app = QApplication.instance() or QApplication([])
    window = chat_gamepad_app.ChatGamepadWindow(mock_bridge=True)
    try:
        window._on_tiktok_state("Connected")
        window._on_twitch_state("Connected")
        window.runtime.engine.schedule(Command("button_a", 1.0, 500), "viewer")
        assert "a" in window.runtime.engine.resolve().buttons

        window._on_tiktok_state("Disconnected")
        assert "a" in window.runtime.engine.resolve().buttons

        window._on_twitch_state("Disconnected")
        assert window.runtime.engine.resolve() == ControllerState()
    finally:
        window.close()
        app.processEvents()
