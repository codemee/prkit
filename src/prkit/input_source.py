from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal, Slot


@dataclass(frozen=True)
class InputSource:
    identifier: str
    name: str

    @property
    def label(self) -> str:
        if self.identifier == "com.apple.inputmethod.TCIM.Zhuyin":
            return "中文（注音）"
        if self.identifier in {"com.apple.keylayout.ABC", "com.apple.keylayout.US"}:
            return "英文"
        return self.name


class MacInputSourceReader:
    """Read the selected input source, independently of Caps Lock and focus."""

    def __init__(self) -> None:
        self._tis = ctypes.CDLL(
            "/System/Library/Frameworks/Carbon.framework/Frameworks/HIToolbox.framework/HIToolbox"
        )
        self._cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        pointer = ctypes.c_void_p
        self._tis.TISCopyCurrentKeyboardInputSource.argtypes = []
        self._tis.TISCopyCurrentKeyboardInputSource.restype = pointer
        self._tis.TISGetInputSourceProperty.argtypes = [pointer, pointer]
        self._tis.TISGetInputSourceProperty.restype = pointer
        self._cf.CFStringGetLength.argtypes = [pointer]
        self._cf.CFStringGetLength.restype = ctypes.c_long
        self._cf.CFStringGetMaximumSizeForEncoding.argtypes = [ctypes.c_long, ctypes.c_uint32]
        self._cf.CFStringGetMaximumSizeForEncoding.restype = ctypes.c_long
        self._cf.CFStringGetCString.argtypes = [
            pointer,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_uint32,
        ]
        self._cf.CFStringGetCString.restype = ctypes.c_bool
        self._cf.CFRelease.argtypes = [pointer]
        self._cf.CFRelease.restype = None
        self._observer: Any = None

    def _string(self, value: int) -> str:
        if not value:
            raise RuntimeError("macOS 未提供輸入來源資訊")
        utf8 = 0x08000100
        size = self._cf.CFStringGetMaximumSizeForEncoding(self._cf.CFStringGetLength(value), utf8)
        buffer = ctypes.create_string_buffer(size + 1)
        if not self._cf.CFStringGetCString(value, buffer, len(buffer), utf8):
            raise RuntimeError("無法讀取 macOS 輸入來源名稱")
        return buffer.value.decode("utf-8")

    def _property(self, source: int, name: str) -> str:
        key = ctypes.c_void_p.in_dll(self._tis, name)
        return self._string(self._tis.TISGetInputSourceProperty(source, key))

    def read(self) -> InputSource:
        source = self._tis.TISCopyCurrentKeyboardInputSource()
        if not source:
            raise RuntimeError("無法取得目前的 macOS 輸入來源")
        try:
            return InputSource(
                self._property(source, "kTISPropertyInputSourceID"),
                self._property(source, "kTISPropertyLocalizedName"),
            )
        finally:
            self._cf.CFRelease(source)

    def observe(self, refresh: Any) -> None:
        from AppKit import NSDistributedNotificationCenter

        name = self._string(
            ctypes.c_void_p.in_dll(self._tis, "kTISNotifySelectedKeyboardInputSourceChanged").value
        )
        center = NSDistributedNotificationCenter.defaultCenter()

        def on_notification(notification: Any) -> None:
            # AppKit's block has a void return type; Signal.emit() can return
            # a non-None value, so do not return its result to PyObjC.
            refresh()

        self._observer = center.addObserverForName_object_queue_usingBlock_(
            name, None, None, on_notification
        )

    def close(self) -> None:
        if self._observer is not None:
            from AppKit import NSDistributedNotificationCenter

            NSDistributedNotificationCenter.defaultCenter().removeObserver_(self._observer)
            self._observer = None


class InputSourceMonitor(QObject):
    changed = Signal(str)
    failed = Signal(str)
    _refresh = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._reader: MacInputSourceReader | None = None
        self._state: InputSource | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll)
        self._refresh.connect(self._poll)

    def start(self) -> None:
        self.stop()
        try:
            if sys.platform != "darwin":
                raise RuntimeError("輸入法狀態顯示目前只支援 macOS")
            self._reader = MacInputSourceReader()
            self._reader.observe(self._refresh.emit)
            self._poll()
            if self._reader is not None:
                self._timer.start()
        except Exception as error:
            self.stop()
            self.failed.emit(str(error))

    def stop(self) -> None:
        self._timer.stop()
        if self._reader is not None:
            self._reader.close()
            self._reader = None
        self._state = None

    @Slot()
    def _poll(self) -> None:
        try:
            if self._reader is None:
                return
            source = self._reader.read()
            if source != self._state:
                self._state = source
                self.changed.emit(source.label)
        except Exception as error:
            self.stop()
            self.failed.emit(str(error))
