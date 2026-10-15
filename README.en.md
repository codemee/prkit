# PRKit: Presenter Toolkit

[繁體中文](README.md) | [English](README.en.md)

A cross-platform system-tray presentation assistant. The application has no main window; all settings are available from the tray icon's context menu.

## Features

- Spotlight cursor: customizable color, opacity, and circle diameter from 48 to 320 px. Windows uses a real system cursor, while macOS and Linux use a click-through transparent overlay.
- Keystroke display: shows individual keys and key combinations near the bottom center of the screen containing the pointer without intercepting keyboard input.
- Status indicator: a draggable Caps Lock ON/OFF display with customizable appearance and duration; macOS can instead follow the selected Chinese/English input source.
- Persistent preferences: remembers whether each feature is enabled and restores its appearance settings.
- Multi-monitor and high-DPI support: positions and renders using Qt logical pixels.

## Download desktop apps

Download from [GitHub Releases](https://github.com/codemee/prkit/releases/latest), with no separate Python or uv installation:

| Platform | Archive | Launch |
| --- | --- | --- |
| Windows x64 | `PRKit-0.2.1-windows-x64.exe` | Open the executable directly |
| macOS Apple Silicon | `PRKit-0.2.1-macos-arm64.dmg` | Open the DMG and drag `PRKit.app` onto its Applications shortcut |

The Windows download is a single EXE containing the runtime and cursor-recovery watchdog; no additional files are required. The macOS download supports Apple Silicon only. The application appears in the tray/menu bar without opening a main window.

These builds do not use a Windows publisher certificate or Apple Developer ID signing/notarization; macOS uses an ad-hoc signature. Follow your operating system's security prompts to allow a download whose source you have verified. The macOS keystroke display still requires Input Monitoring permission for `PRKit`; input source status does not. Each download has a corresponding `.sha256` checksum file.

Version tags automatically trigger GitHub cloud desktop builds, tests of the standalone EXE and mounted DMG, and PyPI publishing. To build desktop apps manually, run **Build desktop apps** in Actions and download its Artifacts. See the [release guide](docs/RELEASING.md).

## Install from PyPI

Install [uv](https://docs.astral.sh/uv/) first, then run:

```powershell
uv tool install prkit
prkit
```

You can also install from a downloaded project directory:

```powershell
uv tool install .
prkit
```

Or install the latest stable release directly from GitHub. The `latest` tag is updated for every stable release:

```powershell
uv tool install git+https://github.com/codemee/prkit.git@latest
prkit
```

To pin a specific release, replace `latest` with a version tag such as `v0.2.1`.

If the `prkit` command is not found after installation, run `uv tool update-shell` and open a new terminal. To remove the tool, run `uv tool uninstall prkit`.

## Run without installing using uvx

Run directly from PyPI:

```powershell
uvx prkit
```

You can also run from a downloaded project directory or directly from GitHub:

```powershell
uvx --from . prkit
uvx --from git+https://github.com/codemee/prkit.git@latest prkit
```

`uvx` prepares and runs the application in an isolated environment without persistently installing the `prkit` command in the tool directory.

## Caps Lock and input source indicator

Right-click the tray icon and enable status display in the Caps Lock/input source section. A small, rounded rectangle shows `Caps Lock ON` or `Caps Lock OFF`, or the selected input source on macOS, independently of the keystroke display. Enabling it also shows the current state.

On macOS, the display content selector offers Caps Lock indicator or current input source mode. Input source mode follows the selected system input source, including switches made with Caps Lock, shortcuts, or the input menu. Built-in Zhuyin displays `中文（注音）`, ABC/U.S. displays `英文`, and other sources display their names. This mode does not require Input Monitoring permission and is independent of transient Caps Lock changes during language switching.

- Choose a display duration of 1–60 seconds after each state change, or 0 (always visible).
- Customize the background color and opacity; changes preview the indicator.
- Drag the indicator with the left mouse button. The hide timer pauses while dragging and restarts on release. The position is saved across restarts; an unavailable screen falls back to a visible screen.

| Platform | Caps Lock ON/OFF | Current input source |
| --- | --- | --- |
| Windows | Supported | Not implemented; no option shown |
| macOS | Supported | Supported |
| Linux X11 | Supported | Not implemented; no option shown |
| Wayland | Unsupported | Unsupported |

When macOS uses Caps Lock to switch input sources, a short press switches languages; holding it until the Caps Lock symbol appears enables persistent uppercase locking. Choose input source mode to follow Chinese/English; Caps Lock mode follows the system lock state. Input source mode does not infer private language modes within third-party input methods that keep the same source. Enabling status monitoring on Wayland shows a warning and disables it.

## Development

uv manages Python 3.12, the virtual environment, and all dependencies:

```powershell
uv sync
uv run prkit
```

Quality checks:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

## Platform notes

- Windows: no additional permissions are required. Enabling the spotlight temporarily replaces the system cursors; they are restored when the feature is disabled or the application exits. The independently running watchdog installed with the tool restores the cursors if the main process terminates unexpectedly.
- macOS: the keystroke display uses a read-only HID-level event monitor. In **System Settings → Privacy & Security → Input Monitoring**, allow the application that launches `prkit`, such as ChatGPT, Terminal, or another terminal application. The monitor never modifies or intercepts events and can observe a key combination before another shortcut utility handles it.
- Linux: full support targets X11. The desktop environment must provide a StatusNotifierItem or XEmbed system tray. GNOME may require an AppIndicator-style extension.
- Wayland: global input and overlay protocol restrictions mean that keystroke monitoring and click-through behavior are not guaranteed. The application displays a warning in its menu.

Keystroke content is used only for the live on-screen display. It is never written to settings, files, or logs.

See the [technical design](docs/TECHNICAL.en.md) for the implementation architecture, native macOS window levels, permission model, and keyboard event flow.

See the [changelog](CHANGELOG.md) for version changes and the [release guide](docs/RELEASING.md) for cloud packaging and PyPI publishing.
