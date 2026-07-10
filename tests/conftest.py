"""Pytest configuration: project-root on sys.path + env loading.

Runs against the REAL Gemini API + edge-tts using the repo-root .env. No stubs.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import config  # noqa: E402

pytest_plugins = []


@pytest.fixture(scope="session", autouse=True)
def _require_keys():
    """Gate: real keys must be present. Fail loudly, never silently stub."""
    if not config.gemini_key_present:
        pytest.exit(
            "AGENT_GEMINI_API_KEY missing from repo-root .env — cannot run real-key tests.",
            returncode=2,
        )
    yield


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from src.main import app

    with TestClient(app) as c:
        yield c
