
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QBrush, QPainterPath

def draw_gamepad(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    scale = size / 256.0

    # Deep black rounded tile
    bg_path = QPainterPath()
    bg_path.addRoundedRect(QRectF(12 * scale, 12 * scale, 232 * scale, 232 * scale), 48 * scale, 48 * scale)
    p.fillPath(bg_path, QColor("#050705"))
    # Electric lime border
    p.strokePath(bg_path, QPen(QColor("#B7FF42"), 6 * scale))

    # Inner subtle glow with neon wash
    inner_glow = QPainterPath()
    inner_glow.addRoundedRect(QRectF(16 * scale, 16 * scale, 224 * scale, 224 * scale), 44 * scale, 44 * scale)
    p.strokePath(inner_glow, QPen(QColor(183, 255, 66, 35), 2 * scale))

    # Gamepad body outline
    pad_body = QPainterPath()
    pad_body.moveTo(76 * scale, 86 * scale)
    pad_body.cubicTo(100 * scale, 76 * scale, 156 * scale, 76 * scale, 180 * scale, 86 * scale)
    pad_body.cubicTo(210 * scale, 98 * scale, 220 * scale, 130 * scale, 208 * scale, 178 * scale)
    pad_body.cubicTo(198 * scale, 214 * scale, 164 * scale, 204 * scale, 150 * scale, 168 * scale)
    pad_body.cubicTo(138 * scale, 142 * scale, 118 * scale, 142 * scale, 106 * scale, 168 * scale)
    pad_body.cubicTo(92 * scale, 204 * scale, 58 * scale, 214 * scale, 48 * scale, 178 * scale)
    pad_body.cubicTo(36 * scale, 130 * scale, 46 * scale, 98 * scale, 76 * scale, 86 * scale)
    pad_body.closeSubpath()

    p.fillPath(pad_body, QColor("#0D110D"))
    p.strokePath(pad_body, QPen(QColor("#B7FF42"), 4.5 * scale))

    # Center guide button (DeepAscension tech style)
    p.setPen(QPen(QColor("#B7FF42"), 2 * scale))
    p.setBrush(QColor("#141A14"))
    p.drawEllipse(QRectF(116 * scale, 98 * scale, 24 * scale, 24 * scale))
    # ''X'' logo in guide button with neon violet
    p.setPen(QPen(QColor("#A98AFF"), 2.5 * scale))
    p.drawLine(QPointF(122 * scale, 104 * scale), QPointF(134 * scale, 116 * scale))
    p.drawLine(QPointF(134 * scale, 104 * scale), QPointF(122 * scale, 116 * scale))

    # Left Analog Stick (top-left) - violet & lime
    p.setPen(QPen(QColor("#A98AFF"), 3 * scale))
    p.setBrush(QColor("#070A07"))
    p.drawEllipse(QRectF(74 * scale, 108 * scale, 32 * scale, 32 * scale))
    p.setBrush(QColor("#B7FF42"))
    p.drawEllipse(QRectF(84 * scale, 118 * scale, 12 * scale, 12 * scale))

    # D-pad (bottom-left)
    dpad = QPainterPath()
    cx, cy = 90 * scale, 158 * scale
    dpad.addRoundedRect(QRectF(cx - 16 * scale, cy - 5 * scale, 32 * scale, 10 * scale), 2 * scale, 2 * scale)
    dpad.addRoundedRect(QRectF(cx - 5 * scale, cy - 16 * scale, 10 * scale, 32 * scale), 2 * scale, 2 * scale)
    p.fillPath(dpad, QColor("#1C241C"))
    p.strokePath(dpad, QPen(QColor("#B7FF42"), 1.5 * scale))

    # Right Analog Stick (bottom-right)
    p.setPen(QPen(QColor("#A98AFF"), 3 * scale))
    p.setBrush(QColor("#070A07"))
    p.drawEllipse(QRectF(150 * scale, 142 * scale, 32 * scale, 32 * scale))
    p.setBrush(QColor("#B7FF42"))
    p.drawEllipse(QRectF(160 * scale, 152 * scale, 12 * scale, 12 * scale))

    # ABXY Buttons (top-right diamond)
    btn_r = 5 * scale
    p.setPen(Qt.PenStyle.NoPen)
    # Y (top, violet)
    p.setBrush(QColor("#A98AFF"))
    p.drawEllipse(QPointF(166 * scale, 108 * scale), btn_r, btn_r)
    # A (bottom, neon green)
    p.setBrush(QColor("#B7FF42"))
    p.drawEllipse(QPointF(166 * scale, 128 * scale), btn_r, btn_r)
    # X (left, tech blue-violet)
    p.setBrush(QColor("#D2C5FF"))
    p.drawEllipse(QPointF(156 * scale, 118 * scale), btn_r, btn_r)
    # B (right, coral-red)
    p.setBrush(QColor("#F87171"))
    p.drawEllipse(QPointF(176 * scale, 118 * scale), btn_r, btn_r)

    p.end()
    return img

def main():
    assets_dir = Path("assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    img256 = draw_gamepad(256)
    img256.save(str(assets_dir / "app_icon.png"), "PNG")
    img256.save(str(assets_dir / "app_icon.ico"), "ICO")
    print("Generated DeepAscension LivePad icons in assets/")

if __name__ == "__main__":
    main()

