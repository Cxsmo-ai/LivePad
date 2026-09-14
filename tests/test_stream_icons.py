import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QImage, QTextDocument
from PyQt6.QtWidgets import QApplication

from stream_icons import format_chat_html, register_chat_icons


def test_twitch_icon_is_registered_and_chat_text_is_html_escaped():
    app = QApplication.instance() or QApplication([])
    document = QTextDocument()
    register_chat_icons(document)
    resource = document.resource(
        QTextDocument.ResourceType.ImageResource, QUrl("icon://twitch")
    )
    assert isinstance(resource, QImage)
    assert not resource.isNull()

    chat_html = format_chat_html(
        "12:00", "twitch", "<b>viewer</b>", "<img src=x>", "1 < 2"
    )
    assert 'src="icon://twitch"' in chat_html
    assert "&lt;b&gt;viewer&lt;/b&gt;" in chat_html
    assert "&lt;img src=x&gt;" in chat_html
    assert "1 &lt; 2" in chat_html
    app.processEvents()
