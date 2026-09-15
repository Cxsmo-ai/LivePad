"""Capture polished LivePad UI screenshots for the repository and release docs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

if os.environ.get("LIVEPAD_CAPTURE_VISIBLE") != "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "images"
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from chat_gamepad_app import ChatGamepadWindow


def capture() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = ChatGamepadWindow(mock_bridge=True, automation_mode=True)
    window.resize(1280, 1050)
    window.show()

    # Give the widget tree its final geometry before grabbing the viewport.
    app.processEvents()
    window.test_input.setText("w sprint ads fire right 35")
    window._apply_test_command()
    window._set_status_label(window.bridge_status, "Ready (mock)")
    window._set_status_label(window.tiktok_status, "Connected")
    window._set_status_label(window.youtube_status, "Connected")
    window._set_status_label(window.twitch_status, "Connected")
    window._set_status_label(window.chat_plays_status, "Active")
    window.log.append(
        '<span style="color:#38BDF8">[YouTube]</span> '
        '<span style="color:#E8EAEE">movement and camera input accepted</span>'
    )
    window.log.append(
        '<span style="color:#818CF8">[TikTok]</span> '
        '<span style="color:#E8EAEE">compound command resolved</span>'
    )
    window.log.append(
        '<span style="color:#A5B4FC">[Twitch]</span> '
        '<span style="color:#E8EAEE">controller lease active</span>'
    )
    app.processEvents()

    full_size = window.size()
    window.grab().save(str(OUTPUT / "livepad-desktop-full.png"), "PNG")

    # A compact crop keeps the README preview readable without hiding the
    # controller tester and test-mode controls.
    crop_height = min(full_size.height(), 820)
    window.grab().copy(0, 0, full_size.width(), crop_height).save(
        str(OUTPUT / "livepad-desktop-preview.png"), "PNG"
    )
    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(capture())
