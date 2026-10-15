from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication, QMouseEvent

from prkit.capslock import CapsLockMonitor
from prkit.overlays import CapsLockOverlay
from prkit.settings import CapsLockSettings


def test_macos_monitor_reads_lock_state_without_appkit_events(qtbot, monkeypatch) -> None:
    from types import SimpleNamespace

    import prkit.capslock as capslock

    state = False
    closed = []

    class LockState:
        def read(self):
            return state

        def close(self):
            closed.append(True)

    monkeypatch.setattr(capslock.sys, "platform", "darwin")
    monkeypatch.setitem(
        capslock.sys.modules,
        "prkit.mac_capslock",
        SimpleNamespace(MacCapsLockState=LockState),
    )
    monitor = CapsLockMonitor()
    monkeypatch.setattr(monitor, "_start_macos_listener", lambda: None)
    states = []
    monitor.changed.connect(states.append)
    try:
        monitor.start()
        assert states == [False]
        state = True
        qtbot.waitUntil(lambda: states == [False, True])
        state = False
        qtbot.waitUntil(lambda: states == [False, True, False])
    finally:
        monitor.stop()
    assert closed == [True]


def test_macos_event_flags_cannot_override_lock_indicator(qtbot, monkeypatch) -> None:
    import threading
    from types import SimpleNamespace

    import prkit.capslock as capslock

    callbacks = {}
    stopped = []

    class Listener:
        def __init__(self, **kwargs):
            callbacks.update(kwargs)

        def start(self):
            return True, None

        def stop(self):
            stopped.append(True)

    monkeypatch.setitem(
        capslock.sys.modules, "prkit.mac_keyboard", SimpleNamespace(MacKeyboardListener=Listener)
    )
    monitor = CapsLockMonitor()
    lock_state = False
    reads = []

    def read_lock():
        reads.append(lock_state)
        return lock_state

    monitor._read = read_lock
    states = []
    monitor.changed.connect(states.append)
    monitor._poll()
    monitor._start_macos_listener()
    # The lock indicator stays ON even when an event reports OFF.
    lock_state = True

    def emit_transitions():
        callbacks["on_capslock"](True)
        callbacks["on_capslock"](False)

    worker = threading.Thread(target=emit_transitions)
    worker.start()
    worker.join()
    qtbot.waitUntil(lambda: len(reads) == 3)
    assert states == [False, True]
    monitor._poll()
    assert states == [False, True]
    lock_state = False
    callbacks["on_capslock"](True)
    assert states == [False, True, False]
    monitor.stop()
    callbacks["on_capslock"](True)
    assert states == [False, True, False]
    assert stopped == [True]


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


def test_input_source_text_survives_appearance_changes(qtbot) -> None:
    settings = CapsLockSettings(enabled=True, mode="input_source")
    overlay = CapsLockOverlay(settings)
    qtbot.addWidget(overlay)
    overlay.show_input_source("中文（注音）")
    settings.opacity = 50
    overlay.apply_settings()
    assert overlay.isVisible()
    assert overlay._text == "中文（注音）"
    overlay.show_input_source("英文")
    assert overlay._text == "英文"
    overlay.hide_now()


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
