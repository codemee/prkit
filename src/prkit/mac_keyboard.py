from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass

from CoreFoundation import (
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CFRunLoopStop,
    kCFRunLoopDefaultMode,
)
from Quartz import (
    CGEventGetFlags,
    CGEventGetIntegerValueField,
    CGEventMaskBit,
    CGEventTapCreate,
    CGEventTapEnable,
    CGPreflightListenEventAccess,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
    kCGEventFlagsChanged,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGEventTapOptionListenOnly,
    kCGHeadInsertEventTap,
    kCGHIDEventTap,
    kCGKeyboardEventKeycode,
)


@dataclass(frozen=True, slots=True)
class MacKey:
    name: str | None = None
    char: str | None = None
    vk: int | None = None


SPECIAL_KEYCODES = {
    36: "enter",
    48: "tab",
    49: "space",
    51: "backspace",
    53: "esc",
    54: "cmd_r",
    55: "cmd_l",
    56: "shift_l",
    57: "caps_lock",
    58: "alt_l",
    59: "ctrl_l",
    60: "shift_r",
    61: "alt_r",
    62: "ctrl_r",
    117: "delete",
    123: "left",
    124: "right",
    125: "down",
    126: "up",
}

CHARACTER_KEYCODES = {
    0: "a",
    1: "s",
    2: "d",
    3: "f",
    4: "h",
    5: "g",
    6: "z",
    7: "x",
    8: "c",
    9: "v",
    11: "b",
    12: "q",
    13: "w",
    14: "e",
    15: "r",
    16: "y",
    17: "t",
    18: "1",
    19: "2",
    20: "3",
    21: "4",
    22: "6",
    23: "5",
    25: "9",
    26: "7",
    28: "8",
    29: "0",
    31: "o",
    32: "u",
    34: "i",
    35: "p",
    37: "l",
    38: "j",
    40: "k",
    24: "=",
    27: "-",
    30: "]",
    33: "[",
    39: "'",
    41: ";",
    42: "\\",
    43: ",",
    44: "/",
    45: "n",
    46: "m",
    47: ".",
    50: "`",
}

MODIFIER_FLAGS = {
    55: kCGEventFlagMaskCommand,
    56: kCGEventFlagMaskShift,
    58: kCGEventFlagMaskAlternate,
    59: kCGEventFlagMaskControl,
}


class MacKeyboardListener:
    """Passive macOS event monitor that cannot consume or alter keystrokes."""

    def __init__(
        self,
        on_press: Callable[[object], None],
        on_release: Callable[[object], None],
    ) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._thread: threading.Thread | None = None
        self._loop: object | None = None
        self._ready = threading.Event()
        self._error: str | None = None
        self._pressed_modifiers: set[int] = set()
        self._pressed_keycodes: set[int] = set()

    def start(self) -> tuple[bool, str | None]:
        if not CGPreflightListenEventAccess():
            return False, "請在系統設定的「輸入監控」中允許 ChatGPT"
        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(target=self._run, name="prkit-mac-keyboard", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=2):
            return False, "鍵盤事件監聽啟動逾時"
        return self._error is None, self._error

    def stop(self) -> None:
        loop, self._loop = self._loop, None
        if loop is not None:
            CFRunLoopStop(loop)
        self._thread = None
        self._pressed_modifiers.clear()
        self._pressed_keycodes.clear()

    def _run(self) -> None:
        mask = (
            CGEventMaskBit(kCGEventKeyDown)
            | CGEventMaskBit(kCGEventKeyUp)
            | CGEventMaskBit(kCGEventFlagsChanged)
        )
        tap = CGEventTapCreate(
            kCGHIDEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            mask,
            self._handle_event,
            None,
        )
        if tap is None:
            self._error = "無法建立 macOS 唯讀鍵盤事件監看器"
            self._ready.set()
            return
        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        self._loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._loop, source, kCFRunLoopDefaultMode)
        CGEventTapEnable(tap, True)
        self._ready.set()
        CFRunLoopRun()

    def _handle_event(
        self, proxy: object, event_type: int, event: object, refcon: object
    ) -> object:
        del proxy, refcon
        keycode = int(CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode))
        if event_type == kCGEventFlagsChanged:
            self._update_modifiers(int(CGEventGetFlags(event)))
            if keycode == 57:
                self._press_transient_key(keycode)
            return event
        key = self._key(keycode)
        if key is None:
            return event
        if event_type == kCGEventKeyDown:
            self._pressed_keycodes.add(keycode)
            self._on_press(key)
        elif event_type == kCGEventKeyUp and keycode in self._pressed_keycodes:
            self._release_key(keycode)
        return event

    def _update_modifiers(self, flags: int) -> None:
        for keycode, flag in MODIFIER_FLAGS.items():
            is_pressed = bool(flags & flag)
            was_pressed = keycode in self._pressed_modifiers
            if is_pressed and not was_pressed:
                self._pressed_modifiers.add(keycode)
                self._pressed_keycodes.add(keycode)
                self._on_press(self._key(keycode))
            elif not is_pressed and was_pressed:
                self._pressed_modifiers.remove(keycode)
                self._pressed_keycodes.discard(keycode)
                self._on_release(self._key(keycode))

    def _press_transient_key(self, keycode: int) -> None:
        key = self._key(keycode)
        if key is None:
            return
        self._pressed_keycodes.add(keycode)
        self._on_press(key)
        self._release_key(keycode)

    def _release_key(self, keycode: int) -> None:
        if keycode not in self._pressed_keycodes:
            return
        self._pressed_keycodes.remove(keycode)
        self._on_release(self._key(keycode))

    @staticmethod
    def _key(keycode: int) -> MacKey | None:
        if keycode == 255:
            return None
        name = SPECIAL_KEYCODES.get(keycode)
        return (
            MacKey(name=name, vk=keycode)
            if name
            else MacKey(char=CHARACTER_KEYCODES.get(keycode, f"Key {keycode}"), vk=keycode)
        )
