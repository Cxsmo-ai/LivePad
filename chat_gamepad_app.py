"""TikTok LIVE comments to a HIDMaestro-backed Xbox controller."""

from __future__ import annotations

import argparse
import asyncio
import ctypes
from copy import deepcopy
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bridge_process import BridgeProcess
from app_config import AppConfig
from chat.parser import CommandParser
from controller.state import ControllerState
from ipc.named_pipe import NamedPipeClient
from runtime import ControllerRuntime
from tiktok_client import TikTokLiveManager


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

    def __init__(self, mock_bridge: bool = False):
        super().__init__()
        self.setWindowTitle("TikTok Chat Gamepad")
        self.resize(860, 780)
        self.bridge = BridgeProcess()
        self.worker: TikTokWorker | None = None
        self.chat_paused = False
        self.hotkey_listener = None
        config_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        self.config = AppConfig(config_root / "chat_gamepad.json")
        self.config.load()
        self.runtime = ControllerRuntime(config=self.config.data)
        self._build_ui()
        if self.config.last_recovery:
            self._log(self.config.last_recovery)
        self.username.setText(self.config.data["tiktok"]["username"])
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
        if mock_bridge or not self._start_global_hotkey():
            self.f12_shortcut = QShortcut(QKeySequence("F12"), self)
            self.f12_shortcut.activated.connect(self._emergency_stop)

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        self.setCentralWidget(central)

        status = QGroupBox("Status")
        status_grid = QGridLayout(status)
        self.tiktok_status = QLabel("Disconnected")
        self.bridge_status = QLabel("Starting")
        status_grid.addWidget(QLabel("TikTok"), 0, 0)
        status_grid.addWidget(self.tiktok_status, 0, 1)
        status_grid.addWidget(QLabel("HIDMaestro bridge"), 1, 0)
        status_grid.addWidget(self.bridge_status, 1, 1)
        root.addWidget(status)

        connection = QGroupBox("TikTok LIVE")
        connection_layout = QHBoxLayout(connection)
        self.username = QLineEdit()
        self.username.setPlaceholderText("TikTok username")
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._toggle_connection)
        connection_layout.addWidget(self.username)
        connection_layout.addWidget(self.connect_button)
        root.addWidget(connection)

        controller = QGroupBox("Resolved Xbox controller state")
        grid = QGridLayout(controller)
        self.state_labels: dict[str, QLabel] = {}
        for row, name in enumerate(("lx", "ly", "rx", "ry", "lt", "rt", "buttons")):
            grid.addWidget(QLabel(name.upper()), row, 0)
            value = QLabel("released" if name == "buttons" else "0.00")
            value.setMinimumWidth(220)
            self.state_labels[name] = value
            grid.addWidget(value, row, 1)
        root.addWidget(controller)

        test_group = QGroupBox("Controller test mode")
        test_layout = QHBoxLayout(test_group)
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("w sprint ads fire right 35")
        self.test_input.returnPressed.connect(self._apply_test_command)
        self.test_button = QPushButton("Apply")
        self.test_button.clicked.connect(self._apply_test_command)
        test_layout.addWidget(self.test_input)
        test_layout.addWidget(self.test_button)
        root.addWidget(test_group)

        safety_layout = QHBoxLayout()
        self.pause_button = QPushButton("PAUSE CHAT")
        self.pause_button.clicked.connect(self._toggle_pause)
        safety_layout.addWidget(self.pause_button)
        clear_button = QPushButton("CLEAR CONTROLLER")
        clear_button.clicked.connect(self._clear)
        safety_layout.addWidget(clear_button)
        root.addLayout(safety_layout)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        root.addWidget(self.log)

        commands_group = QGroupBox("Commands — edit strength, duration, or enabled state")
        commands_layout = QVBoxLayout(commands_group)
        self.command_table = QTableWidget()
        self.command_table.setColumnCount(5)
        self.command_table.setHorizontalHeaderLabels(
            ["Command", "Action", "Strength %", "Duration ms", "Enabled"]
        )
        self._populate_command_table()
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

    def _apply_command_settings(self) -> None:
        updated = deepcopy(self.config.data)
        try:
            for row in range(self.command_table.rowCount()):
                name = self.command_table.item(row, 0).text()
                updated["commands"][name]["strength"] = float(
                    self.command_table.item(row, 2).text()
                ) / 100.0
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
        self.runtime.processor.parser = CommandParser(updated["commands"])
        self._log("Command settings applied; controller cleared")

    def _start_bridge(self, mock: bool) -> None:
        try:
            self.bridge.launch(mock=mock)
            self.runtime = ControllerRuntime(NamedPipeClient(), self.config.data)
            self.runtime.start()
            self.bridge_status.setText("Ready (mock)" if mock else "Ready — Xbox 360")
            self._log("Bridge ready")
        except Exception as error:
            details = self.bridge.failure_details()
            self.bridge.stop()
            self.runtime = ControllerRuntime(config=self.config.data)
            self.runtime.start()
            self.bridge_status.setText("Unavailable — local test only")
            self._log(f"Bridge unavailable: {error}; {details}")

    def _toggle_connection(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.connect_button.setEnabled(False)
            return
        username = self.username.text().strip()
        if not username:
            self._log("Enter a TikTok username first")
            return
        self.worker = TikTokWorker(
            username,
            auto_reconnect=bool(self.config.data["tiktok"]["auto_reconnect"]),
        )
        self.worker.comment_received.connect(self._handle_comment)
        self.worker.state_changed.connect(self._on_tiktok_state)
        self.worker.failed.connect(lambda message: self._log(f"TikTok error: {message}"))
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()
        self.connect_button.setText("Disconnect")

    def _worker_finished(self) -> None:
        self.connect_button.setText("Connect")
        self.connect_button.setEnabled(True)
        self.worker = None

    def _on_tiktok_state(self, state: str) -> None:
        self.tiktok_status.setText(state)
        if state == "Disconnected":
            self.runtime.clear()
            self._render_state(ControllerState())

    def _handle_comment(self, event_data: dict) -> None:
        if self.chat_paused:
            self._log(f"Ignored while paused: {event_data.get('user', 'unknown')}: {event_data.get('comment', '')}")
            return
        result = self.runtime.handle_comment(event_data)
        self._render_state(self.runtime.engine.resolve())
        user = event_data.get("user", "unknown")
        message = event_data.get("comment", "")
        result_text = f"{len(result.accepted)} accepted"
        if result.rate_limited:
            result_text += f", {len(result.rate_limited)} rate limited"
        if result.invalid_tokens:
            result_text += f", invalid: {' '.join(result.invalid_tokens)}"
        self._log(f"{user}: {message} — {result_text}")

    def _apply_test_command(self) -> None:
        message = self.test_input.text().strip()
        if message:
            self._handle_comment({"user": "local-test", "user_id": "local-test", "comment": message})

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
        self.bridge_status.setText("Disconnected — local test only")
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
        self.state_labels["lx"].setText(f"{state.lx:+.2f}")
        self.state_labels["ly"].setText(f"{state.ly:+.2f}")
        self.state_labels["rx"].setText(f"{state.rx:+.2f}")
        self.state_labels["ry"].setText(f"{state.ry:+.2f}")
        self.state_labels["lt"].setText(f"{state.lt:.2f}")
        self.state_labels["rt"].setText(f"{state.rt:.2f}")
        self.state_labels["buttons"].setText(", ".join(sorted(state.buttons)) or "released")

    def _log(self, message: str) -> None:
        self.log.appendPlainText(f"[{datetime.now():%H:%M:%S}] {message}")

    def closeEvent(self, event) -> None:
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        try:
            self.runtime.close()
        except OSError:
            pass
        self.bridge.stop()
        self.config.data["tiktok"]["username"] = self.username.text().strip()
        self.config.save()
        event.accept()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="run the GUI with a mock bridge and exit")
    args = parser.parse_args(argv)
    if getattr(sys, "frozen", False) and os.name == "nt" and not args.smoke:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            parameters = subprocess.list2cmdline(sys.argv[1:])
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, parameters, None, 1)
            return 0 if result > 32 else 1
    app = QApplication([sys.argv[0], *(argv or sys.argv[1:])])
    window = ChatGamepadWindow(mock_bridge=args.smoke)
    if args.smoke:
        window.test_input.setText("w sprint ads fire right 35")
        window._apply_test_command()
        state = window.runtime.engine.resolve()
        compound_success = (
            state.ly == 1.0 and state.rx == 0.35 and state.lt == 1.0
            and state.rt == 1.0 and state.buttons == frozenset({"l3"})
            and window.bridge_status.text() == "Ready (mock)"
        )
        window._emergency_stop()
        safety_success = window.chat_paused and window.runtime.engine.resolve() == ControllerState()
        window._toggle_pause()
        window._apply_test_command()
        resumed_success = window.runtime.engine.resolve().ly == 1.0
        success = compound_success and safety_success and resumed_success
        QTimer.singleShot(75, window.close)
        QTimer.singleShot(100, app.quit)
        app.exec()
        return 0 if success else 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
