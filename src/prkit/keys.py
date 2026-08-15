from __future__ import annotations

import sys
from collections.abc import Hashable
from dataclasses import dataclass, field

MODIFIER_ORDER = ("Ctrl", "⌘", "Alt", "⌥", "Shift", "Meta")

SPECIAL_KEYS = {
    "alt": "⌥" if sys.platform == "darwin" else "Alt",
    "alt_l": "⌥" if sys.platform == "darwin" else "Alt",
    "alt_r": "⌥" if sys.platform == "darwin" else "Alt",
    "alt_gr": "AltGr",
    "backspace": "Backspace",
    "caps_lock": "Caps Lock",
    "cmd": "⌘" if sys.platform == "darwin" else "Meta",
    "cmd_l": "⌘" if sys.platform == "darwin" else "Meta",
    "cmd_r": "⌘" if sys.platform == "darwin" else "Meta",
    "ctrl": "Ctrl",
    "ctrl_l": "Ctrl",
    "ctrl_r": "Ctrl",
    "delete": "Delete",
    "down": "↓",
    "end": "End",
    "enter": "Enter",
    "esc": "Esc",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
    "f6": "F6",
    "f7": "F7",
    "f8": "F8",
    "f9": "F9",
    "f10": "F10",
    "f11": "F11",
    "f12": "F12",
    "home": "Home",
    "insert": "Insert",
    "left": "←",
    "media_next": "Next Track",
    "media_play_pause": "Play/Pause",
    "media_previous": "Previous Track",
    "page_down": "Page Down",
    "page_up": "Page Up",
    "pause": "Pause",
    "print_screen": "Print Screen",
    "right": "→",
    "scroll_lock": "Scroll Lock",
    "shift": "Shift",
    "shift_l": "Shift",
    "shift_r": "Shift",
    "space": "Space",
    "tab": "Tab",
    "up": "↑",
}


def key_identity(key: object) -> Hashable:
    name = getattr(key, "name", None)
    if name:
        return ("name", name)
    vk = getattr(key, "vk", None)
    if vk is not None:
        return ("vk", vk)
    char = getattr(key, "char", None)
    if char is not None:
        return ("char", char)
    return ("object", str(key))


def key_label(key: object) -> str:
    name = getattr(key, "name", None)
    if name:
        return SPECIAL_KEYS.get(name, name.replace("_", " ").title())
    char = getattr(key, "char", None)
    if char is not None:
        if char == " ":
            return "Space"
        return char.upper() if len(char) == 1 and char.isalpha() else char
    text = str(key)
    if text.startswith("Key."):
        text = text[4:]
    return SPECIAL_KEYS.get(text, text.replace("_", " ").title())


@dataclass(slots=True)
class KeyChordTracker:
    _pressed: dict[Hashable, str] = field(default_factory=dict)

    def press(self, key: object) -> str | None:
        identity = key_identity(key)
        if identity in self._pressed:
            return None
        self._pressed[identity] = key_label(key)
        return self.label

    def release(self, key: object) -> bool:
        self._pressed.pop(key_identity(key), None)
        return not self._pressed

    def clear(self) -> None:
        self._pressed.clear()

    @property
    def label(self) -> str:
        labels = list(dict.fromkeys(self._pressed.values()))
        modifiers = [label for label in MODIFIER_ORDER if label in labels]
        ordinary = [label for label in labels if label not in MODIFIER_ORDER]
        return " + ".join([*modifiers, *ordinary])
