"""
Back-compat entry point for the huge pre-computed demo dump.

    python -m app.seed
    python -m app.seed --reset
    python -m app.seed --user-email you@gmail.com --reset

Prefer: python scripts/seed_dump.py --create-user --reset
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ is not a package; load seed_dump as the implementation.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from seed_dump import main  # noqa: E402


if __name__ == "__main__":
    if "--create-user" not in sys.argv:
        sys.argv.append("--create-user")
    main()
