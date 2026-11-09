"""Keep one GUI process per user across installed and frozen copies."""

from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths


def acquire(directory: Path | None = None) -> QLockFile | None:
    if directory is None:
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        if not location:
            raise OSError("No local application data directory is available")
        directory = Path(location)
    directory.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(directory / "prkit.lock"))
    lock.setStaleLockTime(0)
    if lock.tryLock(0):
        return lock
    if lock.error() == QLockFile.LockError.LockFailedError:
        return None
    raise OSError(f"Could not acquire the PRKit instance lock: {lock.error().name}")
