# Phase 4 — Validation, Entry Points, and Docs

## Checklist

- [x] `python -m src` imports cleanly with source-package imports
- [x] Stale root-level duplicate entry files removed
- [x] Startup regression tests added in `tests/unit/test_startup.py`
- [ ] User-facing README/docs reset to current FastAPI + NIM + fraud-detection surface
- [ ] Test config no longer references hard-coded temp paths beyond `tmp_path`

## Commands

```bash
uv run pytest tests/unit -q
uv run pytest -q
uv run python -m src
```

## Known state

- Frontend served at `/app`
- Backend surfaces: `/csv/*`, `/live-db/*`, `/fraud-detection/*`, `/runs`, `/health`
- Default port: `8001` (`PORT` env override supported)
