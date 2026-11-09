from threading import Event

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from prkit.app import AppController
from prkit.capslock import CapsLockMonitor
from prkit.icon import tray_icon
from prkit.input_source import InputSourceMonitor
from prkit.message_dialog import MessageDialog
from prkit.settings import AppSettings
from prkit.windows_cursor import WindowsCursorSpotlight


class MemoryStore:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings.defaults()
        self.save_count = 0

    def load(self) -> AppSettings:
        return self.settings

    def save(self, settings: AppSettings) -> None:
        self.settings = settings
        self.save_count += 1


@pytest.mark.parametrize(
    ("icon", "language", "message", "badge", "button", "maximum_width"),
    [
        (QMessageBox.Icon.Information, "en", "PRKit is already running.", "i", "OK", 420),
        (QMessageBox.Icon.Critical, "zh", "PRKit 已在執行。", "!", "確定", 300),
    ],
)
def test_message_dialog_uses_small_aligned_badge_and_app_icon(
    qapp, qtbot, icon, language, message, badge, button, maximum_width
) -> None:
    qapp.setWindowIcon(tray_icon())
    dialog = MessageDialog(qapp, icon, language, message)
    qtbot.addWidget(dialog)
    dialog.show()
    qapp.processEvents()

    assert dialog.windowIcon().pixmap(32).toImage() == qapp.windowIcon().pixmap(32).toImage()
    assert dialog.badge.text() == badge
    assert dialog.badge.size().width() == 20
    assert dialog.confirm_button.text() == button
    assert dialog.minimumSize() == dialog.maximumSize()
    assert dialog.width() <= maximum_width
    assert dialog.height() <= 150
    badge_center = dialog.badge.geometry().center().y()
    message_center = dialog.message_label.geometry().center().y()
    assert abs(badge_center - message_center) <= 1

    dialog.resize(1160, 1048)
    qapp.processEvents()
    assert dialog.width() <= maximum_width
    assert dialog.height() <= 150


def test_long_message_wraps_within_compact_dialog(qapp, qtbot) -> None:
    dialog = MessageDialog(
        qapp,
        QMessageBox.Icon.Critical,
        "en",
        "Could not check for a running PRKit instance: access to the application data directory "
        "was denied by the operating system.",
    )
    qtbot.addWidget(dialog)
    dialog.show()
    qapp.processEvents()

    assert dialog.width() <= 440
    assert dialog.height() <= 200
    assert dialog.minimumSize() == dialog.maximumSize()


class FakeMonitor(QObject):
    chord_pressed = Signal(str)
    all_released = Signal()
    failed = Signal(str)

    def __init__(self, succeeds: bool = True) -> None:
        super().__init__()
        self.succeeds = succeeds
        self.running = False
        self.stop_count = 0

    def start(self) -> tuple[bool, str | None]:
        self.running = self.succeeds
        return (True, None) if self.succeeds else (False, "permission denied")

    def stop(self) -> None:
        self.running = False
        self.stop_count += 1


class FakeSpotlight:
    def __init__(self) -> None:
        self.enabled = False
        self.diameter = 96
        self.color = "#FFD54F"
        self.opacity = 45

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def set_appearance(self, color: str, opacity: int, diameter: int) -> None:
        self.color = color
        self.opacity = opacity
        self.diameter = diameter

    def sync_position(self) -> None:
        pass


def test_controller_applies_live_spotlight_settings(qapp) -> None:
    store = MemoryStore()
    monitor = FakeMonitor()
    spotlight = FakeSpotlight()
    controller = AppController(qapp, store, monitor, spotlight)  # type: ignore[arg-type]

    controller.set_spotlight_size(208)
    controller.set_spotlight_opacity(61)

    assert controller.spotlight.diameter == 208
    assert store.settings.spotlight.size == 208
    assert store.settings.spotlight.opacity == 61


def test_keyboard_failure_reverts_enabled_state(qapp, monkeypatch) -> None:
    store = MemoryStore()
    monitor = FakeMonitor(succeeds=False)
    controller = AppController(qapp, store, monitor, FakeSpotlight())  # type: ignore[arg-type]
    warnings: list[str] = []
    monkeypatch.setattr(controller.tray, "notify_warning", warnings.append)

    controller.set_keystroke_enabled(True)
    qapp.processEvents()

    assert not store.settings.keystroke.enabled
    assert not controller.tray.panel.keystroke_enabled.isChecked()
    assert warnings and "permission denied" in warnings[0]


def test_autostart_toggle_reverts_when_system_write_fails(qapp, monkeypatch) -> None:
    from prkit import autostart

    controller = AppController(qapp, MemoryStore(), FakeMonitor(), FakeSpotlight())
    warnings: list[str] = []
    monkeypatch.setattr(autostart, "is_enabled", lambda: False)

    def fail(_enabled: bool) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(autostart, "set_enabled", fail)
    monkeypatch.setattr(controller.tray, "notify_warning", warnings.append)
    controller.tray.autostart_checkbox.click()

    assert not controller.tray.autostart_checkbox.isChecked()
    assert warnings and "denied" in warnings[0]


def test_cleanup_stops_effects(qapp) -> None:
    store = MemoryStore()
    monitor = FakeMonitor()
    spotlight = FakeSpotlight()
    controller = AppController(qapp, store, monitor, spotlight)  # type: ignore[arg-type]
    controller.set_spotlight_enabled(True)
    controller.set_keystroke_enabled(True)
    qapp.processEvents()

    controller.cleanup()

    assert not spotlight.enabled
    assert not monitor.running
    assert monitor.stop_count == 1


@pytest.mark.parametrize("cancel", [False, True])
def test_saved_spotlight_waits_for_watchdog_without_blocking_tray(
    qapp, qtbot, monkeypatch, cancel
) -> None:
    import prkit.app as app_module
    import prkit.windows_cursor as cursor_module

    monkeypatch.setattr(app_module.sys, "platform", "win32")
    monkeypatch.setattr(app_module.autostart, "is_enabled", lambda: False)
    started = Event()
    release = Event()
    stopped = Event()

    class SlowWatchdog:
        def __init__(self) -> None:
            started.set()
            assert release.wait(5)

        def stop(self) -> None:
            stopped.set()

    class SafeSpotlight(WindowsCursorSpotlight):
        def __init__(self) -> None:
            self.enabled = False

        def enable_with_watchdog(self, watchdog) -> None:
            self.enabled = True
            self.watchdog = watchdog

        def set_enabled(self, enabled: bool) -> None:
            self.enabled = enabled
            if not enabled and hasattr(self, "watchdog"):
                self.watchdog.stop()

    monkeypatch.setattr(cursor_module, "CursorWatchdog", SlowWatchdog)
    store = MemoryStore()
    store.settings.spotlight.enabled = True
    spotlight = SafeSpotlight()
    controller = AppController(qapp, store, FakeMonitor(), spotlight)
    controller.start()
    try:
        qtbot.waitUntil(started.is_set)
        assert controller.tray.tray.isVisible()
        assert not spotlight.enabled
        if cancel:
            controller.set_spotlight_enabled(False)
        release.set()
        if cancel:
            qtbot.waitUntil(stopped.is_set)
            assert not spotlight.enabled
        else:
            qtbot.waitUntil(lambda: spotlight.enabled)
    finally:
        release.set()
        controller.cleanup()


class FakeCapsLockMonitor(CapsLockMonitor):
    def __init__(self, succeeds: bool = True) -> None:
        super().__init__()
        self.succeeds = succeeds
        self.running = False

    def start(self) -> None:
        self.running = self.succeeds
        if self.succeeds:
            self.changed.emit(True)
        else:
            self.failed.emit("not supported")

    def stop(self) -> None:
        self.running = False


def test_capslock_operates_without_keystroke_monitor(qapp, qtbot) -> None:
    store = MemoryStore()
    keys = FakeMonitor()
    capslock = FakeCapsLockMonitor()
    controller = AppController(qapp, store, keys, FakeSpotlight(), capslock)
    qtbot.addWidget(controller.capslock)
    controller.tray.panel.capslock_enabled.click()
    assert capslock.running
    assert controller.capslock.isVisible()
    assert not keys.running
    controller.tray.panel.capslock_duration.setValue(0)
    assert store.settings.capslock.duration == 0
    assert not controller.capslock._hide_timer.isActive()
    controller.capslock.position_changed.emit(-400, 100)
    assert (store.settings.capslock.x, store.settings.capslock.y) == (-400, 100)
    controller.cleanup()
    assert not capslock.running
    assert not controller.capslock.isVisible()


def test_capslock_failure_reverts_enabled_state(qapp, qtbot, monkeypatch) -> None:
    store = MemoryStore()
    controller = AppController(
        qapp, store, FakeMonitor(), FakeSpotlight(), FakeCapsLockMonitor(False)
    )
    qtbot.addWidget(controller.capslock)
    warnings = []
    monkeypatch.setattr(controller.tray, "notify_warning", warnings.append)
    controller.tray.panel.capslock_enabled.click()
    assert not store.settings.capslock.enabled
    assert not controller.tray.panel.capslock_enabled.isChecked()
    assert not controller.capslock.isVisible()
    assert "not supported" in warnings[0]
    controller.cleanup()


class FakeInputSourceMonitor(InputSourceMonitor):
    def __init__(self) -> None:
        super().__init__()
        self.running = False

    def start(self) -> None:
        self.running = True
        self.changed.emit("中文（注音）")

    def stop(self) -> None:
        self.running = False


def test_input_source_mode_ignores_capslock_and_can_switch_back(qapp, qtbot, monkeypatch):
    import prkit.app as module

    monkeypatch.setattr(module.sys, "platform", "darwin")
    store = MemoryStore()
    store.settings.language = "zh"
    capslock = FakeCapsLockMonitor()
    sources = FakeInputSourceMonitor()
    controller = AppController(qapp, store, FakeMonitor(), FakeSpotlight(), capslock, sources)
    qtbot.addWidget(controller.capslock)
    controller.set_capslock_enabled(True)
    combo = controller.tray.panel.capslock_mode
    combo.setCurrentIndex(combo.findData("input_source"))
    assert sources.running
    assert not capslock.running
    assert store.settings.capslock.mode == "input_source"
    assert controller.capslock._text == "中文（注音）"
    capslock.changed.emit(True)
    capslock.changed.emit(False)
    assert controller.capslock._text == "中文（注音）"
    sources.changed.emit("英文")
    assert controller.capslock._text == "英文"
    controller.set_language("en")
    sources.changed.emit("中文（注音）")
    assert controller.capslock._text == "Chinese (Zhuyin)"
    combo.setCurrentIndex(combo.findData("capslock"))
    assert not sources.running
    assert capslock.running
    assert controller.capslock._text == "Caps Lock ON"
    sources.changed.emit("中文（注音）")
    assert controller.capslock._text == "Caps Lock ON"
    controller.cleanup()
    assert not sources.running
    assert not capslock.running
