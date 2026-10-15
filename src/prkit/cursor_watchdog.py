from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

SPI_SETCURSORS = 0x0057
SYNCHRONIZE = 0x00100000
EVENT_MODIFY_STATE = 0x0002
WAIT_OBJECT_0 = 0
INFINITE = 0xFFFFFFFF


def restore_system_cursors() -> None:
    ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)


def watch(parent_pid: int, stop_event_name: str, ready_event_name: str | None = None) -> int:
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenEventW.restype = wintypes.HANDLE
    kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.SetEvent.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.WaitForMultipleObjects.argtypes = [
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    parent = kernel32.OpenProcess(SYNCHRONIZE, False, parent_pid)
    stop_event = kernel32.OpenEventW(SYNCHRONIZE, False, stop_event_name)
    if not parent or not stop_event:
        restore_system_cursors()
        if parent:
            kernel32.CloseHandle(parent)
        if stop_event:
            kernel32.CloseHandle(stop_event)
        return 1
    try:
        if ready_event_name is not None:
            ready = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, ready_event_name)
            if not ready:
                return 1
            try:
                if not kernel32.SetEvent(ready):
                    return 1
            finally:
                kernel32.CloseHandle(ready)
        handles = (wintypes.HANDLE * 2)(parent, stop_event)
        result = kernel32.WaitForMultipleObjects(2, handles, False, INFINITE)
        if result == WAIT_OBJECT_0:
            restore_system_cursors()
    finally:
        kernel32.CloseHandle(parent)
        kernel32.CloseHandle(stop_event)
    return 0


def main() -> int:
    if sys.platform != "win32" or len(sys.argv) not in {3, 4}:
        return 2
    return watch(int(sys.argv[1]), sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)


if __name__ == "__main__":
    raise SystemExit(main())
