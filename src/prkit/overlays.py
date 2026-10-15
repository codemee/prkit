from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QMouseEvent,
    QPainter,
    QPaintEvent,
)
from PySide6.QtWidgets import QWidget

from prkit.platform import (
    configure_overlay_level,
    keep_window_topmost,
    make_window_click_through,
)
from prkit.settings import CapsLockSettings, KeystrokeSettings, SpotlightSettings


class OverlayWindow(QWidget):
    def __init__(self, *, interactive: bool = False) -> None:
        self._interactive = interactive
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if not interactive:
            flags |= Qt.WindowType.WindowTransparentForInput
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not interactive)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def showEvent(self, event: object) -> None:
        super().showEvent(event)  # type: ignore[arg-type]
        QTimer.singleShot(0, self._configure_native_window)

    def _configure_native_window(self) -> None:
        if not self._interactive:
            make_window_click_through(self)
        configure_overlay_level(self)


class SpotlightOverlay(OverlayWindow):
    def __init__(self, settings: SpotlightSettings) -> None:
        super().__init__()
        self._color = QColor(settings.color)
        self._opacity = settings.opacity
        self._diameter = settings.size
        self.setFixedSize(self._diameter, self._diameter)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._follow_cursor)

    @property
    def diameter(self) -> int:
        return self._diameter

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self._follow_cursor()
            self.show()
            self._timer.start()
        else:
            self._timer.stop()
            self.hide()

    def set_appearance(self, color: str, opacity: int, diameter: int) -> None:
        center = (
            QPoint(self.x() + self._diameter // 2, self.y() + self._diameter // 2)
            if self.isVisible()
            else QCursor.pos()
        )
        self._color = QColor(color)
        self._opacity = opacity
        self._diameter = diameter
        self.setFixedSize(diameter, diameter)
        self.move(center - QPoint(diameter // 2, diameter // 2))
        self.update()

    def _follow_cursor(self) -> None:
        position = QCursor.pos()
        self.move(position.x() - self._diameter // 2, position.y() - self._diameter // 2)
        keep_window_topmost(self)

    def sync_position(self) -> None:
        self._follow_cursor()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._color)
        color.setAlphaF(self._opacity / 100)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))


class KeystrokeOverlay(OverlayWindow):
    DISPLAY_MILLISECONDS = 1200
    FADE_MILLISECONDS = 250

    def __init__(self, settings: KeystrokeSettings) -> None:
        super().__init__()
        self._color = QColor(settings.color)
        self._opacity = settings.opacity
        self._text = ""
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.setFont(font)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_fade)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(self.FADE_MILLISECONDS)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self.hide)

    def set_appearance(self, color: str, opacity: int) -> None:
        self._color = QColor(color)
        self._opacity = opacity
        self.update()

    def show_chord(self, text: str) -> None:
        self._fade.stop()
        self._hide_timer.stop()
        self.setWindowOpacity(1.0)
        self._text = text
        metrics = self.fontMetrics()
        width = max(160, metrics.horizontalAdvance(text) + 64)
        height = metrics.height() + 36
        self.setFixedSize(width, height)
        self._place_on_cursor_screen()
        self.show()
        keep_window_topmost(self)
        self.update()

    def keys_released(self) -> None:
        if self.isVisible():
            self._hide_timer.start(self.DISPLAY_MILLISECONDS)

    def hide_now(self) -> None:
        self._hide_timer.stop()
        self._fade.stop()
        self.hide()

    def _place_on_cursor_screen(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        x = available.x() + (available.width() - self.width()) // 2
        y = available.bottom() - self.height() - 47
        self.move(x, y)

    def _start_fade(self) -> None:
        self._fade.start()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QColor(self._color)
        background.setAlphaF(self._opacity / 100)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(QRect(self.rect()).adjusted(1, 1, -1, -1), 18, 18)
        painter.setPen(QColor("white"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._text)


class CapsLockOverlay(OverlayWindow):
    position_changed = Signal(int, int)

    def __init__(self, settings: CapsLockSettings) -> None:
        super().__init__(interactive=True)
        self._settings = settings
        self._state = False
        self._text = "Caps Lock OFF"
        self._drag_offset: QPoint | None = None
        self.setFixedSize(144, 40)
        self.setToolTip("拖曳以移動狀態提示")
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.setFont(font)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_state(self, enabled: bool) -> None:
        if not self._settings.enabled:
            return
        self._state = enabled
        self._text = "Caps Lock ON" if enabled else "Caps Lock OFF"
        self._show_current_state()

    def show_input_source(self, name: str) -> None:
        self._text = name
        self._show_current_state()

    def _show_current_state(self) -> None:
        if not self._settings.enabled:
            return
        self.setFixedWidth(max(144, self.fontMetrics().horizontalAdvance(self._text) + 32))
        self._place_on_screen()
        self.show()
        keep_window_topmost(self)
        self.repaint()
        self._restart_timeout()

    def apply_settings(self) -> None:
        if self._settings.enabled:
            self._show_current_state()
        else:
            self.hide_now()

    def hide_now(self) -> None:
        self._hide_timer.stop()
        self._drag_offset = None
        self.hide()

    def _restart_timeout(self) -> None:
        self._hide_timer.stop()
        if self._settings.duration and self._drag_offset is None:
            self._hide_timer.start(self._settings.duration * 1000)

    def _place_on_screen(self) -> None:
        screens = QGuiApplication.screens()
        if self._settings.x is not None and self._settings.y is not None:
            position = QPoint(self._settings.x, self._settings.y)
            for screen in screens:
                area = screen.availableGeometry()
                if area.contains(position):
                    self.move(
                        min(position.x(), max(area.left(), area.right() - self.width() + 1)),
                        min(position.y(), max(area.top(), area.bottom() - self.height() + 1)),
                    )
                    return
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.center().x() - self.width() // 2, area.bottom() - self.height() - 100)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self._hide_timer.stop()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self._settings.x, self._settings.y = self.x(), self.y()
            self._place_on_screen()
            self._settings.x, self._settings.y = self.x(), self.y()
            self.position_changed.emit(self.x(), self.y())
            self._restart_timeout()
            event.accept()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QColor(self._settings.color)
        background.setAlphaF(self._settings.opacity / 100)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        painter.setPen(QColor("black" if background.lightnessF() > 0.6 else "white"))
        painter.setFont(self.font())
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            self._text,
        )
