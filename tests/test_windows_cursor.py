import ctypes
import sys

import pytest

from prkit.windows_cursor import (
    ICONINFO,
    CursorBackendError,
    CursorWatchdog,
    _paint_circle,
    _paint_monochrome_cursor,
)


def test_installed_watchdog_uses_sibling_executable(tmp_path, monkeypatch) -> None:
    import os

    executable = tmp_path / "PRKit.exe"
    helper = tmp_path / "prkit-cursor-watchdog.exe"
    helper.touch()
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    watchdog = object.__new__(CursorWatchdog)
    watchdog._event_name = "test-stop-event"
    watchdog._ready_event_name = "test-ready-event"
    assert watchdog._command() == [
        str(helper),
        str(os.getpid()),
        "test-stop-event",
        "test-ready-event",
    ]


def test_frozen_watchdog_uses_same_exe_in_watchdog_mode(tmp_path, monkeypatch) -> None:
    import os

    monkeypatch.setattr(sys, "executable", str(tmp_path / "PRKit.exe"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    watchdog = object.__new__(CursorWatchdog)
    watchdog._event_name = "test-stop-event"
    watchdog._ready_event_name = "test-ready-event"
    assert watchdog._command() == [
        sys.executable,
        "--cursor-watchdog",
        str(os.getpid()),
        "test-stop-event",
        "test-ready-event",
    ]


@pytest.mark.parametrize("failure", [None, "exit", "timeout"])
def test_watchdog_waits_for_readiness_with_independent_runtime(monkeypatch, failure) -> None:
    import os
    from types import SimpleNamespace

    import prkit.windows_cursor as module

    handles = iter([101, 102])
    waits = iter([258, 0])
    closed = []
    spawned = []

    class Process:
        terminated = False

        def poll(self):
            return 1 if failure == "exit" else None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            return 0

    process = Process()

    def spawn(command, **kwargs):
        spawned.append((command, kwargs))
        return process

    def wait(handle, timeout):
        assert handle == 102
        return 258 if failure else next(waits)

    kernel = SimpleNamespace(
        CreateEventW=lambda *args: next(handles),
        WaitForSingleObject=wait,
        SetEvent=lambda handle: True,
        CloseHandle=lambda handle: closed.append(handle),
    )
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("PYINSTALLER_RESET_ENVIRONMENT", "0")
    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    if failure == "timeout":
        times = iter([0, 31])
        monkeypatch.setattr(module.time, "monotonic", lambda: next(times))
    if failure:
        with pytest.raises(CursorBackendError):
            CursorWatchdog()
        assert sorted(closed) == [101, 102]
        assert process.terminated == (failure == "timeout")
    else:
        watchdog = CursorWatchdog()
        assert closed == [102]
        watchdog.stop()
        assert closed == [102, 101]
    assert spawned[0][1]["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert os.environ["PYINSTALLER_RESET_ENVIRONMENT"] == "0"


def test_argb_circle_has_transparent_corners_and_colored_center() -> None:
    size = 48
    pixels = (ctypes.c_uint32 * (size * size))()

    _paint_circle(ctypes.addressof(pixels), "#FF0000", 50, size)

    assert pixels[0] == 0
    center = pixels[(size // 2) * size + size // 2]
    alpha = center >> 24
    red = (center >> 16) & 0xFF
    green = (center >> 8) & 0xFF
    blue = center & 0xFF
    assert 126 <= alpha <= 128
    assert red == alpha
    assert green == 0
    assert blue == 0


@pytest.mark.skipif(sys.platform != "win32", reason="Windows cursor mask test")
def test_ibeam_mask_paints_only_cursor_pixels() -> None:
    from ctypes import wintypes

    size = 96
    pixels = (ctypes.c_uint32 * (size * size))()
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    user32.LoadCursorW.restype = wintypes.HANDLE
    user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
    user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    cursor = user32.LoadCursorW(None, ctypes.c_void_p(32513))
    info = ICONINFO()
    assert user32.GetIconInfo(cursor, ctypes.byref(info))
    try:
        painted = _paint_monochrome_cursor(
            ctypes.addressof(pixels), info.hbmMask, info.xHotspot, info.yHotspot, size
        )
    finally:
        gdi32.DeleteObject(info.hbmMask)
        if info.hbmColor:
            gdi32.DeleteObject(info.hbmColor)

    assert 0 < painted < 200
    assert sum(pixel == 0xFF000000 for pixel in pixels) <= painted
