"""Exercise the instance lock across real Python processes."""

import os
import subprocess
import sys

from prkit.single_instance import acquire


def test_only_one_process_can_own_instance_lock(tmp_path, qapp) -> None:
    command = [
        sys.executable,
        "-c",
        (
            "import sys; from pathlib import Path; "
            "from prkit.single_instance import acquire; "
            "lock = acquire(Path(sys.argv[1])); "
            "sys.exit(0 if lock is not None else 2)"
        ),
        str(tmp_path),
    ]
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"

    lock = acquire(tmp_path)
    assert lock is not None
    try:
        assert subprocess.run(command, env=environment, timeout=15, check=False).returncode == 2
    finally:
        lock.unlock()
    assert subprocess.run(command, env=environment, timeout=15, check=False).returncode == 0
