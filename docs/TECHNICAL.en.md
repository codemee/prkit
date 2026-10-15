# Technical Design

[繁體中文](TECHNICAL.md) | [English](TECHNICAL.en.md)

This document describes Presenter Toolkit's cross-platform backends, native macOS integration, and related security boundaries.

## Components and data flow

`AppController` reads and writes settings and coordinates the system tray, spotlight, keyboard monitor, and keystroke overlay. The keyboard backend starts only after the tray panel closes so that event monitoring is not initialized inside the native macOS menu-tracking loop. The backend emits unformatted key-down and key-up events only. `KeyChordTracker` removes duplicate events and maintains the current key set, while `KeystrokeOverlay` displays the last complete combination and delays its fade-out until every key is released.

## macOS spotlight and overlays

macOS has no public API that lets a background application replace the system cursor across applications. The spotlight therefore uses a transparent Qt tool window that follows `QCursor`. The native Cocoa window applies these additional constraints:

- `NSFloatingWindowLevel`: above normal application windows but below the menu bar and pop-up menus.
- `NSWindowStyleMaskNonactivatingPanel` and `WA_ShowWithoutActivating`: showing the overlay does not make it the key window.
- `hidesOnDeactivate = false`: the overlay remains visible when another application becomes active.
- Shadows, borders, and opaque backgrounds are disabled, and all mouse events are ignored.
- The window joins every Space and can appear in full-screen auxiliary spaces.

The cursor position is synchronized once before the tray panel opens. This prevents the spotlight from remaining at a stale position when the native menu-tracking loop pauses Qt timers.

## macOS keyboard monitoring

On macOS, the application creates a Core Graphics event tap using `CGEventTapCreate` at `kCGHIDEventTap` / `kCGHeadInsertEventTap`, always with `kCGEventTapOptionListenOnly`. The HID frontend receives a copy before Carbon global shortcuts or other shortcut utilities handle the event. Listen-only mode guarantees that the callback's return value cannot stop the event from continuing to its destination.

The event tap runs on a dedicated Core Foundation run loop. Its callback never manipulates Qt widgets or timers; it emits a Qt signal to queue data on the main thread. Monitoring is limited to `keyDown`, `keyUp`, and `flagsChanged`:

- Modifier state is rebuilt from event flags to prevent missing or duplicate events from producing stuck keys.
- Left and right modifiers are merged into the displayed Command, Shift, Option, and Control states.
- Keycode 255 is a system-state event and is ignored.
- Caps Lock is displayed as a one-shot key and does not remain in a combination while the lock is active.
- ANSI letters, numbers, arrow keys, and common punctuation use physical keycode mappings; typed text is never recorded.

This backend requires the macOS Input Monitoring permission. The application maintains only the current key state in memory and never stores, logs, or transmits keystroke content.

## Other platforms

- On Windows, the spotlight replaces the real system cursor, and an independent watchdog restores it after an unexpected termination. Keyboard monitoring uses `pynput`.
- On Linux, the spotlight uses a transparent overlay and keyboard monitoring uses `pynput`. X11 has the most complete support; Wayland is constrained by global-input and click-through protocols.

## Caps Lock and input source status

`AppController` selects one monitor using `CapsLockSettings.mode`, sharing the draggable `CapsLockOverlay`. Switching modes stops both monitors and hides the previous indicator before starting the selected source. Signals from the inactive mode cannot replace the current text. Status monitoring operates independently of the keystroke display.

| Platform | Caps Lock source | Input source mode |
| --- | --- | --- |
| Windows | Toggle bit from `GetKeyState(0x14)` | Not implemented; no option shown |
| macOS | IOKit `IOHIDGetModifierLockState` | Selected system input source |
| Linux X11 | Root window `query_pointer()` and `LockMask` | Not implemented; no option shown |
| Wayland | Unsupported; enabling reverts the toggle and reports the error | Unsupported |

### macOS Caps Lock indicator mode

`MacCapsLockState` connects to `IOHIDSystem` using `ctypes` and queries `kIOHIDCapsLockState`. This reads the system lock state rather than the keyboard LED directly. `CapsLockMonitor` polls every 100 ms. When Input Monitoring permission is available, a separate listen-only keyboard monitor also forwards `flagsChanged` notifications through a Qt signal to request a fresh query on the main thread. Polling continues without that permission. Event flags never directly determine the displayed ON/OFF state. Stopping releases the HID connection and keyboard monitor.

When macOS uses Caps Lock to switch input sources, a short press can produce a transient ON followed by OFF; holding the key enables persistent uppercase locking. Language switching and uppercase locking are separate states. The application does not invert or latch the lock state to infer English mode.

### macOS input source mode

`MacInputSourceReader` uses HIToolbox's `TISCopyCurrentKeyboardInputSource` and `TISGetInputSourceProperty` to retrieve the selected source ID and localized name. Each query releases its source reference with `CFRelease`. `InputSourceMonitor` subscribes to distributed notifications named by `kTISNotifySelectedKeyboardInputSourceChanged`, with 100 ms polling as a fallback. Only source changes update the indicator.

- Built-in Zhuyin (`com.apple.inputmethod.TCIM.Zhuyin`) displays `中文（注音）`.
- ABC/U.S. displays `英文`; other sources display their localized names.
- This tracks the selected system input source, not private language modes inside a third-party input method that retains the same source ID.
- This mode uses no keyboard event tap, requires no Input Monitoring permission, and reads no typed text.
- The native notification block must return `None`, never the result of `Signal.emit()`. Returning that result can raise a PyObjC exception and terminate the application when a notification arrives.
- Stopping removes the native observer. Read failures stop monitoring, revert the enabled toggle, and notify the user.

### Presentation and persistence

The overlay updates on the Qt main thread and uses `repaint()` for immediate drawing. Native macOS window animations are disabled, and the nonactivating style is set only when missing. The indicator does not force window activation or call `orderFrontRegardless()`.

Caps Lock mode displays ON/OFF; input source mode displays the source label. Appearance updates preserve the current text. Display duration is 1–60 seconds, or 0 to remain visible. Dragging pauses the timeout; releasing saves the position and restarts the timeout. `QSettings` stores the mode, enabled state, color, opacity, duration, and position under `capslock/*`. Existing settings default to `capslock`; unknown modes and non-macOS platforms fall back to Caps Lock mode.

## Desktop packaging

`desktop/PRKit.spec` includes Python, Qt, and platform dependencies using a Windows one-file EXE and a macOS app bundle. The macOS bundle uses the stable identifier `com.codemee.prkit`, version metadata, and `LSUIElement` to retain menu-bar-only operation. Cloud builds render ICO/ICNS icons from the existing SVG. The ad-hoc-signed app is copied with `ditto`, then `hdiutil` creates a compressed read-only DMG containing the app and an Applications shortcut.

The Windows EXE launches itself with `--cursor-watchdog` to start an independent process, dispatching before Qt loads to avoid opening another GUI. `PYINSTALLER_RESET_ENVIRONMENT=1` gives the watchdog its own extracted runtime so it can outlive the GUI. The parent waits up to 30 seconds for a ready event, confirming that the watchdog opened the parent-process and stop-event handles before enabling the spotlight. Shutdown signals and waits for the watchdog; failed startup cleans up handles. Python installations still support a console-script helper or `python -m prkit.cursor_watchdog`. The spec explicitly collects pynput's dynamically loaded Windows backends.

`desktop/build.py` runs on Windows/macOS runners. It copies only the Windows EXE to a new directory, or verifies and mounts the macOS DMG read-only and checks its Applications shortcut, before executing `--smoke-test`. Reports are written to files because GUI executables may have no stdout. The test does not load user preferences, enable the spotlight, or change cursors. Windows verifies watchdog readiness and normal termination. macOS checks HID/input source queries, observer cleanup, and the app's signature inside the image. Checksums and uploaded packages follow successful tests.

`desktop.yml` builds Windows x64 and macOS arm64 on version tags or manual dispatch. Successful tag builds attach assets to the matching release, creating a draft when necessary. `publish.yml` also runs automatically on `v*` tag pushes, with manual retries and matching-tag/version validation. Runs for the same ref are serialized, and uploads check for existing files. See the [release guide](RELEASING.md).

## Verification

Run these checks before committing:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Manual macOS verification should cover moving the cursor into the menu bar, opening the tray panel, changing focus, Chinese and English input methods, ordinary letters and punctuation, modifier combinations, and combinations already registered by another shortcut utility.

For the status indicator, also verify short Caps Lock presses switching Zhuyin/ABC, holding Caps Lock to enable uppercase locking, switching sources through menus and shortcuts, updating without mouse movement, switching display modes, preserving text across appearance changes, and restoring dragged positions after restart. Automated tests cover event flags not overriding the lock source, native callback return values, source changes and deduplication, failure cleanup, mode switching, and saved settings.

See the [release guide](RELEASING.md) for packaging and publishing, and the [changelog](../CHANGELOG.md) for user-visible changes.
