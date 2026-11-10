from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QCursor, QPalette
from PySide6.QtWidgets import QCheckBox, QColorDialog, QPushButton

from prkit.language import set_qt_language
from prkit.overlays import KeystrokeOverlay, SpotlightOverlay
from prkit.settings import AppSettings, KeystrokeSettings, SpotlightSettings
from prkit.tray import ColorButton, SettingsPanel, TrayController


def test_color_picker_buttons_keep_system_palette(qapp, qtbot) -> None:
    swatch = ColorButton("#202124")
    qtbot.addWidget(swatch)
    picker = QColorDialog(QColor(swatch.color), swatch)
    picker.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
    qtbot.addWidget(picker)
    picker.show()
    qapp.processEvents()

    reference = QPushButton()
    buttons = picker.findChildren(QPushButton)
    assert buttons
    for button in buttons:
        assert button.palette().color(QPalette.ColorRole.Button) == reference.palette().color(
            QPalette.ColorRole.Button
        )
        assert button.palette().color(QPalette.ColorRole.ButtonText) == reference.palette().color(
            QPalette.ColorRole.ButtonText
        )


def test_color_picker_follows_selected_language(qapp, qtbot) -> None:
    for preference, expected in (("zh", "確定"), ("en", "OK")):
        set_qt_language(qapp, preference)
        picker = QColorDialog()
        picker.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        qtbot.addWidget(picker)
        picker.show()
        qapp.processEvents()
        assert expected in [button.text() for button in picker.findChildren(QPushButton)]
        picker.close()
    set_qt_language(qapp, "en")


def test_spotlight_resizes_around_same_center(qtbot, monkeypatch) -> None:
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(500, 400)))
    overlay = SpotlightOverlay(SpotlightSettings(size=96))
    qtbot.addWidget(overlay)
    overlay.set_enabled(True)
    qtbot.waitUntil(overlay.isVisible)
    original_center = overlay.geometry().center()

    overlay.set_appearance("#123456", 60, 320)

    assert overlay.size().width() == 320
    assert overlay.size().height() == 320
    assert overlay.geometry().center() == original_center
    overlay.set_enabled(False)


def test_keystroke_overlay_shows_and_hides(qtbot) -> None:
    overlay = KeystrokeOverlay(KeystrokeSettings())
    qtbot.addWidget(overlay)

    overlay.show_chord("Ctrl + Shift + P")
    assert overlay.isVisible()
    assert overlay.width() >= 160

    overlay.keys_released()
    overlay._hide_timer.start(1)
    qtbot.waitUntil(lambda: not overlay.isVisible(), timeout=1000)


def test_settings_panel_emits_live_size_change(qtbot) -> None:
    panel = SettingsPanel(AppSettings.defaults())
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel.spotlight_size_changed) as signal:
        panel.spotlight_size.slider.setValue(200)

    assert signal.args == [200]
    assert panel.spotlight_size.value_label.text() == "200 px"


def test_settings_panel_enable_toggle(qtbot) -> None:
    panel = SettingsPanel(AppSettings.defaults())
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel.spotlight_enabled_changed) as signal:
        panel.spotlight_enabled.click()

    assert signal.args == [True]


def test_language_button_cycles_and_retranslates(qapp, qtbot) -> None:
    tray = TrayController(AppSettings.defaults())
    assert tray.language_mode == "system"
    with qtbot.waitSignal(tray.language_changed) as signal:
        tray.language_button.click()
    assert signal.args == ["zh"]

    tray.set_language("zh")
    assert tray.language_button.icon().isNull() is False
    with qtbot.waitSignal(tray.language_changed) as signal:
        tray.language_button.click()
    assert signal.args == ["en"]

    tray.set_language("en")
    assert tray.language_label.text() == "Language: English"
    assert tray.panel.spotlight_enabled.text() == "Enable spotlight cursor"
    assert isinstance(tray.autostart_checkbox, QCheckBox)
    assert tray.autostart_checkbox.text() == "Start at login"
    assert tray.exit_action.text() == "Quit"
    with qtbot.waitSignal(tray.language_changed) as signal:
        tray.language_button.click()
    assert signal.args == ["system"]


def test_macos_language_hover_without_mouse_enter_events(qapp, qtbot, monkeypatch) -> None:
    import prkit.tray as module

    monkeypatch.setattr(module.sys, "platform", "darwin")
    settings = AppSettings.defaults()
    settings.language = "en"
    tray = TrayController(settings)
    # Keep the popup within the test screen while preserving its embedded button.
    tray.menu.actions()[0].setVisible(False)
    position = QPoint(-100, -100)
    monkeypatch.setattr(module.QCursor, "pos", staticmethod(lambda: position))
    tray.menu.popup(QPoint(100, 100))
    try:
        qtbot.waitUntil(lambda: tray.language_button.property("pointerHover") is False)
        before = tray.language_button.grab().toImage()
        position = tray.language_button.mapToGlobal(QPoint(8, 8))
        qtbot.waitUntil(lambda: tray.language_button.property("pointerHover") is True)
        assert tray.language_button.grab().toImage() != before
        position = QPoint(-100, -100)
        qtbot.waitUntil(lambda: tray.language_button.property("pointerHover") is False)
    finally:
        tray.menu.hide()
    assert not tray._hover_timer.isActive()
