from __future__ import annotations

import ctypes
import math
import os
import subprocess
import sys
import time
import uuid
from ctypes import wintypes
from pathlib import Path

from prkit.cursor_watchdog import restore_system_cursors
from prkit.settings import SpotlightSettings

DIB_RGB_COLORS = 0
DI_NORMAL = 0x0003
BI_RGB = 0
IMAGE_CURSOR = 2
SPI_SETCURSORS = 0x0057
CREATE_NO_WINDOW = 0x08000000

SYSTEM_CURSOR_IDS = (
    32512,  # OCR_NORMAL
    32513,  # OCR_IBEAM
    32514,  # OCR_WAIT
    32515,  # OCR_CROSS
    32516,  # OCR_UP
    32642,  # OCR_SIZENWSE
    32643,  # OCR_SIZENESW
    32644,  # OCR_SIZEWE
    32645,  # OCR_SIZENS
    32646,  # OCR_SIZEALL
    32648,  # OCR_NO
    32649,  # OCR_HAND
    32650,  # OCR_APPSTARTING
    32651,  # OCR_HELP
)


class CursorBackendError(RuntimeError):
    pass


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]


class MONO_BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 2)]


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG),
        ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG),
        ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD),
        ("bmBitsPixel", wintypes.WORD),
        ("bmBits", ctypes.c_void_p),
    ]


class CursorWatchdog:
    def __init__(self) -> None:
        self._kernel32 = ctypes.windll.kernel32
        self._kernel32.CreateEventW.restype = wintypes.HANDLE
        self._event_name = f"Local\\PrtoolsCursorRestore-{uuid.uuid4()}"
        self._event = self._kernel32.CreateEventW(None, True, False, self._event_name)
        if not self._event:
            raise CursorBackendError("無法建立游標復原事件")
        try:
            self._process = subprocess.Popen(
                self._command(),
                creationflags=CREATE_NO_WINDOW,
                close_fds=True,
            )
            time.sleep(0.05)
            if self._process.poll() is not None:
                raise CursorBackendError("游標復原監控程序啟動失敗")
        except Exception:
            self._kernel32.CloseHandle(self._event)
            self._event = None
            raise

    def _command(self) -> list[str]:
        sibling = Path(sys.executable).with_name("prkit-cursor-watchdog.exe")
        if sibling.is_file():
            return [str(sibling), str(os.getpid()), self._event_name]
        if "__compiled__" in globals():
            raise CursorBackendError("找不到 prkit-cursor-watchdog.exe")
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        executable = pythonw if pythonw.is_file() else Path(sys.executable)
        return [
            str(executable),
            "-m",
            "prkit.cursor_watchdog",
            str(os.getpid()),
            self._event_name,
        ]

    def stop(self) -> None:
        if not self._event:
            return
        self._kernel32.SetEvent(self._event)
        try:
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.terminate()
        self._kernel32.CloseHandle(self._event)
        self._event = None


class WindowsCursorSpotlight:
    def __init__(self, settings: SpotlightSettings) -> None:
        self._color = settings.color
        self._opacity = settings.opacity
        self._diameter = settings.size
        self._enabled = False
        self._watchdog: CursorWatchdog | None = None

    @property
    def diameter(self) -> int:
        return self._diameter

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        if enabled:
            watchdog = CursorWatchdog()
            try:
                self._replace_cursors()
            except Exception:
                restore_system_cursors()
                watchdog.stop()
                raise
            self._watchdog = watchdog
            self._enabled = True
        else:
            restore_system_cursors()
            self._enabled = False
            if self._watchdog:
                self._watchdog.stop()
                self._watchdog = None

    def sync_position(self) -> None:
        """The Windows implementation is the system cursor and needs no syncing."""

    def set_appearance(self, color: str, opacity: int, diameter: int) -> None:
        self._color = color
        self._opacity = opacity
        self._diameter = diameter
        if self._enabled:
            restore_system_cursors()
            try:
                self._replace_cursors()
            except Exception:
                restore_system_cursors()
                self._enabled = False
                if self._watchdog:
                    self._watchdog.stop()
                    self._watchdog = None
                raise

    def _replace_cursors(self) -> None:
        user32 = ctypes.windll.user32
        user32.LoadCursorW.restype = wintypes.HANDLE
        user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        user32.SetSystemCursor.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        user32.SetSystemCursor.restype = wintypes.BOOL
        user32.DestroyCursor.argtypes = [wintypes.HANDLE]
        originals: list[tuple[int, int]] = []
        for cursor_id in SYSTEM_CURSOR_IDS:
            cursor = user32.LoadCursorW(None, ctypes.c_void_p(cursor_id))
            if cursor:
                originals.append((cursor_id, cursor))
        custom: list[tuple[int, int]] = []
        owned_handles: set[int] = set()
        try:
            for cursor_id, original in originals:
                cursor = _create_spotlight_cursor(
                    original, self._color, self._opacity, self._diameter
                )
                custom.append((cursor_id, cursor))
                owned_handles.add(cursor)
            for cursor_id, cursor in custom:
                if not user32.SetSystemCursor(cursor, cursor_id):
                    raise CursorBackendError(f"無法替換系統游標 {cursor_id}")
                owned_handles.remove(cursor)
        except Exception:
            for cursor in owned_handles:
                user32.DestroyCursor(cursor)
            raise
        if not custom:
            raise CursorBackendError("找不到可替換的 Windows 系統游標")


def _create_spotlight_cursor(original: int, color: str, opacity: int, size: int) -> int:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
    user32.GetIconInfo.restype = wintypes.BOOL
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.DrawIconEx.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
        wintypes.HBRUSH,
        wintypes.UINT,
    ]
    user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
    user32.CreateIconIndirect.restype = wintypes.HANDLE
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC,
        ctypes.POINTER(BITMAPINFO),
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p),
        wintypes.HANDLE,
        wintypes.DWORD,
    ]
    gdi32.CreateBitmap.restype = wintypes.HBITMAP
    gdi32.CreateBitmap.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
    ]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.SelectObject.restype = wintypes.HANDLE
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HBITMAP,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.UINT,
    ]
    icon_info = ICONINFO()
    if not user32.GetIconInfo(original, ctypes.byref(icon_info)):
        raise CursorBackendError("無法讀取原始游標")
    try:
        bitmap_info = BITMAPINFO()
        bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bitmap_info.bmiHeader.biWidth = size
        bitmap_info.bmiHeader.biHeight = -size
        bitmap_info.bmiHeader.biPlanes = 1
        bitmap_info.bmiHeader.biBitCount = 32
        bitmap_info.bmiHeader.biCompression = BI_RGB
        bits = ctypes.c_void_p()
        screen_dc = user32.GetDC(None)
        color_bitmap = gdi32.CreateDIBSection(
            screen_dc,
            ctypes.byref(bitmap_info),
            DIB_RGB_COLORS,
            ctypes.byref(bits),
            None,
            0,
        )
        user32.ReleaseDC(None, screen_dc)
        if not color_bitmap or not bits.value:
            raise CursorBackendError("無法建立游標圖像")
        mask_bitmap = gdi32.CreateBitmap(size, size, 1, 1, None)
        if not mask_bitmap:
            gdi32.DeleteObject(color_bitmap)
            raise CursorBackendError("無法建立游標遮罩")
        try:
            _paint_circle(bits.value, color, opacity, size)
            if icon_info.hbmColor:
                memory_dc = gdi32.CreateCompatibleDC(None)
                previous = gdi32.SelectObject(memory_dc, color_bitmap)
                try:
                    user32.DrawIconEx(
                        memory_dc,
                        size // 2 - icon_info.xHotspot,
                        size // 2 - icon_info.yHotspot,
                        original,
                        0,
                        0,
                        0,
                        None,
                        DI_NORMAL,
                    )
                finally:
                    gdi32.SelectObject(memory_dc, previous)
                    gdi32.DeleteDC(memory_dc)
            else:
                _paint_monochrome_cursor(
                    bits.value,
                    icon_info.hbmMask,
                    icon_info.xHotspot,
                    icon_info.yHotspot,
                    size,
                )
            combined = ICONINFO(
                False,
                size // 2,
                size // 2,
                mask_bitmap,
                color_bitmap,
            )
            cursor = user32.CreateIconIndirect(ctypes.byref(combined))
            if not cursor:
                raise CursorBackendError("無法建立合成游標")
            return cursor
        finally:
            gdi32.DeleteObject(mask_bitmap)
            gdi32.DeleteObject(color_bitmap)
    finally:
        if icon_info.hbmMask:
            gdi32.DeleteObject(icon_info.hbmMask)
        if icon_info.hbmColor:
            gdi32.DeleteObject(icon_info.hbmColor)


def _paint_circle(address: int, color: str, opacity: int, size: int) -> None:
    rgb = int(color.removeprefix("#"), 16)
    red, green, blue = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
    maximum_alpha = round(255 * opacity / 100)
    radius = size / 2 - 1
    center = (size - 1) / 2
    pixels = (ctypes.c_uint32 * (size * size)).from_address(address)
    for y in range(size):
        for x in range(size):
            distance = math.hypot(x - center, y - center)
            coverage = max(0.0, min(1.0, radius + 0.75 - distance))
            alpha = round(maximum_alpha * coverage)
            premultiplied_red = red * alpha // 255
            premultiplied_green = green * alpha // 255
            premultiplied_blue = blue * alpha // 255
            pixels[y * size + x] = (
                alpha << 24
                | premultiplied_red << 16
                | premultiplied_green << 8
                | premultiplied_blue
            )


def _paint_monochrome_cursor(
    destination: int,
    mask_bitmap: int,
    hotspot_x: int,
    hotspot_y: int,
    destination_size: int,
) -> int:
    """Composite a monochrome AND/XOR cursor mask without its bounding box."""
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HBITMAP,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.UINT,
    ]
    bitmap = BITMAP()
    if not gdi32.GetObjectW(mask_bitmap, ctypes.sizeof(bitmap), ctypes.byref(bitmap)):
        raise CursorBackendError("無法讀取單色游標遮罩")
    cursor_width = bitmap.bmWidth
    cursor_height = bitmap.bmHeight // 2
    mask_height = cursor_height * 2
    stride = ((cursor_width + 31) // 32) * 4
    mask_bytes = (ctypes.c_ubyte * (stride * mask_height))()
    bitmap_info = MONO_BITMAPINFO()
    bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bitmap_info.bmiHeader.biWidth = cursor_width
    bitmap_info.bmiHeader.biHeight = -mask_height
    bitmap_info.bmiHeader.biPlanes = 1
    bitmap_info.bmiHeader.biBitCount = 1
    bitmap_info.bmiHeader.biCompression = BI_RGB
    bitmap_info.bmiColors[1] = RGBQUAD(255, 255, 255, 0)
    screen_dc = user32.GetDC(None)
    try:
        rows = gdi32.GetDIBits(
            screen_dc,
            mask_bitmap,
            0,
            mask_height,
            mask_bytes,
            ctypes.byref(bitmap_info),
            DIB_RGB_COLORS,
        )
    finally:
        user32.ReleaseDC(None, screen_dc)
    if rows != mask_height:
        raise CursorBackendError("無法擷取單色游標遮罩")

    def bit_at(x: int, y: int) -> int:
        return (mask_bytes[y * stride + x // 8] >> (7 - x % 8)) & 1

    pixels = (ctypes.c_uint32 * (destination_size * destination_size)).from_address(destination)
    origin_x = destination_size // 2 - hotspot_x
    origin_y = destination_size // 2 - hotspot_y
    painted = 0
    for cursor_y in range(cursor_height):
        target_y = origin_y + cursor_y
        if not 0 <= target_y < destination_size:
            continue
        for cursor_x in range(cursor_width):
            target_x = origin_x + cursor_x
            if not 0 <= target_x < destination_size:
                continue
            and_bit = bit_at(cursor_x, cursor_y)
            xor_bit = bit_at(cursor_x, cursor_y + cursor_height)
            if and_bit and not xor_bit:
                continue
            # Fixed black/white pixels replace XOR inversion. The translucent
            # spotlight beneath them provides a predictable contrast surface.
            pixel = 0xFFFFFFFF if xor_bit and not and_bit else 0xFF000000
            pixels[target_y * destination_size + target_x] = pixel
            painted += 1
    return painted
