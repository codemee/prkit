from __future__ import annotations

import sys
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from prkit.icon import language_icon, tray_icon
from prkit.language import effective_language, tr
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
        self._dialog_title = "選擇顏色"
        self.setFixedSize(42, 24)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("選擇顏色")
        self.clicked.connect(self._choose_color)
        self.set_color(color)

    @property
    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._color = QColor(color).name().upper()
        swatch = QColor(self._color)
        hover = swatch.darker(115) if swatch.lightnessF() > 0.5 else swatch.lighter(140)
        # Lifting black also needs a visible hover state (lighter() keeps it black).
        if swatch.lightnessF() < 0.05:
            hover = QColor("#303030")
        self.setStyleSheet(
            f"QPushButton {{ background: {self._color}; border: none; "
            "border-radius: 6px; }"
            f"QPushButton:hover, QPushButton:focus {{ background: {hover.name()}; }}"
        )

    def _choose_color(self) -> None:
        chosen = QColorDialog.getColor(QColor(self._color), self, self._dialog_title)
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
    capslock_enabled_changed = Signal(bool)
    capslock_color_changed = Signal(str)
    capslock_opacity_changed = Signal(int)
    capslock_duration_changed = Signal(int)
    capslock_mode_changed = Signal(str)

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(310)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        self.spotlight_enabled = QCheckBox("啟用聚光燈游標")
        self.spotlight_enabled.setProperty("i18n", "啟用聚光燈游標")
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
        self.keystroke_enabled.setProperty("i18n", "啟用按鍵顯示")
        self.keystroke_enabled.setChecked(settings.keystroke.enabled)
        self.keystroke_color = ColorButton(settings.keystroke.color)
        self.keystroke_opacity = ValueSlider(10, 100, settings.keystroke.opacity, "%")
        layout.addWidget(self._section_title("按鍵顯示"))
        layout.addWidget(self.keystroke_enabled)
        layout.addLayout(self._row("顏色", self.keystroke_color))
        layout.addLayout(self._row("透明度", self.keystroke_opacity))

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Caps Lock／輸入法狀態"))
        self.capslock_enabled = QCheckBox("啟用狀態顯示")
        self.capslock_enabled.setProperty("i18n", "啟用狀態顯示")
        self.capslock_enabled.setChecked(settings.capslock.enabled)
        self.capslock_color = ColorButton(settings.capslock.color)
        self.capslock_opacity = ValueSlider(10, 100, settings.capslock.opacity, "%")
        self.capslock_duration = QSpinBox()
        self.capslock_duration.setRange(0, 60)
        self.capslock_duration.setSuffix(" 秒")
        self.capslock_duration.setSpecialValueText("一直顯示")
        self.capslock_duration.setValue(settings.capslock.duration)
        self.capslock_duration.setToolTip("狀態變化後的顯示時間；0 表示一直顯示")
        layout.addWidget(self.capslock_enabled)
        self.capslock_mode = QComboBox()
        self.capslock_mode.addItem("Caps Lock 指示燈", "capslock")
        if sys.platform == "darwin":
            self.capslock_mode.addItem("目前輸入法（中文／英文）", "input_source")
        index = self.capslock_mode.findData(settings.capslock.mode)
        self.capslock_mode.setCurrentIndex(max(0, index))
        layout.addLayout(self._row("顯示內容", self.capslock_mode))
        layout.addLayout(self._row("背景顏色", self.capslock_color))
        layout.addLayout(self._row("透明度", self.capslock_opacity))
        layout.addLayout(self._row("顯示時間", self.capslock_duration))
        hint = QLabel("顯示時可用滑鼠拖曳，位置會自動保存。")
        hint.setProperty("i18n", hint.text())
        hint.setWordWrap(True)
        layout.addWidget(hint)

        if is_wayland():
            warning = QLabel("⚠ Wayland 不保證支援全域按鍵與覆蓋層")
            warning.setProperty("i18n", warning.text())
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
        self.capslock_enabled.toggled.connect(self.capslock_enabled_changed)
        self.capslock_color.color_changed.connect(self.capslock_color_changed)
        self.capslock_opacity.value_changed.connect(self.capslock_opacity_changed)
        self.capslock_duration.valueChanged.connect(self.capslock_duration_changed)
        self.capslock_mode.currentIndexChanged.connect(
            lambda index: self.capslock_mode_changed.emit(self.capslock_mode.itemData(index))
        )
        self.retranslate(effective_language(settings.language))

    def retranslate(self, language: str) -> None:
        for widget in self.findChildren(QLabel) + self.findChildren(QCheckBox):
            key = widget.property("i18n")
            if key:
                widget.setText(tr(key, language))
        for button in self.findChildren(ColorButton):
            button._dialog_title = tr("選擇顏色", language)
            button.setToolTip(button._dialog_title)
        self.capslock_duration.setSuffix(tr(" 秒", language))
        self.capslock_duration.setSpecialValueText(tr("一直顯示", language))
        self.capslock_duration.setToolTip(tr("狀態變化後的顯示時間；0 表示一直顯示", language))
        self.capslock_mode.setItemText(0, tr("Caps Lock 指示燈", language))
        if self.capslock_mode.count() > 1:
            self.capslock_mode.setItemText(1, tr("目前輸入法（中文／英文）", language))

    def set_spotlight_enabled(self, enabled: bool) -> None:
        self.spotlight_enabled.setChecked(enabled)

    def set_keystroke_enabled(self, enabled: bool) -> None:
        self.keystroke_enabled.setChecked(enabled)

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("i18n", text)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        return label

    @staticmethod
    def _separator() -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.HLine)
        frame.setFixedHeight(1)
        frame.setStyleSheet("border: none; background: palette(midlight);")
        return frame

    @staticmethod
    def _row(label: str, widget: QWidget) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(18, 0, 0, 0)
        title = QLabel(label)
        title.setProperty("i18n", label)
        title.setMinimumWidth(62)
        layout.addWidget(title)
        layout.addWidget(widget, 1)
        return layout


class TrayController(QObject):
    exit_requested = Signal()
    autostart_changed = Signal(bool)
    language_changed = Signal(str)

    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.panel = SettingsPanel(settings)
        self.menu = QMenu()
        panel_action = QWidgetAction(self.menu)
        panel_action.setDefaultWidget(self.panel)
        self.menu.addAction(panel_action)
        self.menu.addSeparator()
        autostart_row = QWidget(self.menu)
        autostart_layout = QHBoxLayout(autostart_row)
        autostart_layout.setContentsMargins(14, 4, 14, 4)
        self.autostart_checkbox = QCheckBox(autostart_row)
        self.autostart_checkbox.toggled.connect(self.autostart_changed)
        autostart_layout.addWidget(self.autostart_checkbox)
        autostart_action = QWidgetAction(self.menu)
        autostart_action.setDefaultWidget(autostart_row)
        self.menu.addAction(autostart_action)
        self.language_mode = settings.language
        language_row = QWidget(self.menu)
        language_layout = QHBoxLayout(language_row)
        language_layout.setContentsMargins(14, 4, 14, 4)
        self.language_label = QLabel(language_row)
        self.language_button = QPushButton(language_row)
        self.language_button.setFixedSize(40, 36)
        self.language_button.setFlat(True)
        self.language_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.language_button.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.language_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 6px; }"
            'QPushButton:hover, QPushButton[pointerHover="true"] '
            "{ background: rgba(128, 128, 128, 144); }"
            "QPushButton:pressed { background: rgba(128, 128, 128, 192); }"
        )
        self.language_button.clicked.connect(self._cycle_language)
        language_layout.addWidget(self.language_label)
        language_layout.addStretch(1)
        language_layout.addWidget(self.language_button)
        language_action = QWidgetAction(self.menu)
        language_action.setDefaultWidget(language_row)
        self.menu.addAction(language_action)
        self.exit_action = QAction(self.menu)
        self.exit_action.triggered.connect(self.exit_requested)
        self.menu.addAction(self.exit_action)
        self.tray = QSystemTrayIcon(tray_icon(), self)
        if sys.platform == "darwin":
            # Native macOS menus do not track hover for embedded QWidgetActions.
            # Open a Qt popup instead so the settings controls receive mouse events.
            self.tray.activated.connect(self._show_menu)
            self._hover_timer = QTimer(self)
            self._hover_timer.setInterval(40)
            self._hover_timer.timeout.connect(self._refresh_language_hover)
            self.menu.aboutToShow.connect(self._hover_timer.start)
            self.menu.aboutToHide.connect(self._clear_language_hover)
        else:
            self.tray.setContextMenu(self.menu)
        self.retranslate(effective_language(settings.language))

    def _show_menu(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.Context,
        }:
            self.menu.popup(QCursor.pos())

    def _refresh_language_hover(self) -> None:
        button = self.language_button
        hovered = button.rect().contains(button.mapFromGlobal(QCursor.pos()))
        if button.property("pointerHover") != hovered:
            button.setProperty("pointerHover", hovered)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def _clear_language_hover(self) -> None:
        self._hover_timer.stop()
        self.language_button.setProperty("pointerHover", False)
        self.language_button.style().unpolish(self.language_button)
        self.language_button.style().polish(self.language_button)
        self.language_button.update()

    def retranslate(self, language: str) -> None:
        self.panel.retranslate(language)
        self.autostart_checkbox.setText(tr("開機自動啟動", language))
        mode_label = {"system": "隨系統", "zh": "中文", "en": "英文"}[self.language_mode]
        separator = ": " if language == "en" else "："
        self.language_label.setText(f"{tr('語言', language)}{separator}{tr(mode_label, language)}")
        self.language_button.setIcon(language_icon(self.language_mode))
        self.language_button.setToolTip(self.language_label.text())
        self.exit_action.setText(tr("結束", language))
        self.tray.setToolTip(tr("簡報瑞士刀", language))

    def set_language(self, preference: str) -> None:
        self.language_mode = preference
        self.retranslate(effective_language(preference))

    def _cycle_language(self) -> None:
        modes = ("system", "zh", "en")
        self.language_changed.emit(modes[(modes.index(self.language_mode) + 1) % len(modes)])

    def set_autostart_checked(self, enabled: bool) -> None:
        self.autostart_checkbox.blockSignals(True)
        self.autostart_checkbox.setChecked(enabled)
        self.autostart_checkbox.blockSignals(False)

    @staticmethod
    def is_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self.tray.show()

    def hide(self) -> None:
        self.menu.hide()
        self.tray.hide()

    def notify_warning(self, message: str) -> None:
        self.tray.showMessage(self.tray.toolTip(), message, self.tray.icon(), 5000)

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
