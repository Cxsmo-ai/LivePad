"""Live, scalable Xbox 360 controller visualization for the streamer GUI."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from controller.state import ControllerState


class GamepadTesterWidget(QWidget):
    """Render every Xbox 360 control from the authoritative resolved state."""

    _ACTIVE = QColor("#6366F1")
    _ACTIVE_ACCENT = QColor("#818CF8")
    _CANVAS_BG = QColor("#16181D")
    _BODY_SURFACE = QColor("#1F2228")
    _CONTROL_SURFACE = QColor("#191B20")
    _OUTLINE = QColor("#2C3037")
    _OUTLINE_SUBTLE = QColor("#24272D")
    _TEXT = QColor("#E8EAEE")
    _MUTED = QColor("#A6ADB8")
    _FAINT = QColor("#6B7280")

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = ControllerState()
        self.setMinimumHeight(330)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("Live Xbox 360 controller state")
        self._update_accessibility()

    @property
    def state(self) -> ControllerState:
        return self._state

    def set_state(self, state: ControllerState) -> None:
        state = state.clamped()
        if state == self._state:
            return
        self._state = state
        self._update_accessibility()
        self.update()

    def state_summary(self) -> str:
        buttons = ", ".join(sorted(self._state.buttons)) or "none"
        return (
            f"LX {self._state.lx:+.2f}, LY {self._state.ly:+.2f}, "
            f"RX {self._state.rx:+.2f}, RY {self._state.ry:+.2f}, "
            f"LT {self._state.lt:.2f}, RT {self._state.rt:.2f}; "
            f"pressed: {buttons}"
        )

    def _update_accessibility(self) -> None:
        self.setAccessibleDescription(self.state_summary())

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt callback name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self._CANVAS_BG)

        sx = self.width() / 900.0
        sy = self.height() / 330.0
        scale = min(sx, sy)
        offset_x = (self.width() - 900 * scale) / 2
        offset_y = (self.height() - 330 * scale) / 2
        painter.translate(offset_x, offset_y)
        painter.scale(scale, scale)

        self._draw_triggers(painter)
        self._draw_body(painter)
        self._draw_bumpers(painter)
        self._draw_stick(painter, QPointF(280, 150), self._state.lx, self._state.ly, "L", "l3")
        self._draw_stick(painter, QPointF(560, 225), self._state.rx, self._state.ry, "R", "r3")
        self._draw_dpad(painter, QPointF(390, 225))
        self._draw_face_buttons(painter, QPointF(660, 150))
        self._draw_center_buttons(painter)
        self._draw_numeric_readout(painter)
        painter.end()

    def _draw_body(self, painter: QPainter) -> None:
        painter.setPen(QPen(self._OUTLINE, 2.5))
        painter.setBrush(self._BODY_SURFACE)
        body = QPainterPath()
        body.moveTo(260, 70)
        body.cubicTo(190, 70, 145, 100, 125, 155)
        body.lineTo(88, 270)
        body.cubicTo(75, 315, 145, 330, 175, 287)
        body.lineTo(235, 225)
        body.cubicTo(330, 260, 570, 260, 665, 225)
        body.lineTo(725, 287)
        body.cubicTo(755, 330, 825, 315, 812, 270)
        body.lineTo(775, 155)
        body.cubicTo(755, 100, 710, 70, 640, 70)
        body.closeSubpath()
        painter.drawPath(body)

    def _draw_triggers(self, painter: QPainter) -> None:
        self._draw_trigger(painter, QRectF(175, 15, 190, 30), "LT", self._state.lt)
        self._draw_trigger(painter, QRectF(535, 15, 190, 30), "RT", self._state.rt)

    def _draw_trigger(self, painter: QPainter, rect: QRectF, label: str, value: float) -> None:
        painter.setPen(QPen(self._OUTLINE, 2))
        painter.setBrush(self._CONTROL_SURFACE)
        painter.drawRoundedRect(rect, 8, 8)
        fill = QRectF(rect.left() + 3, rect.top() + 3, (rect.width() - 6) * value, rect.height() - 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._ACTIVE_ACCENT if value > 0 else self._ACTIVE)
        painter.drawRoundedRect(fill, 5, 5)
        painter.setPen(self._TEXT)
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{label}  {value * 100:3.0f}%")

    def _draw_bumpers(self, painter: QPainter) -> None:
        self._draw_pill(painter, QRectF(190, 55, 170, 34), "LB", "lb" in self._state.buttons)
        self._draw_pill(painter, QRectF(540, 55, 170, 34), "RB", "rb" in self._state.buttons)

    def _draw_pill(self, painter: QPainter, rect: QRectF, text: str, active: bool) -> None:
        painter.setPen(QPen(self._ACTIVE_ACCENT if active else self._OUTLINE, 2))
        painter.setBrush(self._ACTIVE if active else self._CONTROL_SURFACE)
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(QColor("#14161A") if active else self._TEXT)
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_stick(
        self,
        painter: QPainter,
        center: QPointF,
        x: float,
        y: float,
        label: str,
        button: str,
    ) -> None:
        active = button in self._state.buttons
        radius = 43.0
        painter.setPen(QPen(self._ACTIVE_ACCENT if active else self._OUTLINE, 2))
        painter.setBrush(self._CANVAS_BG)
        painter.drawEllipse(center, radius, radius)
        painter.setPen(QPen(self._OUTLINE_SUBTLE, 1))
        painter.drawLine(QPointF(center.x() - radius + 7, center.y()), QPointF(center.x() + radius - 7, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - radius + 7), QPointF(center.x(), center.y() + radius - 7))

        dot = QPointF(center.x() + x * 30, center.y() - y * 30)
        painter.setPen(QPen(self._ACTIVE_ACCENT, 1.5))
        painter.setBrush(self._ACTIVE)
        painter.drawEllipse(dot, 9, 9)
        painter.setPen(self._TEXT)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(center.x() - 55, center.y() + 48, 110, 18), Qt.AlignmentFlag.AlignCenter, f"{label}3 {'DOWN' if active else 'up'}")
        painter.setPen(self._MUTED)
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(QRectF(center.x() - 70, center.y() + 65, 140, 18), Qt.AlignmentFlag.AlignCenter, f"X {x:+.2f}   Y {y:+.2f}")

    def _draw_face_buttons(self, painter: QPainter, center: QPointF) -> None:
        self._draw_round_button(painter, QPointF(center.x(), center.y() - 43), "Y", "y", QColor("#FBBF24"))
        self._draw_round_button(painter, QPointF(center.x() + 43, center.y()), "B", "b", QColor("#F87171"))
        self._draw_round_button(painter, QPointF(center.x(), center.y() + 43), "A", "a", QColor("#4ADE80"))
        self._draw_round_button(painter, QPointF(center.x() - 43, center.y()), "X", "x", QColor("#38BDF8"))

    def _draw_round_button(
        self, painter: QPainter, center: QPointF, label: str, button: str, color: QColor
    ) -> None:
        active = button in self._state.buttons
        painter.setPen(QPen(color, 2.5))
        painter.setBrush(color if active else self._CONTROL_SURFACE)
        painter.drawEllipse(center, 20, 20)
        painter.setPen(QColor("#14161A") if active else color)
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(QRectF(center.x() - 20, center.y() - 20, 40, 40), Qt.AlignmentFlag.AlignCenter, label)

    def _draw_center_buttons(self, painter: QPainter) -> None:
        self._draw_small_button(painter, QPointF(425, 145), "VIEW", "back")
        self._draw_small_button(painter, QPointF(475, 145), "START", "start")
        active = "guide" in self._state.buttons
        painter.setPen(QPen(self._ACTIVE_ACCENT if active else self._OUTLINE, 2))
        painter.setBrush(self._ACTIVE if active else self._CONTROL_SURFACE)
        painter.drawEllipse(QPointF(450, 185), 25, 25)
        painter.setPen(self._TEXT if active else self._MUTED)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(425, 160, 50, 50), Qt.AlignmentFlag.AlignCenter, "GUIDE")

    def _draw_small_button(self, painter: QPainter, center: QPointF, label: str, button: str) -> None:
        active = button in self._state.buttons
        painter.setPen(QPen(self._ACTIVE_ACCENT if active else self._OUTLINE, 1.5))
        painter.setBrush(self._ACTIVE if active else self._CONTROL_SURFACE)
        painter.drawEllipse(center, 13, 13)
        painter.setPen(self._TEXT if active else self._MUTED)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(center.x() - 30, center.y() - 34, 60, 14), Qt.AlignmentFlag.AlignCenter, label)

    def _draw_dpad(self, painter: QPainter, center: QPointF) -> None:
        directions = (
            ("dpad_up", QRectF(center.x() - 13, center.y() - 42, 26, 30), "▲"),
            ("dpad_down", QRectF(center.x() - 13, center.y() + 12, 26, 30), "▼"),
            ("dpad_left", QRectF(center.x() - 42, center.y() - 13, 30, 26), "◀"),
            ("dpad_right", QRectF(center.x() + 12, center.y() - 13, 30, 26), "▶"),
        )
        painter.setFont(QFont("Segoe UI Symbol", 10, QFont.Weight.Bold))
        for button, rect, symbol in directions:
            active = button in self._state.buttons
            painter.setPen(QPen(self._ACTIVE_ACCENT if active else self._OUTLINE, 1.5))
            painter.setBrush(self._ACTIVE if active else self._CONTROL_SURFACE)
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor("#14161A") if active else self._MUTED)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, symbol)
        painter.setPen(self._MUTED)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(center.x() - 45, center.y() + 48, 90, 16), Qt.AlignmentFlag.AlignCenter, "D-PAD")

    def _draw_numeric_readout(self, painter: QPainter) -> None:
        painter.setPen(self._TEXT)
        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        text = (
            f"LX {self._state.lx:+.3f}   LY {self._state.ly:+.3f}   "
            f"RX {self._state.rx:+.3f}   RY {self._state.ry:+.3f}   "
            f"LT {self._state.lt:.3f}   RT {self._state.rt:.3f}"
        )
        painter.drawText(QRectF(105, 302, 690, 22), Qt.AlignmentFlag.AlignCenter, text)
