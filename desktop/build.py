"""Build and smoke-test a standalone EXE or macOS DMG on GitHub runners."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def make_icons() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    from prkit.icon import TRAY_ICON_SVG

    app = QGuiApplication.instance() or QGuiApplication([])
    renderer = QSvgRenderer(QByteArray(TRAY_ICON_SVG))
    assets = ROOT / "build" / "desktop-assets"
    assets.mkdir(parents=True, exist_ok=True)

    def save(size: int, path: Path) -> None:
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        if not image.save(str(path)):
            raise RuntimeError(f"Could not write icon: {path}")

    if sys.platform == "win32":
        save(256, assets / "PRKit.ico")
    else:
        iconset = assets / "PRKit.iconset"
        iconset.mkdir(exist_ok=True)
        for size in (16, 32, 128, 256, 512):
            save(size, iconset / f"icon_{size}x{size}.png")
            save(size * 2, iconset / f"icon_{size}x{size}@2x.png")
        subprocess.run(
            ["iconutil", "--convert", "icns", str(iconset), "--output", str(assets / "PRKit.icns")],
            check=True,
        )
    # Keep the Qt application alive while rendering all icon sizes.
    del app


def main() -> None:
    if sys.platform not in {"win32", "darwin"}:
        raise SystemExit("Build desktop bundles on Windows or macOS")
    from prkit import __version__

    make_icons()
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "desktop/PRKit.spec"],
        cwd=ROOT,
        check=True,
    )
    target = "windows" if sys.platform == "win32" else "macos"
    architecture = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64"}[platform.machine().lower()]
    name = f"PRKit-{__version__}-{target}-{architecture}"
    report = ROOT / "build" / "desktop-smoke.json"
    report.unlink(missing_ok=True)
    if sys.platform == "darwin":
        artifact = ROOT / "dist" / f"{name}.dmg"
        stage = ROOT / "build" / "dmg-stage"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        subprocess.run(
            ["ditto", str(ROOT / "dist" / "PRKit.app"), str(stage / "PRKit.app")], check=True
        )
        (stage / "Applications").symlink_to("/Applications")
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                "PRKit",
                "-srcfolder",
                str(stage),
                "-fs",
                "HFS+",
                "-format",
                "UDZO",
                "-ov",
                str(artifact),
            ],
            check=True,
        )
        subprocess.run(["hdiutil", "verify", str(artifact)], check=True)
        with tempfile.TemporaryDirectory(prefix="prkit-dmg-test-") as temporary:
            mount = Path(temporary) / "mounted"
            mount.mkdir()
            subprocess.run(
                [
                    "hdiutil",
                    "attach",
                    "-readonly",
                    "-nobrowse",
                    "-mountpoint",
                    str(mount),
                    str(artifact),
                ],
                check=True,
            )
            try:
                subprocess.run(
                    ["codesign", "--verify", "--deep", "--strict", str(mount / "PRKit.app")],
                    check=True,
                )
                if not (mount / "Applications").is_symlink():
                    raise RuntimeError("DMG is missing the Applications shortcut")
                smoke_test(mount / "PRKit.app" / "Contents" / "MacOS" / "PRKit", report)
            finally:
                subprocess.run(["hdiutil", "detach", str(mount)], check=True)
    else:
        artifact = ROOT / "dist" / f"{name}.exe"
        shutil.copy2(ROOT / "dist" / "PRKit.exe", artifact)
        # Only the single EXE is copied; no sibling helper or runtime directory.
        with tempfile.TemporaryDirectory(prefix="prkit-exe-test-") as temporary:
            executable = Path(temporary) / artifact.name
            shutil.copy2(artifact, executable)
            smoke_test(executable, report)
    with artifact.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    artifact.with_suffix(artifact.suffix + ".sha256").write_text(
        f"{digest}  {artifact.name}\n", encoding="utf-8"
    )
    print(f"Built and verified: {artifact}", flush=True)


def smoke_test(executable: Path, report: Path) -> None:
    result = subprocess.run([str(executable), "--smoke-test", str(report)], timeout=180)
    if report.exists():
        print(report.read_text(encoding="utf-8"), flush=True)
    result.check_returncode()
    if not report.exists() or not json.loads(report.read_text(encoding="utf-8"))["ok"]:
        raise RuntimeError("Frozen executable did not produce a successful smoke-test report")


if __name__ == "__main__":
    main()
