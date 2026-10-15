"""Build, archive, and smoke-test a native PRKit desktop bundle."""

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
    archive = ROOT / "dist" / f"{name}.zip"
    if sys.platform == "darwin":
        subprocess.run(
            [
                "ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                "dist/PRKit.app",
                str(archive),
            ],
            cwd=ROOT,
            check=True,
        )
    else:
        shutil.make_archive(str(archive.with_suffix("")), "zip", ROOT / "dist", "PRKit")

    report = ROOT / "build" / "desktop-smoke.json"
    report.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="prkit-smoke-") as temporary:
        extracted = Path(temporary)
        if sys.platform == "darwin":
            subprocess.run(["ditto", "-x", "-k", str(archive), temporary], check=True)
            executable = extracted / "PRKit.app" / "Contents" / "MacOS" / "PRKit"
            subprocess.run(
                ["codesign", "--verify", "--deep", "--strict", str(extracted / "PRKit.app")],
                check=True,
            )
        else:
            shutil.unpack_archive(archive, extracted)
            executable = extracted / "PRKit" / "PRKit.exe"
        result = subprocess.run([str(executable), "--smoke-test", str(report)], timeout=90)
        if report.exists():
            print(report.read_text(encoding="utf-8"), flush=True)
        result.check_returncode()
        if not report.exists() or not json.loads(report.read_text(encoding="utf-8"))["ok"]:
            raise RuntimeError("Frozen executable did not produce a successful smoke-test report")
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Built and verified: {archive}", flush=True)


if __name__ == "__main__":
    main()
