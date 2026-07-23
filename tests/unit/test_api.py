from fastapi.testclient import TestClient

from src.api import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_health_reports_provider_presence_only(no_keys):
    with _client() as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "ok"
        assert data["key_configured"] is False  # no_keys fixture
        # never leaks a key value — only names
        assert "api_key" not in res.text.lower()

