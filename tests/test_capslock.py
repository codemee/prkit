from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication, QMouseEvent

from prkit.capslock import CapsLockMonitor
from prkit.overlays import CapsLockOverlay
from prkit.settings import CapsLockSettings


def test_windows_monitor_reads_toggle_bit(qapp, monkeypatch) -> None:
    import ctypes
    from types import SimpleNamespace

    import prkit.capslock as capslock

    value = 0x8000
    monkeypatch.setattr(capslock.sys, "platform", "win32")
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(
            user32=SimpleNamespace(GetKeyState=lambda key: value if key == 0x14 else 0)
        ),
        raising=False,
    )
    monitor = CapsLockMonitor()
    states = []
    monitor.changed.connect(states.append)
    monitor.start()
    assert states == [False]
    value = 0x8001
    monitor._poll()
    assert states == [False, True]
    assert monitor._timer.isActive()
    monitor.stop()


def test_monitor_reports_initial_state_and_only_changes(qapp) -> None:
    monitor = CapsLockMonitor()
    states = []
    monitor.changed.connect(states.append)
    monitor._read = lambda: True
    monitor._poll()
    monitor._poll()
    monitor._read = lambda: False
    monitor._poll()
    assert states == [True, False]
    monitor.stop()
    monitor._poll()
    assert states == [True, False]


def test_monitor_failure_stops_polling(qapp) -> None:
    monitor = CapsLockMonitor()
    errors = []
    monitor.failed.connect(errors.append)

    def fail() -> bool:
        raise RuntimeError("disconnected")

    monitor._read = fail
    monitor._timer.start()
    monitor._poll()
    assert errors == ["disconnected"]
    assert not monitor._timer.isActive()
    assert monitor._read is None


def test_timeout_and_always_visible_modes(qtbot) -> None:
    settings = CapsLockSettings(enabled=True, duration=1)
    overlay = CapsLockOverlay(settings)
    qtbot.addWidget(overlay)
    overlay.show_state(True)
    assert overlay.isVisible()
    overlay._hide_timer.start(1)
    qtbot.waitUntil(lambda: not overlay.isVisible())
    overlay.show_state(False)
    assert overlay.isVisible()
    assert not overlay._state
    settings.duration = 0
    overlay.apply_settings()
    assert overlay.isVisible()
    assert not overlay._hide_timer.isActive()
    settings.enabled = False
    overlay.apply_settings()
    overlay.show_state(True)
    assert not overlay.isVisible()


def test_drag_pauses_timeout_and_saves_position(qtbot) -> None:
    settings = CapsLockSettings(enabled=True)
    overlay = CapsLockOverlay(settings)
    qtbot.addWidget(overlay)
    overlay.show_state(True)
    origin = overlay.pos()
    local = QPoint(10, 10)
    qtbot.mousePress(overlay, Qt.MouseButton.LeftButton, pos=local)
    assert not overlay._hide_timer.isActive()
    destination = origin + QPoint(25, -25)
    event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        local.toPointF(),
        (destination + local).toPointF(),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    overlay.mouseMoveEvent(event)
    with qtbot.waitSignal(overlay.position_changed) as signal:
        qtbot.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=local)
    assert overlay.pos() == destination
    assert signal.args == [destination.x(), destination.y()]
    assert (settings.x, settings.y) == (destination.x(), destination.y())
    assert overlay._hide_timer.isActive()
    overlay.hide_now()


def test_disconnected_screen_position_returns_to_visible_screen(qtbot) -> None:
    overlay = CapsLockOverlay(CapsLockSettings(enabled=True, x=-99999, y=-99999))
    qtbot.addWidget(overlay)
    overlay.show_state(True)
    assert any(
        screen.availableGeometry().contains(overlay.geometry())
        for screen in QGuiApplication.screens()
    )
    overlay.hide_now()
