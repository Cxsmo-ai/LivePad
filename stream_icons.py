"""Vector icons and HTML formatting for unified multi-stream chat."""

from __future__ import annotations

import html

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


def make_twitch_icon(size: int = 32) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#9146FF")))
    painter.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), 6, 6)

    scale = size / 32.0
    bubble = QPainterPath()
    bubble.moveTo(6 * scale, 5 * scale)
    bubble.lineTo(27 * scale, 5 * scale)
    bubble.lineTo(27 * scale, 21 * scale)
    bubble.lineTo(21 * scale, 27 * scale)
    bubble.lineTo(15 * scale, 27 * scale)
    bubble.lineTo(15 * scale, 23 * scale)
    bubble.lineTo(6 * scale, 23 * scale)
    bubble.closeSubpath()
    painter.setBrush(QBrush(QColor("#FFFFFF")))
    painter.drawPath(bubble)
    painter.setBrush(QBrush(QColor("#5C16C5")))
    painter.drawRect(QRectF(10 * scale, 9 * scale, 13 * scale, 10 * scale))
    painter.setPen(QPen(QColor("#FFFFFF"), max(1.5, 2.2 * scale)))
    painter.drawLine(QPointF(14 * scale, 11 * scale), QPointF(14 * scale, 17 * scale))
    painter.drawLine(QPointF(19 * scale, 11 * scale), QPointF(19 * scale, 17 * scale))
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
        QUrl("icon://twitch"),
        make_twitch_icon(32),
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
    elif plat in ("twitch", "tw"):
        icon_tag = '<img src="icon://twitch" width="16" height="16" style="vertical-align:middle; margin-right:4px;">'
    else:
        icon_tag = '<img src="icon://local" width="16" height="16" style="vertical-align:middle; margin-right:4px;">'

    safe_timestamp = html.escape(str(timestamp))
    safe_user = html.escape(str(user))
    safe_message = html.escape(str(message))
    chat_html = f'<span style="color:#718096; font-family:monospace;">[{safe_timestamp}]</span> {icon_tag} <b>{safe_user}</b>: {safe_message}'
    if result_text:
        chat_html += f' <span style="color:#A0AEC0; font-size:11px;">({html.escape(str(result_text))})</span>'
    return chat_html
