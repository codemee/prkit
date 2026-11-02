"""Manage per-user login startup without changing application settings."""

from __future__ import annotations

import os
import plistlib
import sys
from contextlib import suppress
from pathlib import Path


def launch_command() -> list[str]:
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return [str(executable)]
    if sys.platform == "win32":
        windowless = executable.with_name("pythonw.exe")
        if windowless.exists():
            executable = windowless
    return [str(executable), "-m", "prkit"]


def is_enabled() -> bool:
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, "PRKit")
            return True
        except FileNotFoundError:
            return False
    return _startup_path().exists()


def set_enabled(enabled: bool) -> None:
    if sys.platform == "win32":
        _set_windows(enabled)
    else:
        path = _startup_path()
        if not enabled:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if sys.platform == "darwin":
                content = plistlib.dumps(
                    {
                        "Label": "com.codemee.prkit",
                        "ProgramArguments": launch_command(),
                        "RunAtLoad": True,
                    }
                )
                path.write_bytes(content)
            else:
                command = " ".join(_desktop_quote(arg) for arg in launch_command())
                path.write_text(
                    "[Desktop Entry]\nType=Application\nName=PRKit\n"
                    f"Exec={command}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n",
                    encoding="utf-8",
                )


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _set_windows(enabled: bool) -> None:
    import subprocess
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            command = subprocess.list2cmdline(launch_command())
            winreg.SetValueEx(key, "PRKit", 0, winreg.REG_SZ, command)
        else:
            with suppress(FileNotFoundError):
                winreg.DeleteValue(key, "PRKit")


def _startup_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / "com.codemee.prkit.plist"
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config / "autostart" / "prkit.desktop"


def _desktop_quote(argument: str) -> str:
    # Desktop Entry Exec uses double quotes, rather than shell quoting.
    escaped = argument.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
    return f'"{escaped}"'
