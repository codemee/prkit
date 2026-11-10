from __future__ import annotations

import sys
from collections.abc import Sequence
from contextlib import suppress
from threading import Event, Thread

from PySide6.QtCore import QObject, QSignalBlocker, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from prkit import autostart
from prkit.capslock import CapsLockMonitor
from prkit.icon import tray_icon
from prkit.input_source import InputSourceMonitor
from prkit.keyboard import KeyboardMonitor
from prkit.language import effective_language, set_qt_language, tr
from prkit.message_dialog import MessageDialog
from prkit.overlays import CapsLockOverlay, KeystrokeOverlay
from prkit.settings import SettingsStore, SettingsStoreProtocol
from prkit.spotlight import SpotlightBackend, create_spotlight
from prkit.tray import TrayController


class AppController(QObject):
    startup_watchdog_ready = Signal(object)
    startup_watchdog_failed = Signal(str)

    def __init__(
        self,
        app: QApplication,
        store: SettingsStoreProtocol | None = None,
        monitor: KeyboardMonitor | None = None,
        spotlight: SpotlightBackend | None = None,
        capslock_monitor: CapsLockMonitor | None = None,
        input_source_monitor: InputSourceMonitor | None = None,
    ) -> None:
        super().__init__()
        self._app = app
        self._store = store or SettingsStore()
        self.settings = self._store.load()
        self.spotlight = spotlight or create_spotlight(self.settings.spotlight)
        self.keystroke = KeystrokeOverlay(self.settings.keystroke)
        self.capslock = CapsLockOverlay(self.settings.capslock)
        self.capslock.setToolTip(
            tr("拖曳以移動狀態提示", effective_language(self.settings.language))
        )
        self.capslock_monitor = capslock_monitor or CapsLockMonitor(self)
        self.input_source_monitor = input_source_monitor or InputSourceMonitor(self)
        if sys.platform != "darwin":
            self.settings.capslock.mode = "capslock"
        self.monitor = monitor or KeyboardMonitor(self)
        self.tray = TrayController(self.settings, self)
        self._shutting_down = False
        self._keystroke_start_pending = False
        self._startup_watchdog_pending = False
        self._startup_cancel = Event()
        self.startup_watchdog_ready.connect(self._finish_startup_spotlight)
        self.startup_watchdog_failed.connect(self._fail_startup_spotlight)

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
        self.tray.autostart_changed.connect(self.set_autostart_enabled)
        self.tray.language_changed.connect(self.set_language)
        self.tray.menu.aboutToShow.connect(self.refresh_autostart)
        self.tray.panel.capslock_enabled_changed.connect(self.set_capslock_enabled)
        self.tray.panel.capslock_color_changed.connect(self.set_capslock_color)
        self.tray.panel.capslock_opacity_changed.connect(self.set_capslock_opacity)
        self.tray.panel.capslock_duration_changed.connect(self.set_capslock_duration)
        self.tray.panel.capslock_mode_changed.connect(self.set_capslock_mode)
        self.capslock_monitor.changed.connect(self._show_capslock_state)
        self.input_source_monitor.changed.connect(self._show_input_source)
        self.input_source_monitor.failed.connect(self._capslock_failed)
        self.capslock_monitor.failed.connect(self._capslock_failed)
        self.capslock.position_changed.connect(self._save_capslock_position)
        self.tray.menu.aboutToShow.connect(self.spotlight.sync_position)
        self.tray.menu.aboutToHide.connect(self._start_pending_keyboard_monitor)
        self.monitor.chord_pressed.connect(self.keystroke.show_chord)
        self.monitor.all_released.connect(self.keystroke.keys_released)
        self.monitor.failed.connect(self._keyboard_failed)
        self._app.aboutToQuit.connect(self.cleanup)

    def start(self) -> None:
        self.refresh_autostart()
        self.tray.show()
        if self.settings.spotlight.enabled:
            if sys.platform == "win32":
                from prkit.windows_cursor import WindowsCursorSpotlight

                if isinstance(self.spotlight, WindowsCursorSpotlight):
                    self._start_spotlight_watchdog()
                else:
                    self.set_spotlight_enabled(True)
            else:
                self.set_spotlight_enabled(True)
        if self.settings.keystroke.enabled:
            self.set_keystroke_enabled(True)
        if self.settings.capslock.enabled:
            self.set_capslock_enabled(True)

    def _start_spotlight_watchdog(self) -> None:
        from prkit.windows_cursor import CursorWatchdog

        self._startup_watchdog_pending = True

        def wait_for_watchdog() -> None:
            try:
                watchdog = CursorWatchdog()
            except Exception as error:
                if not self._startup_cancel.is_set():
                    self.startup_watchdog_failed.emit(str(error))
                return
            if self._startup_cancel.is_set():
                watchdog.stop()
            else:
                self.startup_watchdog_ready.emit(watchdog)

        Thread(target=wait_for_watchdog, name="prkit-startup-watchdog", daemon=True).start()

    def _finish_startup_spotlight(self, watchdog: object) -> None:
        self._startup_watchdog_pending = False
        if self._startup_cancel.is_set() or not self.settings.spotlight.enabled:
            watchdog.stop()
            return
        try:
            self.spotlight.enable_with_watchdog(watchdog)
        except Exception as error:
            self._disable_spotlight_ui()
            self.tray.notify_warning(self._text("無法啟用聚光燈游標：{error}", error=error))

    def _fail_startup_spotlight(self, message: str) -> None:
        self._startup_watchdog_pending = False
        if self.settings.spotlight.enabled and not self._startup_cancel.is_set():
            self._disable_spotlight_ui()
            self.tray.notify_warning(self._text("無法啟用聚光燈游標：{error}", error=message))

    def refresh_autostart(self) -> None:
        try:
            self.tray.set_autostart_checked(autostart.is_enabled())
        except OSError as error:
            self.tray.notify_warning(self._text("無法設定開機自動啟動：{error}", error=error))

    def set_autostart_enabled(self, enabled: bool) -> None:
        try:
            autostart.set_enabled(enabled)
        except OSError as error:
            self.tray.set_autostart_checked(not enabled)
            self.refresh_autostart()
            self.tray.notify_warning(self._text("無法設定開機自動啟動：{error}", error=error))

    def set_language(self, preference: str) -> None:
        if preference not in {"system", "zh", "en"}:
            return
        set_qt_language(self._app, preference)
        self.settings.language = preference
        self.tray.set_language(preference)
        self.capslock.setToolTip(self._text("拖曳以移動狀態提示"))
        self._save()

    def _text(self, source: str, **values: object) -> str:
        return tr(source, effective_language(self.settings.language)).format(**values)

    def set_capslock_enabled(self, enabled: bool) -> None:
        self.settings.capslock.enabled = enabled
        self.capslock_monitor.stop()
        self.input_source_monitor.stop()
        self.capslock.hide_now()
        if enabled:
            if self.settings.capslock.mode == "input_source":
                self.input_source_monitor.start()
            else:
                self.capslock_monitor.start()
        self._save()

    def set_capslock_mode(self, mode: str) -> None:
        if mode not in {"capslock", "input_source"}:
            return
        if mode == "input_source" and sys.platform != "darwin":
            return
        self.settings.capslock.mode = mode
        combo = self.tray.panel.capslock_mode
        with QSignalBlocker(combo):
            combo.setCurrentIndex(combo.findData(mode))
        self.set_capslock_enabled(self.settings.capslock.enabled)

    def _show_capslock_state(self, state: bool) -> None:
        if self.settings.capslock.mode == "capslock":
            self.capslock.show_state(state)

    def _show_input_source(self, name: str) -> None:
        if self.settings.capslock.mode == "input_source":
            self.capslock.show_input_source(self._text(name))

    def set_capslock_color(self, color: str) -> None:
        self.settings.capslock.color = color
        self._apply_capslock_settings()

    def set_capslock_opacity(self, opacity: int) -> None:
        self.settings.capslock.opacity = opacity
        self._apply_capslock_settings()

    def set_capslock_duration(self, duration: int) -> None:
        self.settings.capslock.duration = duration
        self._apply_capslock_settings()

    def _apply_capslock_settings(self) -> None:
        self.capslock.apply_settings()
        self._save()

    def _save_capslock_position(self, x: int, y: int) -> None:
        self.settings.capslock.x, self.settings.capslock.y = x, y
        self._save()

    def _capslock_failed(self, message: str) -> None:
        self.set_capslock_enabled(False)
        with QSignalBlocker(self.tray.panel.capslock_enabled):
            self.tray.panel.capslock_enabled.setChecked(False)
        self.tray.notify_warning(self._text("無法顯示鍵盤狀態：{message}", message=message))

    def set_spotlight_enabled(self, enabled: bool) -> None:
        if self._startup_watchdog_pending:
            self.settings.spotlight.enabled = enabled
            self._save()
            return
        try:
            self.spotlight.set_enabled(enabled)
        except Exception as error:
            self._disable_spotlight_ui()
            self.tray.notify_warning(self._text("無法啟用聚光燈游標：{error}", error=error))
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
            self.tray.notify_warning(self._text("無法更新聚光燈游標：{error}", error=error))
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
            self.tray.notify_warning(
                self._text("無法啟用按鍵顯示：{error}", error=error or self._text("未知錯誤"))
            )
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
        self.tray.notify_warning(self._text("按鍵監聽已停止：{message}", message=message))

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
        self._startup_cancel.set()
        self._keystroke_start_pending = False
        self.capslock_monitor.stop()
        self.input_source_monitor.stop()
        self.capslock.hide_now()
        self.monitor.stop()
        self.spotlight.set_enabled(False)
        self.keystroke.hide_now()
        self.tray.hide()


def create_application(arguments: Sequence[str] | None = None) -> QApplication:
    app = QApplication(list(arguments) if arguments is not None else sys.argv)
    app.setOrganizationName("prkit")
    app.setApplicationName("簡報瑞士刀")
    app.setWindowIcon(tray_icon())
    app.setQuitOnLastWindowClosed(False)
    set_qt_language(app, SettingsStore().load().language)
    return app


def show_message(app: QApplication, icon: QMessageBox.Icon, language: str, message: str) -> None:
    dialog = MessageDialog(app, icon, language, message)
    dialog.exec()


def main() -> int:
    app = create_application()
    from prkit.single_instance import acquire

    try:
        instance_lock = acquire()
    except OSError as error:
        language = effective_language(SettingsStore().load().language)
        show_message(
            app,
            QMessageBox.Icon.Critical,
            language,
            tr("無法檢查是否已有執行中的 PRKit：{error}", language).format(error=error),
        )
        return 1
    if instance_lock is None:
        language = effective_language(SettingsStore().load().language)
        show_message(app, QMessageBox.Icon.Information, language, tr("PRKit 已在執行。", language))
        return 0
    try:
        if not TrayController.is_available():
            language = effective_language(SettingsStore().load().language)
            show_message(
                app,
                QMessageBox.Icon.Critical,
                language,
                tr("此桌面環境沒有可用的系統匣。", language),
            )
            return 1
        controller = AppController(app)
        controller.start()
        return app.exec()
    finally:
        instance_lock.unlock()
