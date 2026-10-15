from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from prkit.platform import is_wayland


class CapsLockMonitor(QObject):
    """Read the actual lock state independently of the keystroke display."""

    changed = Signal(bool)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._read: Callable[[], bool] | None = None
        self._connection: Any = None
        self._state: bool | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self.stop()
        try:
            if sys.platform == "win32":
                import ctypes

                self._read = lambda: bool(ctypes.windll.user32.GetKeyState(0x14) & 1)
            elif sys.platform == "darwin":
                from AppKit import NSEvent, NSEventModifierFlagCapsLock

                self._read = lambda: bool(NSEvent.modifierFlags() & NSEventModifierFlagCapsLock)
            elif sys.platform.startswith("linux") and not is_wayland():
                from Xlib import X, display

                self._connection = display.Display()
                root = self._connection.screen().root
                self._read = lambda: bool(root.query_pointer().mask & X.LockMask)
            else:
                raise RuntimeError("此平台不支援 Caps Lock 狀態偵測（Linux 需要 X11）。")
            self._poll()
            if self._read is not None:
                self._timer.start()
        except Exception as error:
            self.stop()
            self.failed.emit(str(error))

    def stop(self) -> None:
        self._timer.stop()
        self._read = None
        self._state = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _poll(self) -> None:
        try:
            if self._read is None:
                return
            state = self._read()
            if state != self._state:
                self._state = state
                self.changed.emit(state)
        except Exception as error:
            self.stop()
            self.failed.emit(str(error))
