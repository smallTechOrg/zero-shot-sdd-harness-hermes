from fastapi.testclient import TestClient

from src.api import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_health_reports_provider_presence_only(no_keys):
    with _client() as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "ok"
        assert data["key_configured"] is False  # no_keys fixture
        # never leaks a key value — only names
        assert "api_key" not in res.text.lower()


def test_get_unknown_run_is_404():
    with _client() as client:
        res = client.get("/runs/nope")
        assert res.status_code == 404
        assert res.json()["detail"]["code"] == "run_not_found"


def test_create_run_rejects_empty_text():
    with _client() as client:
        res = client.post("/runs", json={"text": "", "instruction": "upper"})
        assert res.status_code == 422  # pydantic min_length


def test_run_without_key_fails_gracefully(no_keys):
    """No key → run persists as failed with an actionable message; no 500."""
    # The CSV Analyst run requires a session_id, so create one first.
    with _client() as client:
        res = client.post("/sessions")
        assert res.status_code == 200
        session_id = res.json()["data"]["id"]

        res = client.post("/runs", json={"session_id": session_id, "question": "hello world"})
        assert res.status_code == 200
        run = res.json()["data"]
        assert run["status"] == "failed"
        assert "AGENT_" in run["error_message"]

        # the failed run is persisted and fetchable
        res2 = client.get(f"/runs/{run['run_id']}")
        assert res2.status_code == 200
        assert res2.json()["data"]["status"] == "failed"


def test_frontend_served_at_app():
    with _client() as client:
        res = client.get("/app/")
        assert res.status_code == 200
        assert "CSV Analyst Agent" in res.text
        # styles + js referenced (single-origin)
        assert "styles.css" in res.text
        assert "app.js" in res.text
