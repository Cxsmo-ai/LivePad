"""HID Maestro Streamer Edition.

Unified TikTok, YouTube, and Twitch chat controls emulating an Xbox 360 controller.
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
from copy import deepcopy
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app_config import AppConfig
from bridge_process import BridgeProcess
from chat.parser import Command, CommandParser
from controller.state import ControllerState
from gamepad_tester import GamepadTesterWidget
from ipc.named_pipe import NamedPipeClient
from runtime import ControllerRuntime
from stream_icons import format_chat_html, register_chat_icons
from tiktok_client import TikTokLiveManager
from twitch_client import TwitchLiveManager
from youtube_client import YouTubeLiveManager

SAENXT_DARK_STYLESHEET = """
QMainWindow, QWidget#centralRoot {
    background-color: #16181D;
    color: #E8EAEE;
}
QScrollArea {
    background-color: #16181D;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #16181D;
}
QGroupBox {
    background-color: #1F2228;
    border: 1px solid #2C3037;
    border-radius: 8px;
    margin-top: 22px;
    padding: 14px 10px 10px 10px;
    font-size: 13px;
    font-weight: bold;
    color: #E8EAEE;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 3px 10px;
    left: 14px;
    color: #818CF8;
    background-color: #1F2228;
    border: 1px solid #2C3037;
    border-radius: 5px;
}
QLabel {
    color: #E8EAEE;
    font-size: 12px;
}
QLineEdit {
    background-color: #14161A;
    border: 1px solid #34383F;
    border-radius: 5px;
    color: #E8EAEE;
    padding: 6px 10px;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
}
QLineEdit:focus {
    border: 1px solid #818CF8;
}
QLineEdit:disabled {
    background-color: #191B20;
    color: #6B7280;
    border-color: #24272D;
}
QComboBox {
    background-color: #14161A;
    border: 1px solid #34383F;
    border-radius: 5px;
    color: #E8EAEE;
    padding: 5px 10px;
    min-height: 22px;
}
QComboBox:focus {
    border: 1px solid #818CF8;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #2C3037;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
    background-color: #191B20;
}
QComboBox QAbstractItemView {
    background-color: #1F2228;
    border: 1px solid #2C3037;
    border-radius: 5px;
    color: #E8EAEE;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
    padding: 4px;
    outline: none;
}
QCheckBox {
    color: #E8EAEE;
    font-size: 12px;
    font-weight: 500;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #34383F;
    border-radius: 4px;
    background-color: #14161A;
}
QCheckBox::indicator:hover {
    border: 1px solid #818CF8;
}
QCheckBox::indicator:checked {
    background-color: #6366F1;
    border: 1px solid #818CF8;
}
QPushButton {
    background-color: #6366F1;
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 600;
    border-radius: 5px;
    padding: 7px 14px;
    border: 1px solid transparent;
}
QPushButton:hover {
    background-color: #4F46E5;
}
QPushButton:pressed {
    background-color: #4338CA;
}
QPushButton:disabled {
    background-color: #191B20;
    color: #6B7280;
    border: 1px solid #2C3037;
}
QPushButton#secondaryBtn {
    background-color: #191B20;
    color: #818CF8;
    border: 1px solid #2C3037;
}
QPushButton#secondaryBtn:hover {
    background-color: #24272D;
    border-color: #34383F;
    color: #A5B4FC;
}
QPushButton#secondaryBtn:pressed {
    background-color: #14161A;
}
QPushButton#dangerBtn {
    background-color: #191B20;
    color: #F87171;
    border: 1px solid #EF4444;
}
QPushButton#dangerBtn:hover {
    background-color: #EF4444;
    color: #FFFFFF;
}
QPushButton#warningBtn {
    background-color: #191B20;
    color: #FBBF24;
    border: 1px solid #F59E0B;
}
QPushButton#warningBtn:hover {
    background-color: #F59E0B;
    color: #14161A;
}
QTextBrowser {
    background-color: #14161A;
    border: 1px solid #2C3037;
    border-radius: 6px;
    color: #E8EAEE;
    padding: 8px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}
QTableWidget {
    background-color: #14161A;
    alternate-background-color: #191B20;
    border: 1px solid #2C3037;
    border-radius: 6px;
    gridline-color: #24272D;
    color: #E8EAEE;
    font-size: 12px;
}
QTableWidget::item {
    padding: 4px 8px;
}
QTableWidget::item:selected {
    background-color: #6366F1;
    color: #FFFFFF;
}
QHeaderView::section {
    background-color: #1F2228;
    color: #A6ADB8;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid #2C3037;
    border-right: 1px solid #24272D;
    padding: 6px 10px;
}
QScrollBar:vertical {
    background: #16181D;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #2C3037;
    min-height: 24px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #34383F;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #16181D;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #2C3037;
    min-width: 24px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #34383F;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


_SINGLE_INSTANCE_NAME = "Local\\HIDMaestroStreamerEdition.SingleInstance"


def _config_root() -> Path:
    """Keep the portable EXE directory clean; runtime data belongs in LocalAppData."""
    if getattr(sys, "frozen", False):
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", Path(sys.executable).resolve().parent)
        )
        return local_app_data / "HIDMaestroStreamerEdition"
    return Path(__file__).resolve().parent


def _acquire_single_instance(name: str = _SINGLE_INSTANCE_NAME) -> int | None:
    """Keep one app/bridge owner per interactive Windows session."""
    if os.name != "nt":
        return 1
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_bool
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        raise ctypes.WinError()
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return None
    return int(handle)


def _release_single_instance(handle: int | None) -> None:
    if os.name == "nt" and handle:
        ctypes.windll.kernel32.CloseHandle(handle)


class TikTokWorker(QThread):
    comment_received = pyqtSignal(dict)
    state_changed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, username: str, auto_reconnect: bool = True):
        super().__init__()
        self.username = username.lstrip("@")
        self.auto_reconnect = auto_reconnect
        self.stop_requested = False
        self.manager: TikTokLiveManager | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.stop_event: asyncio.Event | None = None

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._run())
        finally:
            self.loop.close()
            self.loop = None

    async def _run(self) -> None:
        self.stop_event = asyncio.Event()
        self.manager = TikTokLiveManager(self.username)

        def _on_comment(data: dict) -> None:
            data_with_platform = dict(data)
            data_with_platform.setdefault("platform", "tiktok")
            self.comment_received.emit(data_with_platform)

        self.manager.on_event("comment", _on_comment)
        self.manager.on_event("connect", lambda _: self.state_changed.emit("Connected"))
        retry_seconds = 1
        while not self.stop_requested:
            try:
                self.state_changed.emit("Connecting" if retry_seconds == 1 else "Reconnecting")
                await self.manager.connect()
                retry_seconds = 1
            except Exception as error:
                if not self.stop_requested:
                    self.failed.emit(str(error))
            finally:
                self.state_changed.emit("Disconnected")

            if self.stop_requested or not self.auto_reconnect:
                break
            self.state_changed.emit(f"Retrying in {retry_seconds}s")
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=retry_seconds)
                break
            except asyncio.TimeoutError:
                retry_seconds = min(retry_seconds * 2, 30)
        self.stop_event = None

    def stop(self) -> None:
        self.stop_requested = True
        if self.loop is not None:
            if self.stop_event is not None:
                self.loop.call_soon_threadsafe(self.stop_event.set)
            if self.manager is not None:
                asyncio.run_coroutine_threadsafe(self.manager.disconnect(), self.loop)


class YouTubeWorker(QThread):
    comment_received = pyqtSignal(dict)
    state_changed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, target: str, chat_type: str = "live", auto_reconnect: bool = True):
        super().__init__()
        self.target = target.strip()
        self.chat_type = chat_type
        self.auto_reconnect = auto_reconnect
        self.stop_requested = False
        self.manager: YouTubeLiveManager | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.stop_event: asyncio.Event | None = None

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._run())
        finally:
            self.loop.close()
            self.loop = None

    async def _run(self) -> None:
        self.stop_event = asyncio.Event()
        self.manager = YouTubeLiveManager(self.target, chat_type=self.chat_type)
        self.manager.on_event("comment", self.comment_received.emit)
        self.manager.on_event("connect", lambda _: self.state_changed.emit("Connected"))
        retry_seconds = 2
        while not self.stop_requested:
            try:
                self.state_changed.emit("Connecting" if retry_seconds == 2 else "Reconnecting")
                await self.manager.connect()
                retry_seconds = 2
            except Exception as error:
                if not self.stop_requested:
                    self.failed.emit(str(error))
            finally:
                self.state_changed.emit("Disconnected")

            if self.stop_requested or not self.auto_reconnect:
                break
            self.state_changed.emit(f"Retrying in {retry_seconds}s")
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=retry_seconds)
                break
            except asyncio.TimeoutError:
                retry_seconds = min(retry_seconds * 2, 30)
        self.stop_event = None

    def stop(self) -> None:
        self.stop_requested = True
        if self.loop is not None:
            if self.stop_event is not None:
                self.loop.call_soon_threadsafe(self.stop_event.set)
            if self.manager is not None:
                asyncio.run_coroutine_threadsafe(self.manager.disconnect(), self.loop)


class TwitchWorker(QThread):
    comment_received = pyqtSignal(dict)
    state_changed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, channel: str, auto_reconnect: bool = True):
        super().__init__()
        self.channel = channel.strip()
        self.auto_reconnect = auto_reconnect
        self.stop_requested = False
        self.manager: TwitchLiveManager | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.stop_event: asyncio.Event | None = None

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._run())
        finally:
            self.loop.close()
            self.loop = None

    async def _run(self) -> None:
        self.stop_event = asyncio.Event()
        self.manager = TwitchLiveManager(self.channel)
        self.manager.on_event("comment", self.comment_received.emit)
        self.manager.on_event("connect", lambda _: self.state_changed.emit("Connected"))
        retry_seconds = 1
        while not self.stop_requested:
            try:
                self.state_changed.emit("Connecting" if retry_seconds == 1 else "Reconnecting")
                await self.manager.connect()
                retry_seconds = 1
            except Exception as error:
                if not self.stop_requested:
                    self.failed.emit(str(error))
            finally:
                self.state_changed.emit("Disconnected")

            if self.stop_requested or not self.auto_reconnect:
                break
            self.state_changed.emit(f"Retrying in {retry_seconds}s")
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=retry_seconds)
                break
            except asyncio.TimeoutError:
                retry_seconds = min(retry_seconds * 2, 30)
        self.stop_event = None

    def stop(self) -> None:
        self.stop_requested = True
        if self.loop is not None:
            if self.stop_event is not None:
                self.loop.call_soon_threadsafe(self.stop_event.set)
            if self.manager is not None:
                asyncio.run_coroutine_threadsafe(self.manager.disconnect(), self.loop)


class ChatGamepadWindow(QMainWindow):
    emergency_stop_requested = pyqtSignal()

    @staticmethod
    def _set_status_label(label: QLabel, text: str) -> None:
        label.setText(text)
        lower = text.lower()
        if ("connected" in lower and not "disconnected" in lower) or "ready" in lower or text == "Active":
            label.setStyleSheet("color: #4ADE80; font-weight: bold;")
        elif "connecting" in lower or "reconnecting" in lower or "paused" in lower:
            label.setStyleSheet("color: #FBBF24; font-weight: bold;")
        elif "disconnected" in lower or "unavailable" in lower:
            label.setStyleSheet("color: #A6ADB8;")
        else:
            label.setStyleSheet("color: #E8EAEE;")

    def __init__(self, mock_bridge: bool = False, automation_mode: bool = False):
        super().__init__()
        self.setWindowTitle("HID Maestro Streamer Edition")
        self.resize(920, 840)
        self.bridge = BridgeProcess()
        self.tiktok_worker: TikTokWorker | None = None
        self.youtube_worker: YouTubeWorker | None = None
        self.twitch_worker: TwitchWorker | None = None
        self.connected_platforms: set[str] = set()
        self.chat_paused = False
        self.hotkey_listener = None
        self.config = AppConfig(_config_root() / "chat_gamepad.json")
        self.config.load()
        self.runtime = ControllerRuntime(config=self.config.data)
        self._build_ui()
        if self.config.last_recovery:
            self._log(self.config.last_recovery)

        self._start_bridge(mock_bridge)

        self.state_timer = QTimer(self)
        scheduler_hz = self.config.data["controller"]["scheduler_hz"]
        self.state_timer.setInterval(max(1, round(1000 / scheduler_hz)))
        self.state_timer.timeout.connect(self._tick)
        self.state_timer.start()

        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.setInterval(250)
        self.heartbeat_timer.timeout.connect(self._heartbeat)
        self.heartbeat_timer.start()

        self.emergency_stop_requested.connect(self._emergency_stop)
        self.f12_shortcut = None
        if mock_bridge or automation_mode or not self._start_global_hotkey():
            self.f12_shortcut = QShortcut(QKeySequence("F12"), self)
            self.f12_shortcut.activated.connect(self._emergency_stop)

    def _build_ui(self) -> None:
        self.setStyleSheet(SAENXT_DARK_STYLESHEET)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        central = QWidget()
        central.setObjectName("centralRoot")
        root = QVBoxLayout(central)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        # Status Bar / Dashboard
        status = QGroupBox("System and Stream Status")
        status_grid = QGridLayout(status)
        self.tiktok_status = QLabel("Disconnected")
        self.youtube_status = QLabel("Disconnected")
        self.twitch_status = QLabel("Disconnected")
        self.bridge_status = QLabel("Starting")
        self.chat_plays_status = QLabel("Active")
        self._set_status_label(self.tiktok_status, "Disconnected")
        self._set_status_label(self.youtube_status, "Disconnected")
        self._set_status_label(self.twitch_status, "Disconnected")
        self._set_status_label(self.bridge_status, "Starting")
        self._set_status_label(self.chat_plays_status, "Active")

        status_grid.addWidget(QLabel("<b>TikTok LIVE:</b>"), 0, 0)
        status_grid.addWidget(self.tiktok_status, 0, 1)
        status_grid.addWidget(QLabel("<b>YouTube LIVE:</b>"), 0, 2)
        status_grid.addWidget(self.youtube_status, 0, 3)
        status_grid.addWidget(QLabel("<b>Twitch:</b>"), 0, 4)
        status_grid.addWidget(self.twitch_status, 0, 5)

        status_grid.addWidget(QLabel("<b>HIDMaestro Bridge:</b>"), 1, 0)
        status_grid.addWidget(self.bridge_status, 1, 1)
        status_grid.addWidget(QLabel("<b>Chat Plays:</b>"), 1, 2)
        status_grid.addWidget(self.chat_plays_status, 1, 3)
        root.addWidget(status)

        # Stream Integrations Grid
        streams_group = QGroupBox("Live Stream Sources (TikTok, YouTube, Twitch)")
        streams_layout = QVBoxLayout(streams_group)
        cards_layout = QHBoxLayout()

        # Left Column: TikTok
        tt_box = QGroupBox("TikTok LIVE")
        tt_layout = QVBoxLayout(tt_box)
        self.tiktok_enabled_cb = QCheckBox("Enable TikTok Stream")
        self.tiktok_enabled_cb.setChecked(self.config.data.get("tiktok", {}).get("enabled", True))
        tt_layout.addWidget(self.tiktok_enabled_cb)

        tt_input_layout = QHBoxLayout()
        tt_input_layout.addWidget(QLabel("Username:"))
        self.tiktok_username = QLineEdit()
        self.tiktok_username.setPlaceholderText("@creator_username")
        self.tiktok_username.setText(self.config.data.get("tiktok", {}).get("username", ""))
        tt_input_layout.addWidget(self.tiktok_username)
        tt_layout.addLayout(tt_input_layout)

        self.tiktok_connect_button = QPushButton("Connect TikTok")
        self.tiktok_connect_button.clicked.connect(self._toggle_tiktok)
        tt_layout.addWidget(self.tiktok_connect_button)
        cards_layout.addWidget(tt_box)

        # Right Column: YouTube
        yt_box = QGroupBox("YouTube LIVE (youtube-chat-next engine)")
        yt_layout = QVBoxLayout(yt_box)
        self.youtube_enabled_cb = QCheckBox("Enable YouTube Stream")
        self.youtube_enabled_cb.setChecked(self.config.data.get("youtube", {}).get("enabled", True))
        yt_layout.addWidget(self.youtube_enabled_cb)

        yt_input_layout = QHBoxLayout()
        yt_input_layout.addWidget(QLabel("Handle / URL:"))
        self.youtube_target = QLineEdit()
        self.youtube_target.setPlaceholderText("@channel or watch?v=...")
        self.youtube_target.setText(self.config.data.get("youtube", {}).get("target", ""))
        yt_input_layout.addWidget(self.youtube_target)
        yt_layout.addLayout(yt_input_layout)

        yt_type_layout = QHBoxLayout()
        yt_type_layout.addWidget(QLabel("Chat View:"))
        self.youtube_chat_type = QComboBox()
        self.youtube_chat_type.addItem("Live Chat (all messages)", "live")
        self.youtube_chat_type.addItem("Top Chat (filtered)", "top")
        current_type = self.config.data.get("youtube", {}).get("chat_type", "live")
        idx = 1 if current_type == "top" else 0
        self.youtube_chat_type.setCurrentIndex(idx)
        yt_type_layout.addWidget(self.youtube_chat_type)
        yt_layout.addLayout(yt_type_layout)

        self.youtube_connect_button = QPushButton("Connect YouTube")
        self.youtube_connect_button.clicked.connect(self._toggle_youtube)
        yt_layout.addWidget(self.youtube_connect_button)
        cards_layout.addWidget(yt_box)

        # Third Column: Twitch
        twitch_box = QGroupBox("Twitch Chat (IRC over secure WebSocket)")
        twitch_layout = QVBoxLayout(twitch_box)
        self.twitch_enabled_cb = QCheckBox("Enable Twitch Stream")
        self.twitch_enabled_cb.setChecked(
            self.config.data.get("twitch", {}).get("enabled", False)
        )
        twitch_layout.addWidget(self.twitch_enabled_cb)

        twitch_input_layout = QHBoxLayout()
        twitch_input_layout.addWidget(QLabel("Channel:"))
        self.twitch_channel = QLineEdit()
        self.twitch_channel.setPlaceholderText("FazeClanLuke")
        self.twitch_channel.setText(
            self.config.data.get("twitch", {}).get("channel", "")
        )
        twitch_input_layout.addWidget(self.twitch_channel)
        twitch_layout.addLayout(twitch_input_layout)

        twitch_note = QLabel("Public read-only chat • no password")
        twitch_note.setToolTip(
            "Uses Twitch's anonymous IRC reader. Twitch officially guarantees only OAuth chat:read clients."
        )
        twitch_layout.addWidget(twitch_note)

        self.twitch_connect_button = QPushButton("Connect Twitch")
        self.twitch_connect_button.clicked.connect(self._toggle_twitch)
        twitch_layout.addWidget(self.twitch_connect_button)
        cards_layout.addWidget(twitch_box)

        streams_layout.addLayout(cards_layout)

        # Bulk Actions
        bulk_layout = QHBoxLayout()
        connect_all_btn = QPushButton("CONNECT ALL ENABLED")
        connect_all_btn.clicked.connect(self._connect_all_enabled)
        disconnect_all_btn = QPushButton("DISCONNECT ALL")
        disconnect_all_btn.setObjectName("secondaryBtn")
        disconnect_all_btn.clicked.connect(self._disconnect_all)
        bulk_layout.addWidget(connect_all_btn)
        bulk_layout.addWidget(disconnect_all_btn)
        streams_layout.addLayout(bulk_layout)

        root.addWidget(streams_group)

        # Resolved Controller State
        controller = QGroupBox("Resolved Xbox 360 Controller — Live Gamepad Tester")
        grid = QVBoxLayout(controller)
        self.gamepad_tester = GamepadTesterWidget()
        grid.addWidget(self.gamepad_tester)
        root.addWidget(controller)

        # Test Mode
        test_group = QGroupBox("Controller Test Mode")
        test_layout = QHBoxLayout(test_group)
        self.test_input = QLineEdit()
        self.test_input.setText("w sprint ads fire right 35")
        self.test_input.setPlaceholderText("w sprint ads fire right 35")
        self.test_input.returnPressed.connect(self._apply_test_command)
        self.test_button = QPushButton("Apply")
        self.test_button.clicked.connect(self._apply_test_command)
        self.hold_button = QPushButton("Hold 10s")
        self.hold_button.setObjectName("secondaryBtn")
        self.hold_button.setToolTip("Hold Button A and movement for 10 seconds to activate browsers and joy.cpl")
        self.hold_button.clicked.connect(self._apply_hold_test)
        self.joy_button = QPushButton("Open joy.cpl")
        self.joy_button.setObjectName("secondaryBtn")
        self.joy_button.setToolTip("Open Windows Game Controllers control panel")
        self.joy_button.clicked.connect(self._open_joy_cpl)
        test_layout.addWidget(self.test_input)
        test_layout.addWidget(self.test_button)
        test_layout.addWidget(self.hold_button)
        test_layout.addWidget(self.joy_button)
        root.addWidget(test_group)

        # Safety Controls
        safety_layout = QHBoxLayout()
        self.pause_button = QPushButton("PAUSE CHAT")
        self.pause_button.setObjectName("warningBtn")
        self.pause_button.clicked.connect(self._toggle_pause)
        safety_layout.addWidget(self.pause_button)
        clear_button = QPushButton("CLEAR CONTROLLER")
        clear_button.setObjectName("dangerBtn")
        clear_button.clicked.connect(self._clear)
        safety_layout.addWidget(clear_button)
        root.addLayout(safety_layout)

        # Unified Multi-Stream Chat Log
        chat_group = QGroupBox("Unified Live Chat (TikTok, YouTube, Twitch)")
        chat_layout = QVBoxLayout(chat_group)
        self.log = QTextBrowser()
        self.log.setReadOnly(True)
        self.log.setOpenExternalLinks(False)
        self.log.document().setMaximumBlockCount(1000)
        register_chat_icons(self.log.document())
        chat_layout.addWidget(self.log)
        root.addWidget(chat_group)

        # Commands Configuration Table
        commands_group = QGroupBox("Commands — Edit Strength, Duration, or Enabled State")
        commands_layout = QVBoxLayout(commands_group)

        # Seconds / Milliseconds duration toggle
        seconds_toggle_layout = QHBoxLayout()
        self.allow_seconds_cb = QCheckBox("Enable seconds duration (e.g. 1.2s, 0.5s) — uncheck for ms only")
        self.allow_seconds_cb.setChecked(
            bool(self.config.data.get("controller", {}).get("allow_seconds", True))
        )
        self.allow_seconds_cb.toggled.connect(self._toggle_allow_seconds)
        seconds_toggle_layout.addWidget(self.allow_seconds_cb)
        seconds_toggle_layout.addStretch()
        commands_layout.addLayout(seconds_toggle_layout)

        self.command_table = QTableWidget()
        self.command_table.setColumnCount(5)
        self.command_table.setHorizontalHeaderLabels(
            ["Command", "Action", "Strength (1-100)", "Duration ms", "Enabled"]
        )
        self.command_table.verticalHeader().setVisible(False)
        self.command_table.setMinimumHeight(280)
        self._populate_command_table()
        self.command_table.horizontalHeader().setStretchLastSection(True)
        commands_layout.addWidget(self.command_table)
        apply_commands = QPushButton("APPLY COMMAND SETTINGS")
        apply_commands.clicked.connect(self._apply_command_settings)
        commands_layout.addWidget(apply_commands)
        root.addWidget(commands_group)

    @staticmethod
    def _readonly_item(value: str) -> QTableWidgetItem:
        item = QTableWidgetItem(value)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _populate_command_table(self) -> None:
        commands = self.config.data["commands"]
        self.command_table.setRowCount(len(commands))
        for row, (name, spec) in enumerate(commands.items()):
            self.command_table.setItem(row, 0, self._readonly_item(name))
            self.command_table.setItem(row, 1, self._readonly_item(str(spec["action"])))
            self.command_table.setItem(row, 2, QTableWidgetItem(f"{float(spec['strength']) * 100:g}"))
            self.command_table.setItem(row, 3, QTableWidgetItem(str(spec["duration_ms"])))
            enabled = QTableWidgetItem()
            enabled.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            enabled.setCheckState(
                Qt.CheckState.Checked if spec.get("enabled", True) else Qt.CheckState.Unchecked
            )
            self.command_table.setItem(row, 4, enabled)
        self.command_table.resizeColumnsToContents()
        self.command_table.setColumnWidth(0, 120)
        self.command_table.setColumnWidth(1, 160)
        self.command_table.setColumnWidth(2, 140)
        self.command_table.setColumnWidth(3, 120)
        self.command_table.setColumnWidth(4, 90)

    def _toggle_allow_seconds(self, enabled: bool) -> None:
        self.config.data.setdefault("controller", {})["allow_seconds"] = enabled
        self.config.save()
        self.runtime.processor.parser.allow_seconds = enabled
        mode_text = "seconds & ms" if enabled else "ms only"
        self._log(f"Duration format: {mode_text}")

    def _apply_command_settings(self) -> None:
        updated = deepcopy(self.config.data)
        try:
            for row in range(self.command_table.rowCount()):
                name = self.command_table.item(row, 0).text()
                strength_str = self.command_table.item(row, 2).text().strip().rstrip("%")
                updated["commands"][name]["strength"] = float(strength_str) / 100.0
                updated["commands"][name]["duration_ms"] = int(
                    self.command_table.item(row, 3).text()
                )
                updated["commands"][name]["enabled"] = (
                    self.command_table.item(row, 4).checkState() == Qt.CheckState.Checked
                )
            self.config.validate(updated)
        except (TypeError, ValueError, AttributeError) as error:
            self._log(f"Command settings rejected: {error}")
            return
        self.config.data = updated
        self.config.save()
        self.runtime.clear()
        allow_seconds = bool(self.config.data.get("controller", {}).get("allow_seconds", True))
        self.runtime.processor.parser = CommandParser(
            updated["commands"], allow_seconds=allow_seconds
        )
        self._log("Command settings applied; controller cleared")

    def _start_bridge(self, mock: bool) -> None:
        try:
            self.bridge.launch(mock=mock)
            self.runtime = ControllerRuntime(NamedPipeClient(), self.config.data)
            self.runtime.start()
            self._set_status_label(self.bridge_status, "Ready (mock)" if mock else "Ready — Xbox 360")
            self._log("Bridge ready")
        except Exception as error:
            details = self.bridge.failure_details()
            self.bridge.stop()
            self.runtime = ControllerRuntime(config=self.config.data)
            self.runtime.start()
            self._set_status_label(self.bridge_status, "Unavailable — local test only")
            self._log(f"Bridge unavailable: {error}; {details}")

    def _connect_all_enabled(self) -> None:
        if self.tiktok_enabled_cb.isChecked() and (self.tiktok_worker is None or not self.tiktok_worker.isRunning()):
            self._start_tiktok()
        if self.youtube_enabled_cb.isChecked() and (self.youtube_worker is None or not self.youtube_worker.isRunning()):
            self._start_youtube()
        if self.twitch_enabled_cb.isChecked() and (self.twitch_worker is None or not self.twitch_worker.isRunning()):
            self._start_twitch()

    def _disconnect_all(self) -> None:
        self._stop_tiktok()
        self._stop_youtube()
        self._stop_twitch()
        self._clear()

    def _clear_if_no_other_streams(self, disconnected_platform: str) -> None:
        self.connected_platforms.discard(disconnected_platform)
        if not self.connected_platforms:
            self.runtime.clear()
            self._render_state(ControllerState())

    # --- TikTok Handling ---
    def _toggle_tiktok(self) -> None:
        if self.tiktok_worker is not None and self.tiktok_worker.isRunning():
            self._stop_tiktok()
        else:
            self._start_tiktok()

    def _start_tiktok(self) -> None:
        username = self.tiktok_username.text().strip()
        if not username:
            self._log("Enter a TikTok username first")
            return
        self.tiktok_worker = TikTokWorker(
            username,
            auto_reconnect=bool(self.config.data.get("tiktok", {}).get("auto_reconnect", True)),
        )
        self.tiktok_worker.comment_received.connect(lambda data: self._handle_comment(data, "tiktok"))
        self.tiktok_worker.state_changed.connect(self._on_tiktok_state)
        self.tiktok_worker.failed.connect(lambda message: self._log(f"TikTok error: {message}"))
        self.tiktok_worker.finished.connect(self._tiktok_worker_finished)
        self.tiktok_worker.start()
        self.tiktok_connect_button.setText("Disconnect TikTok")

    def _stop_tiktok(self) -> None:
        if self.tiktok_worker is not None and self.tiktok_worker.isRunning():
            self.tiktok_worker.stop()
            self.tiktok_connect_button.setEnabled(False)

    def _tiktok_worker_finished(self) -> None:
        self.tiktok_connect_button.setText("Connect TikTok")
        self.tiktok_connect_button.setEnabled(True)
        self.tiktok_worker = None

    def _on_tiktok_state(self, state: str) -> None:
        self._set_status_label(self.tiktok_status, state)
        if state == "Connected":
            self.connected_platforms.add("tiktok")
        elif state == "Disconnected":
            self._clear_if_no_other_streams("tiktok")

    # --- YouTube Handling ---
    def _toggle_youtube(self) -> None:
        if self.youtube_worker is not None and self.youtube_worker.isRunning():
            self._stop_youtube()
        else:
            self._start_youtube()

    def _start_youtube(self) -> None:
        target = self.youtube_target.text().strip()
        if not target:
            self._log("Enter a YouTube handle, live URL, or channel ID first")
            return
        chat_type = self.youtube_chat_type.currentData() or "live"
        self.youtube_worker = YouTubeWorker(
            target,
            chat_type=chat_type,
            auto_reconnect=bool(self.config.data.get("youtube", {}).get("auto_reconnect", True)),
        )
        self.youtube_worker.comment_received.connect(lambda data: self._handle_comment(data, "youtube"))
        self.youtube_worker.state_changed.connect(self._on_youtube_state)
        self.youtube_worker.failed.connect(lambda message: self._log(f"YouTube error: {message}"))
        self.youtube_worker.finished.connect(self._youtube_worker_finished)
        self.youtube_worker.start()
        self.youtube_connect_button.setText("Disconnect YouTube")

    def _stop_youtube(self) -> None:
        if self.youtube_worker is not None and self.youtube_worker.isRunning():
            self.youtube_worker.stop()
            self.youtube_connect_button.setEnabled(False)

    def _youtube_worker_finished(self) -> None:
        self.youtube_connect_button.setText("Connect YouTube")
        self.youtube_connect_button.setEnabled(True)
        self.youtube_worker = None

    def _on_youtube_state(self, state: str) -> None:
        self._set_status_label(self.youtube_status, state)
        if state == "Connected":
            self.connected_platforms.add("youtube")
        elif state == "Disconnected":
            self._clear_if_no_other_streams("youtube")

    # --- Twitch Handling ---
    def _toggle_twitch(self) -> None:
        if self.twitch_worker is not None and self.twitch_worker.isRunning():
            self._stop_twitch()
        else:
            self._start_twitch()

    def _start_twitch(self) -> None:
        channel = self.twitch_channel.text().strip()
        if not channel:
            self._log("Enter a Twitch channel username first")
            return
        self.twitch_worker = TwitchWorker(
            channel,
            auto_reconnect=bool(
                self.config.data.get("twitch", {}).get("auto_reconnect", True)
            ),
        )
        self.twitch_worker.comment_received.connect(
            lambda data: self._handle_comment(data, "twitch")
        )
        self.twitch_worker.state_changed.connect(self._on_twitch_state)
        self.twitch_worker.failed.connect(
            lambda message: self._log(f"Twitch error: {message}")
        )
        self.twitch_worker.finished.connect(self._twitch_worker_finished)
        self.twitch_worker.start()
        self.twitch_connect_button.setText("Disconnect Twitch")

    def _stop_twitch(self) -> None:
        if self.twitch_worker is not None and self.twitch_worker.isRunning():
            self.twitch_worker.stop()
            self.twitch_connect_button.setEnabled(False)

    def _twitch_worker_finished(self) -> None:
        self.twitch_connect_button.setText("Connect Twitch")
        self.twitch_connect_button.setEnabled(True)
        self.twitch_worker = None

    def _on_twitch_state(self, state: str) -> None:
        self._set_status_label(self.twitch_status, state)
        if state == "Connected":
            self.connected_platforms.add("twitch")
        elif state == "Disconnected":
            self._clear_if_no_other_streams("twitch")

    # --- Unified Comment Processing ---
    def _handle_comment(self, event_data: dict, platform: str | None = None) -> None:
        source = platform or event_data.get("platform", "system")
        user = event_data.get("user", "unknown")
        message = event_data.get("comment", "")
        timestamp_str = datetime.now().strftime("%H:%M:%S")

        if self.chat_paused:
            html = format_chat_html(timestamp_str, source, user, message, "paused — ignored")
            self.log.append(html)
            return

        result = self.runtime.handle_comment(event_data, platform=source)
        self._render_state(self.runtime.engine.resolve())

        result_text = f"{len(result.accepted)} accepted"
        if result.rate_limited:
            result_text += f", {len(result.rate_limited)} rate limited"
        if result.invalid_tokens:
            result_text += f", invalid: {' '.join(result.invalid_tokens)}"

        html = format_chat_html(timestamp_str, source, user, message, result_text)
        self.log.append(html)

    def _apply_test_command(self) -> None:
        message = (
            self.test_input.text().strip()
            or self.test_input.placeholderText().strip()
            or "w sprint ads fire right 35"
        )
        self._handle_comment(
            {"user": "local-test", "user_id": "local-test", "comment": message, "platform": "local"},
            platform="local",
        )

    def _apply_hold_test(self) -> None:
        commands = [
            Command("move_forward", 1.0, 10000),
            Command("button_a", 1.0, 10000),
            Command("button_l3", 1.0, 10000),
            Command("left_trigger", 1.0, 10000),
            Command("right_trigger", 1.0, 10000),
            Command("look_right", 0.35, 10000),
        ]
        now_ns = time.monotonic_ns()
        for cmd in commands:
            self.runtime.engine.schedule(cmd, "local-hold", now_ns)
        self.runtime.flush(now_ns)
        self._render_state(self.runtime.engine.resolve(now_ns))
        self._log("HOLD TEST (10s) active: Button A, LY+1.0, RX+0.35, LT 100%, RT 100%, L3 — switch to joy.cpl")

    def _open_joy_cpl(self) -> None:
        try:
            subprocess.Popen(["joy.cpl"], shell=True)
            self._log("Opened joy.cpl — select Xbox 360 controller -> Properties")
        except Exception as error:
            self._log(f"Failed to open joy.cpl: {error}")

    def _tick(self) -> None:
        try:
            submission = self.runtime.flush()
        except OSError as error:
            self._bridge_failed(error)
            return
        if submission is not None:
            self._render_state(submission.state)

    def _heartbeat(self) -> None:
        try:
            self.runtime.heartbeat()
        except OSError as error:
            self._bridge_failed(error)

    def _bridge_failed(self, error: Exception) -> None:
        self.runtime.pipe = None
        self.runtime.clear()
        self._set_status_label(self.bridge_status, "Disconnected — local test only")
        self._render_state(ControllerState())
        self._log(f"Bridge disconnected: {error}")

    def _clear(self) -> None:
        try:
            self.runtime.clear()
        except OSError as error:
            self._bridge_failed(error)
        self._render_state(ControllerState())
        self._log("CONTROLLER CLEARED")

    def _toggle_pause(self) -> None:
        self._set_paused(not self.chat_paused)

    def _set_paused(self, paused: bool) -> None:
        self.chat_paused = paused
        self.pause_button.setText("RESUME CHAT" if paused else "PAUSE CHAT")
        self._set_status_label(self.chat_plays_status, "Paused" if paused else "Active")
        if paused:
            self._clear()
        self._log("CHAT PAUSED" if paused else "CHAT RESUMED")

    def _emergency_stop(self) -> None:
        self._set_paused(True)
        self._log("EMERGENCY F12 STOP")

    def _start_global_hotkey(self) -> bool:
        try:
            from pynput import keyboard

            def on_press(key) -> None:
                if key == keyboard.Key.f12:
                    self.emergency_stop_requested.emit()

            self.hotkey_listener = keyboard.Listener(on_press=on_press)
            self.hotkey_listener.start()
            self._log("Global F12 emergency stop ready")
            return True
        except Exception as error:
            self._log(f"Global F12 unavailable; in-window F12 still works: {error}")
            return False

    def _render_state(self, state: ControllerState) -> None:
        self.gamepad_tester.set_state(state)

    def _log(self, message: str) -> None:
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        self.log.append(f'<span style="color:#6B7280; font-family:Consolas,monospace;">[{timestamp_str}]</span> <i style="color:#A6ADB8;">{message}</i>')

    def closeEvent(self, event) -> None:
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        if self.tiktok_worker is not None and self.tiktok_worker.isRunning():
            self.tiktok_worker.stop()
            self.tiktok_worker.wait(2000)
        if self.youtube_worker is not None and self.youtube_worker.isRunning():
            self.youtube_worker.stop()
            self.youtube_worker.wait(2000)
        if self.twitch_worker is not None and self.twitch_worker.isRunning():
            self.twitch_worker.stop()
            self.twitch_worker.wait(2000)
        try:
            self.runtime.close()
        except OSError:
            pass
        self.bridge.stop()
        self.config.data.setdefault("tiktok", {})
        self.config.data.setdefault("youtube", {})
        self.config.data.setdefault("twitch", {})
        self.config.data["tiktok"]["enabled"] = self.tiktok_enabled_cb.isChecked()
        self.config.data["tiktok"]["username"] = self.tiktok_username.text().strip()
        self.config.data["youtube"]["enabled"] = self.youtube_enabled_cb.isChecked()
        self.config.data["youtube"]["target"] = self.youtube_target.text().strip()
        self.config.data["youtube"]["chat_type"] = self.youtube_chat_type.currentData() or "live"
        self.config.data["twitch"]["enabled"] = self.twitch_enabled_cb.isChecked()
        self.config.data["twitch"]["channel"] = self.twitch_channel.text().strip()
        self.config.data.setdefault("controller", {})["allow_seconds"] = self.allow_seconds_cb.isChecked()
        self.config.save()
        event.accept()


def _write_hardware_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _run_hardware_smoke(app: QApplication, window: ChatGamepadWindow, report_path: Path) -> None:
    """Exercise the real bridge, CLEAR, watchdog, and XInput unattended."""
    from xinput_probe import connected_states

    report: dict = {
        "test": "real-hidmaestro-xinput",
        "command": "w sprint ads fire right 35",
        "passed": False,
    }

    def finish() -> None:
        _write_hardware_report(report_path, report)
        window.close()
        app.exit(0 if report["passed"] else 1)

    def is_neutral(state: dict | None) -> bool:
        return state is not None and (
            state["buttons"] == 0
            and state["left_trigger"] == 0
            and state["right_trigger"] == 0
            and abs(state["left_x"]) <= 1024
            and abs(state["left_y"]) <= 1024
            and abs(state["right_x"]) <= 1024
            and abs(state["right_y"]) <= 1024
        )

    def matching_compound(states: list[dict]) -> list[dict]:
        return [
            state for state in states
            if state["left_trigger"] >= 200
            and state["right_trigger"] >= 200
            and state["buttons"] & 0x0040
            and state["left_y"] >= 20_000
            and abs(state["right_x"]) >= 5_000
        ]

    if not window.bridge_status.text().startswith("Ready —"):
        report["error"] = window.bridge_status.text()
        QTimer.singleShot(0, finish)
        return

    try:
        report["initial"] = connected_states()
        started_ns = time.monotonic_ns()
        window.test_input.setText(report["command"])
        window._apply_test_command()
    except Exception as error:
        report["error"] = f"setup failed: {error}"
        QTimer.singleShot(0, finish)
        return

    def observe_active() -> None:
        try:
            active_states = connected_states()
            report["active"] = active_states
            report["active_observation_ms"] = round(
                (time.monotonic_ns() - started_ns) / 1_000_000, 3
            )
            matching = matching_compound(active_states)
            if not matching:
                report["error"] = "compound controller state was not visible through XInput"
                window._clear()
                QTimer.singleShot(100, finish)
                return
            report["controller_index"] = matching[0]["index"]
            window._clear()
            QTimer.singleShot(100, observe_neutral)
        except Exception as error:
            report["error"] = f"active-state observation failed: {error}"
            window._clear()
            QTimer.singleShot(100, finish)

    def observe_neutral() -> None:
        try:
            neutral_states = connected_states()
            report["clear_neutral"] = neutral_states
            index = report["controller_index"]
            neutral = next((state for state in neutral_states if state["index"] == index), None)
            if not is_neutral(neutral):
                report["error"] = "controller did not return to neutral after CLEAR"
                finish()
                return

            window.test_input.setText(report["command"])
            window._apply_test_command()
            window.state_timer.stop()
            window.heartbeat_timer.stop()
            QTimer.singleShot(75, observe_watchdog_active)
        except Exception as error:
            report["error"] = f"neutral-state observation failed: {error}"
            finish()

    def observe_watchdog_active() -> None:
        try:
            states = connected_states()
            report["watchdog_active"] = states
            if not matching_compound(states):
                report["error"] = "watchdog test state was not active before the timeout"
                finish()
                return
            QTimer.singleShot(1200, observe_watchdog_neutral)
        except Exception as error:
            report["error"] = f"watchdog active-state observation failed: {error}"
            finish()

    def observe_watchdog_neutral() -> None:
        try:
            states = connected_states()
            report["watchdog_neutral"] = states
            index = report["controller_index"]
            neutral = next((state for state in states if state["index"] == index), None)
            report["passed"] = is_neutral(neutral)
            if not report["passed"]:
                report["error"] = "bridge watchdog did not neutralize the controller"
        except Exception as error:
            report["error"] = f"watchdog neutral-state observation failed: {error}"
        finish()

    QTimer.singleShot(75, observe_active)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="run the GUI with a mock bridge and exit")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="keep the GUI open with a mock bridge for visual testing",
    )
    parser.add_argument(
        "--hardware-smoke",
        action="store_true",
        help="exercise the real HIDMaestro controller through XInput and exit",
    )
    parser.add_argument("--hardware-report", type=Path, help="hardware smoke-test JSON output path")
    args = parser.parse_args(argv)
    if getattr(sys, "frozen", False) and os.name == "nt" and not args.smoke and not args.mock:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            parameters = subprocess.list2cmdline(sys.argv[1:])
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, parameters, None, 1)
            os._exit(0 if result > 32 else 1)
    instance_handle = _acquire_single_instance()
    if instance_handle is None:
        return 0
    try:
        app = QApplication([sys.argv[0]])
        app.setStyle("Fusion")
        window = ChatGamepadWindow(
            mock_bridge=args.smoke or args.mock,
            automation_mode=args.hardware_smoke,
        )
        if args.smoke:
            # Test local command
            window.test_input.setText("w sprint ads fire right 35")
            window._apply_test_command()
            state = window.runtime.engine.resolve()
            compound_success = (
                state.ly == 1.0 and state.rx == 0.35 and state.lt == 1.0
                and state.rt == 1.0 and state.buttons == frozenset({"l3"})
                and window.bridge_status.text() == "Ready (mock)"
            )
            # Test TikTok comment through handler
            window._handle_comment({"user": "TTGamer", "user_id": "101", "comment": "jump reload"}, "tiktok")
            tt_state = window.runtime.engine.resolve()
            tt_success = "a" in tt_state.buttons and "x" in tt_state.buttons
            # Test YouTube comment through handler
            window._handle_comment({"user": "YTGamer", "user_id": "202", "comment": "melee swap"}, "youtube")
            yt_state = window.runtime.engine.resolve()
            yt_success = "r3" in yt_state.buttons and "y" in yt_state.buttons
            # Test Twitch comment through the same unified handler
            window._handle_comment(
                {"user": "TWGamer", "user_id": "303", "comment": "crouch dpadup"},
                "twitch",
            )
            twitch_state = window.runtime.engine.resolve()
            twitch_success = (
                "b" in twitch_state.buttons
                and "dpad_up" in twitch_state.buttons
                and window.twitch_status.text() == "Disconnected"
            )

            window._emergency_stop()
            safety_success = window.chat_paused and window.runtime.engine.resolve() == ControllerState()
            window._toggle_pause()
            window._apply_test_command()
            resumed_success = window.runtime.engine.resolve().ly == 1.0
            success = (
                compound_success
                and tt_success
                and yt_success
                and twitch_success
                and safety_success
                and resumed_success
            )
            QTimer.singleShot(75, window.close)
            QTimer.singleShot(100, app.quit)
            app.exec()
            return 0 if success else 1
        if args.hardware_smoke:
            report_path = args.hardware_report or (
                Path(sys.executable).resolve().parent / "hardware-smoke-report.json"
            )
            _run_hardware_smoke(app, window, report_path)
            return app.exec()
        window.show()
        return app.exec()
    finally:
        _release_single_instance(instance_handle)


if __name__ == "__main__":
    raise SystemExit(main())
