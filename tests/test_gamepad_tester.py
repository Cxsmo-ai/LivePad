import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from controller.state import ControllerState
from gamepad_tester import GamepadTesterWidget


def test_gamepad_tester_renders_every_state_group():
    app = QApplication.instance() or QApplication([])
    widget = GamepadTesterWidget()
    widget.resize(900, 330)
    state = ControllerState(
        lx=-0.5,
        ly=0.75,
        rx=0.25,
        ry=-1.0,
        lt=0.4,
        rt=1.0,
        buttons=frozenset({
            "a", "b", "x", "y", "lb", "rb", "l3", "r3",
            "back", "start", "guide", "dpad_up", "dpad_right",
        }),
    )
    widget.set_state(state)
    image = QImage(widget.size(), QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    widget.render(painter)
    painter.end()

    assert widget.state == state
    assert "LX -0.50" in widget.state_summary()
    assert "dpad_up" in widget.accessibleDescription()
    assert not image.isNull()
    app.processEvents()
