from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from prkit.icon import tray_icon
from prkit.platform import is_wayland
from prkit.settings import (
    MAX_SPOTLIGHT_SIZE,
    MIN_SPOTLIGHT_SIZE,
    AppSettings,
)


class ColorButton(QPushButton):
    color_changed = Signal(str)

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(42, 24)
        self.setToolTip("選擇顏色")
        self.clicked.connect(self._choose_color)
        self.set_color(color)

    @property
    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._color = QColor(color).name().upper()
        self.setStyleSheet(
            f"QPushButton {{ background: {self._color}; border: 1px solid #777; "
            "border-radius: 4px; }"
        )

    def _choose_color(self) -> None:
        chosen = QColorDialog.getColor(QColor(self._color), self, "選擇顏色")
        if chosen.isValid():
            self.set_color(chosen.name())
            self.color_changed.emit(self._color)


class ValueSlider(QWidget):
    value_changed = Signal(int)

    def __init__(
        self,
        minimum: int,
        maximum: int,
        value: int,
        suffix: str,
        step: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._suffix = suffix
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(minimum, maximum)
        self.slider.setSingleStep(step)
        self.slider.setPageStep(step)
        self.slider.setValue(value)
        self.value_label = QLabel(self)
        self.value_label.setMinimumWidth(48)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)
        self.slider.valueChanged.connect(self._on_value_changed)
        self._on_value_changed(value)

    @property
    def value(self) -> int:
        return self.slider.value()

    def _on_value_changed(self, value: int) -> None:
        step = self.slider.singleStep()
        if step > 1 and value % step:
            value = round(value / step) * step
            self.slider.setValue(value)
            return
        self.value_label.setText(f"{value}{self._suffix}")
        self.value_changed.emit(value)


class SettingsPanel(QWidget):
    spotlight_enabled_changed = Signal(bool)
    spotlight_color_changed = Signal(str)
    spotlight_opacity_changed = Signal(int)
    spotlight_size_changed = Signal(int)
    keystroke_enabled_changed = Signal(bool)
    keystroke_color_changed = Signal(str)
    keystroke_opacity_changed = Signal(int)

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(310)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        self.spotlight_enabled = QCheckBox("啟用聚光燈游標")
        self.spotlight_enabled.setChecked(settings.spotlight.enabled)
        self.spotlight_color = ColorButton(settings.spotlight.color)
        self.spotlight_opacity = ValueSlider(10, 100, settings.spotlight.opacity, "%")
        self.spotlight_size = ValueSlider(
            MIN_SPOTLIGHT_SIZE,
            MAX_SPOTLIGHT_SIZE,
            settings.spotlight.size,
            " px",
            8,
        )
        layout.addWidget(self._section_title("聚光燈游標"))
        layout.addWidget(self.spotlight_enabled)
        layout.addLayout(self._row("顏色", self.spotlight_color))
        layout.addLayout(self._row("透明度", self.spotlight_opacity))
        layout.addLayout(self._row("圓圈大小", self.spotlight_size))
        layout.addWidget(self._separator())

        self.keystroke_enabled = QCheckBox("啟用按鍵顯示")
        self.keystroke_enabled.setChecked(settings.keystroke.enabled)
        self.keystroke_color = ColorButton(settings.keystroke.color)
        self.keystroke_opacity = ValueSlider(10, 100, settings.keystroke.opacity, "%")
        layout.addWidget(self._section_title("按鍵顯示"))
        layout.addWidget(self.keystroke_enabled)
        layout.addLayout(self._row("顏色", self.keystroke_color))
        layout.addLayout(self._row("透明度", self.keystroke_opacity))

        if is_wayland():
            warning = QLabel("⚠ Wayland 不保證支援全域按鍵與覆蓋層")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #b26a00; padding-top: 6px")
            layout.addWidget(warning)

        self.spotlight_enabled.toggled.connect(self.spotlight_enabled_changed)
        self.spotlight_color.color_changed.connect(self.spotlight_color_changed)
        self.spotlight_opacity.value_changed.connect(self.spotlight_opacity_changed)
        self.spotlight_size.value_changed.connect(self.spotlight_size_changed)
        self.keystroke_enabled.toggled.connect(self.keystroke_enabled_changed)
        self.keystroke_color.color_changed.connect(self.keystroke_color_changed)
        self.keystroke_opacity.value_changed.connect(self.keystroke_opacity_changed)

    def set_spotlight_enabled(self, enabled: bool) -> None:
        self.spotlight_enabled.setChecked(enabled)

    def set_keystroke_enabled(self, enabled: bool) -> None:
        self.keystroke_enabled.setChecked(enabled)

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        return label

    @staticmethod
    def _separator() -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.HLine)
        frame.setFrameShadow(QFrame.Shadow.Sunken)
        return frame

    @staticmethod
    def _row(label: str, widget: QWidget) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(18, 0, 0, 0)
        title = QLabel(label)
        title.setMinimumWidth(62)
        layout.addWidget(title)
        layout.addWidget(widget, 1)
        return layout


class TrayController(QObject):
    exit_requested = Signal()

    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.panel = SettingsPanel(settings)
        self.menu = QMenu()
        panel_action = QWidgetAction(self.menu)
        panel_action.setDefaultWidget(self.panel)
        self.menu.addAction(panel_action)
        self.menu.addSeparator()
        exit_action = QAction("結束", self.menu)
        exit_action.triggered.connect(self.exit_requested)
        self.menu.addAction(exit_action)
        self.tray = QSystemTrayIcon(tray_icon(), self)
        self.tray.setToolTip("簡報瑞士刀")
        self.tray.setContextMenu(self.menu)

    @staticmethod
    def is_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self.tray.show()

    def hide(self) -> None:
        self.menu.hide()
        self.tray.hide()

    def notify_warning(self, message: str) -> None:
        self.tray.showMessage("簡報瑞士刀", message, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def connect_settings(
        self,
        *,
        spotlight_enabled: Callable[[bool], None],
        spotlight_color: Callable[[str], None],
        spotlight_opacity: Callable[[int], None],
        spotlight_size: Callable[[int], None],
        keystroke_enabled: Callable[[bool], None],
        keystroke_color: Callable[[str], None],
        keystroke_opacity: Callable[[int], None],
    ) -> None:
        self.panel.spotlight_enabled_changed.connect(spotlight_enabled)
        self.panel.spotlight_color_changed.connect(spotlight_color)
        self.panel.spotlight_opacity_changed.connect(spotlight_opacity)
        self.panel.spotlight_size_changed.connect(spotlight_size)
        self.panel.keystroke_enabled_changed.connect(keystroke_enabled)
        self.panel.keystroke_color_changed.connect(keystroke_color)
        self.panel.keystroke_opacity_changed.connect(keystroke_opacity)
