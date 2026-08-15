from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor

from prkit.overlays import KeystrokeOverlay, SpotlightOverlay
from prkit.settings import AppSettings, KeystrokeSettings, SpotlightSettings
from prkit.tray import SettingsPanel


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
