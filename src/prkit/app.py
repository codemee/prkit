from __future__ import annotations

import sys
from collections.abc import Sequence
from contextlib import suppress

from PySide6.QtCore import QObject, QSignalBlocker, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from prkit.keyboard import KeyboardMonitor
from prkit.overlays import KeystrokeOverlay
from prkit.settings import SettingsStore, SettingsStoreProtocol
from prkit.spotlight import SpotlightBackend, create_spotlight
from prkit.tray import TrayController


class AppController(QObject):
    def __init__(
        self,
        app: QApplication,
        store: SettingsStoreProtocol | None = None,
        monitor: KeyboardMonitor | None = None,
        spotlight: SpotlightBackend | None = None,
    ) -> None:
        super().__init__()
        self._app = app
        self._store = store or SettingsStore()
        self.settings = self._store.load()
        self.spotlight = spotlight or create_spotlight(self.settings.spotlight)
        self.keystroke = KeystrokeOverlay(self.settings.keystroke)
        self.monitor = monitor or KeyboardMonitor(self)
        self.tray = TrayController(self.settings, self)
        self._shutting_down = False
        self._keystroke_start_pending = False

        self.tray.connect_settings(
            spotlight_enabled=self.set_spotlight_enabled,
            spotlight_color=self.set_spotlight_color,
            spotlight_opacity=self.set_spotlight_opacity,
            spotlight_size=self.set_spotlight_size,
            keystroke_enabled=self.set_keystroke_enabled,
            keystroke_color=self.set_keystroke_color,
            keystroke_opacity=self.set_keystroke_opacity,
        )
        self.tray.exit_requested.connect(self.shutdown)
        self.tray.menu.aboutToShow.connect(self.spotlight.sync_position)
        self.tray.menu.aboutToHide.connect(self._start_pending_keyboard_monitor)
        self.monitor.chord_pressed.connect(self.keystroke.show_chord)
        self.monitor.all_released.connect(self.keystroke.keys_released)
        self.monitor.failed.connect(self._keyboard_failed)
        self._app.aboutToQuit.connect(self.cleanup)

    def start(self) -> None:
        self.tray.show()
        self.spotlight.set_enabled(self.settings.spotlight.enabled)
        if self.settings.keystroke.enabled:
            self.set_keystroke_enabled(True)

    def set_spotlight_enabled(self, enabled: bool) -> None:
        try:
            self.spotlight.set_enabled(enabled)
        except Exception as error:
            self._disable_spotlight_ui()
            self.tray.notify_warning(f"無法啟用聚光燈游標：{error}")
            return
        self.settings.spotlight.enabled = enabled
        self._save()

    def set_spotlight_color(self, color: str) -> None:
        self.settings.spotlight.color = color
        self._apply_spotlight_appearance()

    def set_spotlight_opacity(self, opacity: int) -> None:
        self.settings.spotlight.opacity = opacity
        self._apply_spotlight_appearance()

    def set_spotlight_size(self, size: int) -> None:
        self.settings.spotlight.size = size
        self._apply_spotlight_appearance()

    def _apply_spotlight_appearance(self) -> None:
        value = self.settings.spotlight
        try:
            self.spotlight.set_appearance(value.color, value.opacity, value.size)
        except Exception as error:
            self._disable_spotlight_ui()
            self.tray.notify_warning(f"無法更新聚光燈游標：{error}")
            return
        self._save()

    def _disable_spotlight_ui(self) -> None:
        with suppress(Exception):
            self.spotlight.set_enabled(False)
        self.settings.spotlight.enabled = False
        with QSignalBlocker(self.tray.panel.spotlight_enabled):
            self.tray.panel.set_spotlight_enabled(False)
        self._save()

    def set_keystroke_enabled(self, enabled: bool) -> None:
        if enabled:
            self._keystroke_start_pending = True
            if not self.tray.menu.isVisible():
                QTimer.singleShot(0, self._start_pending_keyboard_monitor)
            return
        else:
            self._keystroke_start_pending = False
            self.monitor.stop()
            self.keystroke.hide_now()
        self.settings.keystroke.enabled = enabled
        self._save()

    def _start_pending_keyboard_monitor(self) -> None:
        if not self._keystroke_start_pending:
            return
        self._keystroke_start_pending = False
        success, error = self.monitor.start()
        if not success:
            self._disable_keystroke_ui()
            self.tray.notify_warning(f"無法啟用按鍵顯示：{error or '未知錯誤'}")
            return
        self.settings.keystroke.enabled = True
        self._save()

    def set_keystroke_color(self, color: str) -> None:
        self.settings.keystroke.color = color
        self._apply_keystroke_appearance()

    def set_keystroke_opacity(self, opacity: int) -> None:
        self.settings.keystroke.opacity = opacity
        self._apply_keystroke_appearance()

    def _apply_keystroke_appearance(self) -> None:
        value = self.settings.keystroke
        self.keystroke.set_appearance(value.color, value.opacity)
        self._save()

    def _keyboard_failed(self, message: str) -> None:
        self._disable_keystroke_ui()
        self.tray.notify_warning(f"按鍵監聽已停止：{message}")

    def _disable_keystroke_ui(self) -> None:
        self._keystroke_start_pending = False
        self.monitor.stop()
        self.keystroke.hide_now()
        self.settings.keystroke.enabled = False
        with QSignalBlocker(self.tray.panel.keystroke_enabled):
            self.tray.panel.set_keystroke_enabled(False)
        self._save()

    def _save(self) -> None:
        self._store.save(self.settings)

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self.cleanup()
        self._app.quit()

    def cleanup(self) -> None:
        self._keystroke_start_pending = False
        self.monitor.stop()
        self.spotlight.set_enabled(False)
        self.keystroke.hide_now()
        self.tray.hide()


def create_application(arguments: Sequence[str] | None = None) -> QApplication:
    app = QApplication(list(arguments) if arguments is not None else sys.argv)
    app.setApplicationName("簡報瑞士刀")
    app.setOrganizationName("prkit")
    app.setQuitOnLastWindowClosed(False)
    return app


def main() -> int:
    app = create_application()
    if not TrayController.is_available():
        QMessageBox.critical(None, "簡報瑞士刀", "此桌面環境沒有可用的系統匣。")
        return 1
    controller = AppController(app)
    controller.start()
    return app.exec()
