from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

SPI_SETCURSORS = 0x0057
SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0
INFINITE = 0xFFFFFFFF


def restore_system_cursors() -> None:
    ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)


def watch(parent_pid: int, stop_event_name: str) -> int:
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenEventW.restype = wintypes.HANDLE
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
        handles = (wintypes.HANDLE * 2)(parent, stop_event)
        result = kernel32.WaitForMultipleObjects(2, handles, False, INFINITE)
        if result == WAIT_OBJECT_0:
            restore_system_cursors()
    finally:
        kernel32.CloseHandle(parent)
        kernel32.CloseHandle(stop_event)
    return 0


def main() -> int:
    if sys.platform != "win32" or len(sys.argv) != 3:
        return 2
    return watch(int(sys.argv[1]), sys.argv[2])


if __name__ == "__main__":
    raise SystemExit(main())
