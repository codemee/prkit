from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

TRAY_ICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><radialGradient id="g"><stop offset="0" stop-color="#fff"/>
<stop offset=".18" stop-color="#ffb3b3"/><stop offset=".48" stop-color="#f44336"/>
<stop offset="1" stop-color="#8b0000" stop-opacity=".25"/></radialGradient></defs>
<circle cx="32" cy="32" r="27" fill="url(#g)"/><circle cx="32" cy="32" r="8" fill="#fff"/>
</svg>"""


def tray_icon() -> QIcon:
    renderer = QSvgRenderer(QByteArray(TRAY_ICON_SVG))
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill("transparent")
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon
