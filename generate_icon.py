
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QBrush, QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen

SLATE_PAGE = "#16181D"
SLATE_PANEL = "#1F2228"
SLATE_WELL = "#191B20"
SLATE_INK = "#14161A"
INDIGO = "#6366F1"
INDIGO_LIGHT = "#818CF8"
INDIGO_HIGHLIGHT = "#A5B4FC"


def _scaled_rect(x: float, y: float, w: float, h: float, scale: float) -> QRectF:
    return QRectF(x * scale, y * scale, w * scale, h * scale)


def draw_mark(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    scale = size / 256.0

    # A compact slate tile makes the mark survive dark, light, and browser UI
    # surfaces while keeping the website's neutral-first visual language.
    bg_path = QPainterPath()
    bg_path.addRoundedRect(_scaled_rect(10, 10, 236, 236, scale), 48 * scale, 48 * scale)
    tile_gradient = QLinearGradient(0, 10 * scale, 0, 246 * scale)
    tile_gradient.setColorAt(0.0, QColor(SLATE_PANEL))
    tile_gradient.setColorAt(1.0, QColor(SLATE_PAGE))
    p.fillPath(bg_path, QBrush(tile_gradient))
    p.strokePath(bg_path, QPen(QColor(INDIGO), 6 * scale))

    inner_glow = QPainterPath()
    inner_glow.addRoundedRect(_scaled_rect(16, 16, 224, 224, scale), 44 * scale, 44 * scale)
    p.strokePath(inner_glow, QPen(QColor(INDIGO_LIGHT), 2 * scale, Qt.PenStyle.SolidLine))

    # An original LP monogram: architectural, compact, and closer to the
    # website's cut-out geometry than to a literal controller illustration.
    logo = QPainterPath()
    logo.moveTo(78 * scale, 74 * scale)
    logo.lineTo(78 * scale, 183 * scale)
    logo.lineTo(126 * scale, 183 * scale)
    logo.moveTo(145 * scale, 183 * scale)
    logo.lineTo(145 * scale, 74 * scale)
    logo.lineTo(176 * scale, 74 * scale)
    logo.cubicTo(203 * scale, 74 * scale, 208 * scale, 125 * scale, 176 * scale, 125 * scale)
    logo.lineTo(145 * scale, 125 * scale)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(INDIGO_LIGHT), 18 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin))
    p.drawPath(logo)

    # The small four-dot live signal is the only playful element: four states,
    # one stream, kept deliberately secondary to the monogram.
    p.setPen(Qt.PenStyle.NoPen)
    for x, y, color in (
        (183, 157, INDIGO),
        (201, 157, INDIGO_LIGHT),
        (183, 175, INDIGO_HIGHLIGHT),
        (201, 175, INDIGO),
    ):
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(x * scale, y * scale), 5.5 * scale, 5.5 * scale)

    # A single stepped cut-out echoes the parent website's cube silhouette
    # without borrowing its face artwork or wordmark.
    cutout = QPainterPath()
    cutout.moveTo(188 * scale, 64 * scale)
    cutout.lineTo(212 * scale, 64 * scale)
    cutout.lineTo(212 * scale, 88 * scale)
    cutout.lineTo(200 * scale, 88 * scale)
    cutout.lineTo(200 * scale, 76 * scale)
    cutout.lineTo(188 * scale, 76 * scale)
    cutout.closeSubpath()
    p.fillPath(cutout, QColor(SLATE_PAGE))

    p.end()
    return img


def main():
    # QPainter can rasterize paths without a widget, but font metrics are
    # backed by Qt's GUI subsystem.  Start a headless GUI context so the same
    # script works in packaging and on a build machine without a display.
    app = QGuiApplication.instance() or QGuiApplication([])
    assets_dir = Path("assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    img256 = draw_mark(256)
    img256.save(str(assets_dir / "app_icon.png"), "PNG")
    img256.save(str(assets_dir / "app_icon.ico"), "ICO")
    draw_mark(128).save(str(assets_dir / "livepad_mark.png"), "PNG")
    extension_assets = Path("controller-chat-extension") / "assets"
    extension_assets.mkdir(parents=True, exist_ok=True)
    draw_mark(128).save(str(extension_assets / "livepad_mark.png"), "PNG")
    print("Generated LivePad mark and app icons in assets/")

if __name__ == "__main__":
    main()

