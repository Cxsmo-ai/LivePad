"""Vector icons and HTML formatting for unified multi-stream chat."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, QUrl
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QTextDocument,
)


def make_youtube_icon(size: int = 32) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#FF0000")))
    painter.drawRoundedRect(QRectF(1, 4, size - 2, size - 8), 6, 6)
    painter.setBrush(QBrush(QColor("#FFFFFF")))
    path = QPainterPath()
    path.moveTo(size * 0.40, size * 0.32)
    path.lineTo(size * 0.68, size * 0.50)
    path.lineTo(size * 0.40, size * 0.68)
    path.closeSubpath()
    painter.drawPath(path)
    painter.end()
    return img


def make_tiktok_icon(size: int = 32) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#010101")))
    painter.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), 6, 6)
    
    # Cyan accent
    painter.setPen(QPen(QColor("#25F4EE"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    path_c = QPainterPath()
    path_c.moveTo(size * 0.51, size * 0.26)
    path_c.lineTo(size * 0.51, size * 0.65)
    path_c.addEllipse(QPointF(size * 0.41, size * 0.65), size * 0.14, size * 0.12)
    path_c.moveTo(size * 0.51, size * 0.34)
    path_c.cubicTo(size * 0.59, size * 0.34, size * 0.69, size * 0.29, size * 0.72, size * 0.22)
    painter.drawPath(path_c)
    
    # Magenta accent
    painter.setPen(QPen(QColor("#FE2C55"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    path_m = QPainterPath()
    path_m.moveTo(size * 0.55, size * 0.24)
    path_m.lineTo(size * 0.55, size * 0.63)
    path_m.addEllipse(QPointF(size * 0.45, size * 0.63), size * 0.14, size * 0.12)
    path_m.moveTo(size * 0.55, size * 0.32)
    path_m.cubicTo(size * 0.63, size * 0.32, size * 0.73, size * 0.27, size * 0.76, size * 0.20)
    painter.drawPath(path_m)
    
    # White foreground note
    painter.setPen(QPen(QColor("#FFFFFF"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    path_w = QPainterPath()
    path_w.moveTo(size * 0.53, size * 0.25)
    path_w.lineTo(size * 0.53, size * 0.64)
    path_w.addEllipse(QPointF(size * 0.43, size * 0.64), size * 0.14, size * 0.12)
    path_w.moveTo(size * 0.53, size * 0.33)
    path_w.cubicTo(size * 0.61, size * 0.33, size * 0.71, size * 0.28, size * 0.74, size * 0.21)
    painter.drawPath(path_w)
    
    painter.end()
    return img


def make_local_icon(size: int = 32) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#4A5568")))
    painter.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), 6, 6)
    painter.setPen(QPen(QColor("#FFFFFF"), 2.0))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "DEV")
    painter.end()
    return img


def register_chat_icons(document: QTextDocument) -> None:
    """Register application icons as QTextDocument resources."""
    document.addResource(
        QTextDocument.ResourceType.ImageResource,
        QUrl("icon://youtube"),
        make_youtube_icon(32),
    )
    document.addResource(
        QTextDocument.ResourceType.ImageResource,
        QUrl("icon://tiktok"),
        make_tiktok_icon(32),
    )
    document.addResource(
        QTextDocument.ResourceType.ImageResource,
        QUrl("icon://local"),
        make_local_icon(32),
    )


def format_chat_html(
    timestamp: str,
    platform: str,
    user: str,
    message: str,
    result_text: str | None = None,
) -> str:
    plat = (platform or "system").lower()
    if plat in ("youtube", "yt"):
        icon_tag = '<img src="icon://youtube" width="16" height="16" style="vertical-align:middle; margin-right:4px;">'
    elif plat in ("tiktok", "tt"):
        icon_tag = '<img src="icon://tiktok" width="16" height="16" style="vertical-align:middle; margin-right:4px;">'
    else:
        icon_tag = '<img src="icon://local" width="16" height="16" style="vertical-align:middle; margin-right:4px;">'

    html = f'<span style="color:#718096; font-family:monospace;">[{timestamp}]</span> {icon_tag} <b>{user}</b>: {message}'
    if result_text:
        html += f' <span style="color:#A0AEC0; font-size:11px;">({result_text})</span>'
    return html

