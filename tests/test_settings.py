from PySide6.QtCore import QSettings

from prkit.settings import (
    MAX_SPOTLIGHT_SIZE,
    MIN_SPOTLIGHT_SIZE,
    AppSettings,
    SettingsStore,
)


def ini_settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_defaults(tmp_path) -> None:
    settings = SettingsStore(ini_settings(tmp_path)).load()

    assert settings == AppSettings.defaults()
    assert settings.spotlight.size == 96
    assert not settings.spotlight.enabled
    assert not settings.keystroke.enabled


def test_round_trip(tmp_path) -> None:
    backend = ini_settings(tmp_path)
    store = SettingsStore(backend)
    settings = AppSettings.defaults()
    settings.spotlight.enabled = True
    settings.spotlight.color = "#123456"
    settings.spotlight.opacity = 67
    settings.spotlight.size = 184
    settings.keystroke.enabled = True
    settings.keystroke.color = "#ABCDEF"
    settings.keystroke.opacity = 88

    store.save(settings)

    assert SettingsStore(ini_settings(tmp_path)).load() == settings


def test_invalid_values_are_sanitized(tmp_path) -> None:
    backend = ini_settings(tmp_path)
    backend.setValue("spotlight/color", "not-a-color")
    backend.setValue("spotlight/opacity", -10)
    backend.setValue("spotlight/size", 9999)
    backend.setValue("keystroke/opacity", 200)
    backend.sync()

    settings = SettingsStore(ini_settings(tmp_path)).load()

    assert settings.spotlight.color == "#FFD54F"
    assert settings.spotlight.opacity == 10
    assert settings.spotlight.size == MAX_SPOTLIGHT_SIZE
    assert settings.keystroke.opacity == 100

    backend.setValue("spotlight/size", 1)
    backend.sync()
    assert SettingsStore(ini_settings(tmp_path)).load().spotlight.size == MIN_SPOTLIGHT_SIZE
