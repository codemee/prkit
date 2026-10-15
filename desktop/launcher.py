"""Frozen GUI entry point with a build-only smoke test command."""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        report = Path(sys.argv[2])
        try:
            from desktop_smoke import check_bundle

            result = {"ok": True, "checks": check_bundle()}
        except Exception:
            result = {"ok": False, "error": traceback.format_exc()}
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if result["ok"] else 1

    from prkit.app import main as app_main

    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
