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
if is_windows:
    exe = EXE(
        PYZ(analysis.pure),
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name="PRKit",
        console=False,
        upx=False,
        icon=str(assets / "PRKit.ico"),
    )
else:
    exe = EXE(
        PYZ(analysis.pure),
        analysis.scripts,
        [],
        exclude_binaries=True,
        name="PRKit",
        console=False,
        upx=False,
        icon=str(assets / "PRKit.icns"),
    )
    bundle = COLLECT(exe, analysis.binaries, analysis.datas, name="PRKit", upx=False)
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
