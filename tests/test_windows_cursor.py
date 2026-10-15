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


def test_frozen_watchdog_uses_sibling_executable(tmp_path, monkeypatch) -> None:
    import os

    executable = tmp_path / "PRKit.exe"
    helper = tmp_path / "prkit-cursor-watchdog.exe"
    helper.touch()
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    watchdog = object.__new__(CursorWatchdog)
    watchdog._event_name = "test-stop-event"
    assert watchdog._command() == [str(helper), str(os.getpid()), "test-stop-event"]


def test_frozen_watchdog_never_relaunches_gui_as_python(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "executable", str(tmp_path / "PRKit.exe"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    watchdog = object.__new__(CursorWatchdog)
    watchdog._event_name = "test-stop-event"
    with pytest.raises(CursorBackendError, match="prkit-cursor-watchdog.exe"):
        watchdog._command()


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
