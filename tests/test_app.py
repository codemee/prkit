from PySide6.QtCore import QObject, Signal

from prkit.app import AppController
from prkit.settings import AppSettings


class MemoryStore:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings.defaults()
        self.save_count = 0

    def load(self) -> AppSettings:
        return self.settings

    def save(self, settings: AppSettings) -> None:
        self.settings = settings
        self.save_count += 1


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
