import sys
from pathlib import Path

# Ensure repo root is importable so `tests/` can import `src`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Initialise the SQLite schema (incl. Phase 2 `sched` table) before any test.
from src.db import init_db  # noqa: E402

init_db()
