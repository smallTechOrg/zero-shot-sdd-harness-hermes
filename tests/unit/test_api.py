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
    with _client() as client:
        res = client.post("/runs", json={"text": "hello world"})
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
  # updated branding for Phase 3 analyst UI
  assert "UP Police Data Analyst" in res.text
  # styles + js referenced (single-origin)
  assert "styles.css" in res.text
  assert "app.js" in res.text


def test_list_runs_returns_empty_list_when_no_runs():
 with _client() as client:
  res = client.get("/runs")
  assert res.status_code == 200
  data = res.json()["data"]
  assert data == []


def test_get_run_history_404_for_missing_run():
 with _client() as client:
  res = client.get("/runs/nope")
  assert res.status_code == 404


def test_run_audit_trace_returns_404_for_missing_run():
 with _client() as client:
  res = client.get("/runs/nope/audit")
  assert res.status_code == 404
  payload = res.json()["detail"]
  assert isinstance(payload, dict)
  assert payload.get("code") == "run_not_found"
