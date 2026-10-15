# Build with: uv run --group build pyinstaller --noconfirm --clean desktop/PRKit.spec
import sys
from pathlib import Path

from prkit import __version__

root = Path(SPECPATH).parent
assets = root / "build" / "desktop-assets"
is_windows = sys.platform == "win32"
hidden = ["pynput.keyboard._win32", "pynput.mouse._win32"] if is_windows else []
analysis = Analysis(
    [str(root / "desktop" / "launcher.py")],
    pathex=[str(root / "src"), str(root / "desktop")],
    hiddenimports=hidden,
    excludes=["tkinter", "PyQt5", "PyQt6", "PySide2"],
)
exe = EXE(
    PYZ(analysis.pure),
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="PRKit",
    console=False,
    upx=False,
    icon=str(assets / ("PRKit.ico" if is_windows else "PRKit.icns")),
)
parts = [exe, analysis.binaries, analysis.datas]
if is_windows:
    watchdog = Analysis(
        [str(root / "desktop" / "watchdog.py")],
        pathex=[str(root / "src")],
    )
    helper = EXE(
        PYZ(watchdog.pure),
        watchdog.scripts,
        [],
        exclude_binaries=True,
        name="prkit-cursor-watchdog",
        console=False,
        upx=False,
        icon=str(assets / "PRKit.ico"),
    )
    parts.extend([helper, watchdog.binaries, watchdog.datas])
bundle = COLLECT(*parts, name="PRKit", upx=False)
if sys.platform == "darwin":
    app = BUNDLE(
        bundle,
        name="PRKit.app",
        icon=str(assets / "PRKit.icns"),
        bundle_identifier="com.codemee.prkit",
        version=__version__,
        info_plist={
            "CFBundleShortVersionString": __version__,
            "LSUIElement": True,
            "NSHighResolutionCapable": True,
            "NSInputMonitoringUsageDescription": "PRKit uses read-only keyboard monitoring to display keystrokes.",
        },
    )
