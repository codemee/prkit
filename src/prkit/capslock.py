from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from prkit.platform import is_wayland


class CapsLockMonitor(QObject):
    """Read the actual lock state independently of the keystroke display."""

    changed = Signal(bool)
    failed = Signal(str)
    _refresh = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._read: Callable[[], bool] | None = None
        self._connection: Any = None
        self._listener: Any = None
        self._state: bool | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll)
        self._refresh.connect(self._poll)

    def start(self) -> None:
        self.stop()
        try:
            if sys.platform == "win32":
                import ctypes

                self._read = lambda: bool(ctypes.windll.user32.GetKeyState(0x14) & 1)
            elif sys.platform == "darwin":
                from prkit.mac_capslock import MacCapsLockState

                self._connection = MacCapsLockState()
                self._read = self._connection.read
            elif sys.platform.startswith("linux") and not is_wayland():
                from Xlib import X, display

                self._connection = display.Display()
                root = self._connection.screen().root
                self._read = lambda: bool(root.query_pointer().mask & X.LockMask)
            else:
                raise RuntimeError("此平台不支援 Caps Lock 狀態偵測（Linux 需要 X11）。")
            self._poll()
            if self._read is not None:
                if sys.platform == "darwin":
                    self._start_macos_listener()
                self._timer.start()
        except Exception as error:
            self.stop()
            self.failed.emit(str(error))

    def stop(self) -> None:
        self._timer.stop()
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._read = None
        self._state = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _start_macos_listener(self) -> None:
        from prkit.mac_keyboard import MacKeyboardListener

        # Event flags can be transient or disagree with the lock indicator.
        # Events only wake the Qt thread to query the same source as polling.
        listener = MacKeyboardListener(
            on_press=lambda key: None,
            on_release=lambda key: None,
            on_capslock=lambda state: self._refresh.emit(),
        )
        success, _ = listener.start()
        if success:
            self._listener = listener
        else:
            listener.stop()

    @Slot(bool)
    def _set_state(self, state: bool) -> None:
        if self._read is not None and state != self._state:
            self._state = state
            self.changed.emit(state)

    @Slot()
    def _poll(self) -> None:
        try:
            if self._read is None:
                return
            self._set_state(self._read())
        except Exception as error:
            self.stop()
            self.failed.emit(str(error))
