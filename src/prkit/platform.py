from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


def is_wayland() -> bool:
    return (
        bool(os.environ.get("WAYLAND_DISPLAY"))
        or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    )


def make_window_click_through(widget: QWidget) -> None:
    """Apply native input transparency in addition to Qt's window flags.

    Every implementation is deliberately best-effort: Qt's own transparent-input
    hint remains active if the native API is unavailable.
    """
    window_id = int(widget.winId())
    try:
        if sys.platform == "win32":
            _make_windows_click_through(window_id)
        elif sys.platform == "darwin":
            from PySide6.QtGui import QGuiApplication

            if QGuiApplication.platformName() == "cocoa":
                _make_macos_click_through(window_id)
        elif sys.platform.startswith("linux") and not is_wayland():
            _make_x11_click_through(window_id)
    except (ImportError, OSError, RuntimeError, AttributeError, TypeError):
        return


def configure_overlay_level(widget: QWidget) -> None:
    """Keep macOS overlays above apps but below the menu bar and popup menus."""
    if sys.platform != "darwin":
        return
    try:
        import objc
        from AppKit import (
            NSColor,
            NSFloatingWindowLevel,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowStyleMaskNonactivatingPanel,
        )
        from PySide6.QtGui import QGuiApplication

        if QGuiApplication.platformName() != "cocoa":
            return
        native_view = objc.objc_object(c_void_p=int(widget.winId()))
        native_window = native_view.window()
        native_window.setLevel_(NSFloatingWindowLevel)
        native_window.setHidesOnDeactivate_(False)
        native_window.setHasShadow_(False)
        native_window.setOpaque_(False)
        native_window.setBackgroundColor_(NSColor.clearColor())
        native_window.setStyleMask_(native_window.styleMask() | NSWindowStyleMaskNonactivatingPanel)
        if native_window.respondsToSelector_("setBecomesKeyOnlyIfNeeded:"):
            native_window.setBecomesKeyOnlyIfNeeded_(True)
        native_window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
    except (ImportError, OSError, RuntimeError, AttributeError, TypeError):
        return


def keep_window_topmost(widget: QWidget) -> None:
    """Keep an overlay above other topmost Windows such as the taskbar."""
    if sys.platform != "win32" or not widget.isVisible():
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd_topmost = -1
        no_size = 0x0001
        no_move = 0x0002
        no_activate = 0x0010
        no_owner_z_order = 0x0200
        user32.SetWindowPos(
            int(widget.winId()),
            hwnd_topmost,
            0,
            0,
            0,
            0,
            no_size | no_move | no_activate | no_owner_z_order,
        )
    except (OSError, AttributeError, TypeError):
        return


def _make_windows_click_through(window_id: int) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    get_window_long = user32.GetWindowLongPtrW
    set_window_long = user32.SetWindowLongPtrW
    index_extended_style = -20
    transparent = 0x00000020
    layered = 0x00080000
    no_activate = 0x08000000
    tool_window = 0x00000080
    current = get_window_long(window_id, index_extended_style)
    set_window_long(
        window_id,
        index_extended_style,
        current | transparent | layered | no_activate | tool_window,
    )
    hwnd_topmost = -1
    no_size = 0x0001
    no_move = 0x0002
    no_activate_position = 0x0010
    no_owner_z_order = 0x0200
    user32.SetWindowPos(
        window_id,
        hwnd_topmost,
        0,
        0,
        0,
        0,
        no_size | no_move | no_activate_position | no_owner_z_order,
    )


def _make_macos_click_through(window_id: int) -> None:
    import objc

    native_view = objc.objc_object(c_void_p=window_id)
    native_window = native_view.window()
    native_window.setIgnoresMouseEvents_(True)
    native_window.setAcceptsMouseMovedEvents_(False)


def _make_x11_click_through(window_id: int) -> None:
    from Xlib import display
    from Xlib.ext import shape

    connection = display.Display()
    try:
        window = connection.create_resource_object("window", window_id)
        window.shape_rectangles(shape.SO.Set, shape.SK.Input, 0, 0, 0, [])
        connection.sync()
    finally:
        connection.close()
