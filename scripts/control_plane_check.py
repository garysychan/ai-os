#!/usr/bin/env python3
"""Run the AI OS Control Plane consistency check from a source checkout."""

from __future__ import annotations

import sys
from pathlib import Path

# Permit direct execution before the package is installed.
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = _REPOSITORY_ROOT / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from ai_os.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "control-plane",
                "check",
                "--root",
                str(_REPOSITORY_ROOT),
                *sys.argv[1:],
            ]
        )
    )
