import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication

from controller.state import ControllerState
from gamepad_tester import GamepadTesterWidget


PAGE = QColor("#16181D")
PANEL = QColor("#1F2228")
WELL = QColor("#191B20")
BORDER = QColor("#2C3037")
INK = QColor("#E8EAEE")
MUTED = QColor("#A6ADB8")
INDIGO = QColor("#6366F1")
INDIGO_LIGHT = QColor("#818CF8")
GREEN = QColor("#4ADE80")
RED = QColor("#F87171")
BLUE = QColor("#38BDF8")
AMBER = QColor("#FBBF24")


def rounded(painter: QPainter, rect: QRectF, radius: float, fill: QColor, stroke: QColor | None = None, width: float = 1.0) -> None:
    painter.setBrush(fill)
    painter.setPen(QPen(stroke, width) if stroke else Qt.PenStyle.NoPen)
    painter.drawRoundedRect(rect, radius, radius)


def draw_controller(painter: QPainter, x: float, y: float, scale: float) -> None:
    body = QPainterPath()
    body.moveTo(x + 80 * scale, y + 115 * scale)
    body.cubicTo(x + 35 * scale, y + 120 * scale, x + 20 * scale, y + 185 * scale, x + 8 * scale, y + 250 * scale)
    body.cubicTo(x + 5 * scale, y + 270 * scale, x + 26 * scale, y + 274 * scale, x + 45 * scale, y + 250 * scale)
    body.lineTo(x + 94 * scale, y + 205 * scale)
    body.lineTo(x + 266 * scale, y + 205 * scale)
    body.lineTo(x + 315 * scale, y + 250 * scale)
    body.cubicTo(x + 334 * scale, y + 274 * scale, x + 355 * scale, y + 270 * scale, x + 352 * scale, y + 250 * scale)
    body.cubicTo(x + 340 * scale, y + 185 * scale, x + 325 * scale, y + 120 * scale, x + 280 * scale, y + 115 * scale)
    body.closeSubpath()
    painter.setBrush(QColor("#262A32"))
    painter.setPen(QPen(QColor("#3A3F49"), 4 * scale))
    painter.drawPath(body)

    # Subtle shell highlight follows the top contour without turning the
    # controller into a flat icon.
    highlight = QPainterPath()
    highlight.moveTo(x + 76 * scale, y + 126 * scale)
    highlight.cubicTo(x + 128 * scale, y + 112 * scale, x + 226 * scale, y + 112 * scale, x + 284 * scale, y + 126 * scale)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#4A505C"), 2 * scale))
    painter.drawPath(highlight)

    # Shoulder/trigger silhouette.
    rounded(painter, QRectF(x + 68 * scale, y + 90 * scale, 92 * scale, 25 * scale), 10 * scale, WELL, BORDER, 2 * scale)
    rounded(painter, QRectF(x + 200 * scale, y + 90 * scale, 92 * scale, 25 * scale), 10 * scale, WELL, BORDER, 2 * scale)
    rounded(painter, QRectF(x + 83 * scale, y + 68 * scale, 70 * scale, 18 * scale), 8 * scale, INDIGO_LIGHT, BORDER, 2 * scale)
    rounded(painter, QRectF(x + 207 * scale, y + 68 * scale, 70 * scale, 18 * scale), 8 * scale, INDIGO_LIGHT, BORDER, 2 * scale)

    # Sticks and d-pad.
    for cx, cy in ((105, 162), (250, 175)):
        painter.setBrush(QColor("#14161A"))
        painter.setPen(QPen(BORDER, 3 * scale))
        painter.drawEllipse(QPointF(x + cx * scale, y + cy * scale), 28 * scale, 28 * scale)
        painter.setBrush(INDIGO_LIGHT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(x + cx * scale, y + cy * scale - 10 * scale), 8 * scale, 8 * scale)
    painter.setBrush(WELL)
    painter.setPen(QPen(BORDER, 2 * scale))
    painter.drawRoundedRect(QRectF(x + 64 * scale, y + 175 * scale, 54 * scale, 18 * scale), 6 * scale, 6 * scale)
    painter.drawRoundedRect(QRectF(x + 82 * scale, y + 157 * scale, 18 * scale, 54 * scale), 6 * scale, 6 * scale)

    # Guide button and face buttons.
    painter.setBrush(INDIGO)
    painter.setPen(QPen(INDIGO_LIGHT, 2 * scale))
    painter.drawEllipse(QPointF(x + 177 * scale, y + 148 * scale), 22 * scale, 22 * scale)
    painter.setFont(QFont("Segoe UI", int(11 * scale), QFont.Weight.Bold))
    painter.setPen(INK)
    painter.drawText(QRectF(x + 155 * scale, y + 142 * scale, 44 * scale, 16 * scale), Qt.AlignmentFlag.AlignCenter, "LP")
    for label, cx, cy, color in (("Y", 286, 137, AMBER), ("B", 307, 160, RED), ("A", 286, 183, GREEN), ("X", 265, 160, BLUE)):
        painter.setBrush(WELL)
        painter.setPen(QPen(color, 3 * scale))
        painter.drawEllipse(QPointF(x + cx * scale, y + cy * scale), 15 * scale, 15 * scale)
        painter.setPen(color)
        painter.drawText(QRectF(x + (cx - 12) * scale, y + (cy - 9) * scale, 24 * scale, 18 * scale), Qt.AlignmentFlag.AlignCenter, label)


def render_tester() -> QImage:
    """Render the real in-app tester so this artwork cannot drift from it."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    tester = GamepadTesterWidget()
    # Render at 4x so the controller remains crisp after it is composed into
    # the 1280x640 social card.
    tester.resize(3600, 1320)
    tester.set_state(
        ControllerState(
            ly=1.0,
            rx=0.35,
            lt=1.0,
            rt=1.0,
            buttons=frozenset({"l3"}),
        )
    )
    image = QImage(3600, 1320, QImage.Format.Format_RGB32)
    image.fill(PAGE)
    painter = QPainter(image)
    tester.render(painter)
    painter.end()
    return image


def draw_preview() -> None:
    app = QApplication.instance() or QApplication([])
    logical_width, logical_height = 1280, 640
    output_scale = 2
    width, height = logical_width * output_scale, logical_height * output_scale
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(PAGE)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.scale(output_scale, output_scale)

    # Soft indigo glow behind the brand card.
    glow = QLinearGradient(0, 0, logical_width, logical_height)
    glow.setColorAt(0.0, QColor(99, 102, 241, 35))
    glow.setColorAt(0.45, QColor(22, 24, 29, 0))
    glow.setColorAt(1.0, QColor(22, 24, 29, 0))
    painter.fillRect(0, 0, logical_width, logical_height, glow)

    rounded(painter, QRectF(42, 42, 1196, 556), 28, PANEL, BORDER, 2)
    painter.setPen(QPen(INDIGO, 6))
    painter.drawLine(82, 112, 360, 112)

    # Use the canonical LivePad mark from assets so the social card and the
    # application/extension never drift into different logo designs.
    mark = QImage(str(Path("assets/livepad_mark.png")))
    painter.drawImage(QRectF(82, 142, 128, 128), mark)

    painter.setPen(INK)
    painter.setFont(QFont("Segoe UI", 56, QFont.Weight.Bold))
    painter.drawText(QRectF(230, 146, 600, 80), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "LivePad")
    painter.setPen(INDIGO_LIGHT)
    painter.setFont(QFont("Segoe UI", 24, QFont.Weight.DemiBold))
    painter.drawText(QRectF(234, 228, 720, 42), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "LIVE CHAT  →  SHARED XBOX CONTROLLER")
    painter.setPen(MUTED)
    painter.setFont(QFont("Segoe UI", 19))
    painter.drawText(QRectF(234, 282, 620, 34), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "TikTok LIVE  •  YouTube LIVE  •  Twitch")
    painter.setPen(INK)
    painter.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
    painter.drawText(QRectF(234, 338, 560, 32), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Fast, safe, unified chat control")
    painter.setPen(MUTED)
    painter.setFont(QFont("Segoe UI", 16))
    painter.drawText(QRectF(234, 378, 560, 30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Created by Cxsmo_AI")

    # Reuse the actual Qt tester render. This keeps the social preview's
    # controller geometry, labels, state readout, and palette 1:1 with the
    # controller shown in the desktop application.
    tester_image = render_tester().copy(200, 0, 3200, 1320)
    tester_image = tester_image.scaled(
        1050,
        432,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawImage(QRectF(700, 270, 525, 216), tester_image)
    painter.setPen(QPen(INDIGO, 2))
    painter.drawLine(82, 526, 1198, 526)
    painter.setPen(MUTED)
    painter.setFont(QFont("Segoe UI", 15))
    painter.drawText(QRectF(82, 542, 1116, 28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "github.com/Cxsmo-ai/LivePad")
    painter.end()

    target = Path("docs/images/livepad-social-preview.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(target), "PNG")
    print(f"Wrote {target} ({width}x{height})")


if __name__ == "__main__":
    draw_preview()
