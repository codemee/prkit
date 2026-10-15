from __future__ import annotations

import ctypes


class MacCapsLockState:
    """Read the HID lock state used by the Caps Lock indicator, not event flags."""

    def __init__(self) -> None:
        self._io = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
        system = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        uint = ctypes.c_uint32
        self._io.IOServiceMatching.argtypes = [ctypes.c_char_p]
        self._io.IOServiceMatching.restype = ctypes.c_void_p
        self._io.IOServiceGetMatchingService.argtypes = [uint, ctypes.c_void_p]
        self._io.IOServiceGetMatchingService.restype = uint
        self._io.IOServiceOpen.argtypes = [uint, uint, uint, ctypes.POINTER(uint)]
        self._io.IOServiceOpen.restype = ctypes.c_int32
        self._io.IOObjectRelease.argtypes = [uint]
        self._io.IOObjectRelease.restype = ctypes.c_int32
        self._io.IOServiceClose.argtypes = [uint]
        self._io.IOServiceClose.restype = ctypes.c_int32
        self._io.IOHIDGetModifierLockState.argtypes = [
            uint,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_bool),
        ]
        self._io.IOHIDGetModifierLockState.restype = ctypes.c_int32
        self._handle = uint()
        service = self._io.IOServiceGetMatchingService(
            0, self._io.IOServiceMatching(b"IOHIDSystem")
        )
        if not service:
            raise RuntimeError("找不到 macOS HID 鍵盤服務")
        try:
            task = uint.in_dll(system, "mach_task_self_").value
            # kIOHIDParamConnectType = 1; only the read API is used below.
            result = self._io.IOServiceOpen(service, task, 1, ctypes.byref(self._handle))
            if result:
                raise RuntimeError(f"無法開啟 macOS HID 鍵盤服務：{result}")
        finally:
            self._io.IOObjectRelease(service)

    def read(self) -> bool:
        if not self._handle.value:
            raise RuntimeError("macOS HID 鍵盤服務已關閉")
        state = ctypes.c_bool()
        # kIOHIDCapsLockState = 1 returns the lock state rather than key-down.
        result = self._io.IOHIDGetModifierLockState(self._handle, 1, ctypes.byref(state))
        if result:
            raise RuntimeError(f"無法讀取 macOS Caps Lock 鎖定狀態：{result}")
        return state.value

    def close(self) -> None:
        if self._handle.value:
            self._io.IOServiceClose(self._handle)
            self._handle.value = 0
