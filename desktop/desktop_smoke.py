"""Verify a standalone download without altering desktop preferences."""

from __future__ import annotations

import os
import sys


def check_bundle() -> dict[str, object]:
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Smoke tests must run from the frozen executable")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from prkit import __version__
    from prkit.app import create_application
    from prkit.icon import tray_icon
    from prkit.overlays import CapsLockOverlay
    from prkit.settings import CapsLockSettings

    app = create_application([])
    if tray_icon().isNull():
        raise RuntimeError("Missing Qt SVG support")
    overlay = CapsLockOverlay(CapsLockSettings(enabled=True))
    overlay.show_state(True)
    app.processEvents()
    if not overlay.isVisible() or overlay._text != "Caps Lock ON":
        raise RuntimeError("Caps Lock overlay could not be presented")
    overlay.show_input_source("中文（注音）")
    app.processEvents()
    if overlay._text != "中文（注音）":
        raise RuntimeError("Input source overlay did not update")
    overlay.hide_now()
    checks: dict[str, object] = {"version": __version__, "qt": True, "overlay": True}

    if sys.platform == "win32":
        from pynput import keyboard

        from prkit.windows_cursor import CursorWatchdog

        if keyboard.Listener is None:
            raise RuntimeError("Missing pynput Windows backend")
        watchdog = CursorWatchdog()
        try:
            # Signal normal shutdown; never replace or restore system cursors.
            watchdog._kernel32.SetEvent(watchdog._event)
            if watchdog._process.wait(timeout=30) != 0:
                raise RuntimeError("Packaged watchdog did not exit successfully")
        finally:
            watchdog.stop()
        checks["windows_watchdog"] = True
        checks["keyboard_backend"] = True
    elif sys.platform == "darwin":
        from prkit.input_source import MacInputSourceReader
        from prkit.mac_capslock import MacCapsLockState
        from prkit.mac_keyboard import MacKeyboardListener

        if MacKeyboardListener is None:
            raise RuntimeError("Missing native macOS keyboard backend")
        lock = MacCapsLockState()
        try:
            checks["capslock_query"] = isinstance(lock.read(), bool)
        finally:
            lock.close()
        source = MacInputSourceReader()
        try:
            checks["input_source_query"] = bool(source.read().identifier)
            source.observe(lambda: None)
            app.processEvents()
        finally:
            source.close()
        checks["keyboard_backend"] = True
    else:
        raise RuntimeError("Desktop bundles support Windows and macOS only")
    return checks
