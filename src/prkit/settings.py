from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor

MIN_SPOTLIGHT_SIZE = 48
MAX_SPOTLIGHT_SIZE = 320
DEFAULT_SPOTLIGHT_SIZE = 96


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def valid_color(value: object, fallback: str) -> str:
    color = QColor(str(value))
    return color.name().upper() if color.isValid() else fallback


@dataclass(slots=True)
class SpotlightSettings:
    enabled: bool = False
    color: str = "#FFD54F"
    opacity: int = 45
    size: int = DEFAULT_SPOTLIGHT_SIZE


@dataclass(slots=True)
class KeystrokeSettings:
    enabled: bool = False
    color: str = "#202124"
    opacity: int = 75


@dataclass(slots=True)
class AppSettings:
    spotlight: SpotlightSettings
    keystroke: KeystrokeSettings

    @classmethod
    def defaults(cls) -> AppSettings:
        return cls(SpotlightSettings(), KeystrokeSettings())


class SettingsStoreProtocol(Protocol):
    def load(self) -> AppSettings: ...

    def save(self, settings: AppSettings) -> None: ...


class SettingsStore:
    def __init__(self, backend: QSettings | None = None) -> None:
        self._backend = backend or QSettings()

    def load(self) -> AppSettings:
        defaults = AppSettings.defaults()
        backend = self._backend
        spotlight = SpotlightSettings(
            enabled=backend.value("spotlight/enabled", defaults.spotlight.enabled, type=bool),
            color=valid_color(
                backend.value("spotlight/color", defaults.spotlight.color),
                defaults.spotlight.color,
            ),
            opacity=clamp(
                backend.value("spotlight/opacity", defaults.spotlight.opacity, type=int), 10, 100
            ),
            size=clamp(
                backend.value("spotlight/size", defaults.spotlight.size, type=int),
                MIN_SPOTLIGHT_SIZE,
                MAX_SPOTLIGHT_SIZE,
            ),
        )
        keystroke = KeystrokeSettings(
            enabled=backend.value("keystroke/enabled", defaults.keystroke.enabled, type=bool),
            color=valid_color(
                backend.value("keystroke/color", defaults.keystroke.color),
                defaults.keystroke.color,
            ),
            opacity=clamp(
                backend.value("keystroke/opacity", defaults.keystroke.opacity, type=int),
                10,
                100,
            ),
        )
        return AppSettings(spotlight, keystroke)

    def save(self, settings: AppSettings) -> None:
        values = {
            "spotlight/enabled": settings.spotlight.enabled,
            "spotlight/color": settings.spotlight.color,
            "spotlight/opacity": settings.spotlight.opacity,
            "spotlight/size": settings.spotlight.size,
            "keystroke/enabled": settings.keystroke.enabled,
            "keystroke/color": settings.keystroke.color,
            "keystroke/opacity": settings.keystroke.opacity,
        }
        for key, value in values.items():
            self._backend.setValue(key, value)
        self._backend.sync()
