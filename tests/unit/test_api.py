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
        assert "api_key" not in res.text.lower()


def test_get_unknown_run_is_404():
    with _client() as client:
        res = client.get("/runs/nope")
        assert res.status_code == 404
        assert res.json()["detail"]["code"] == "run_not_found"


def test_create_run_rejects_no_files(no_keys):
    with _client() as client:
        res = client.post("/runs", data={"instruction": "upper"})
        assert res.status_code == 400


def test_run_without_key_fails_gracefully(no_keys):
    """No key → run persists as failed with an actionable message; no 500."""
    with _client() as client:
        from io import BytesIO

        res = client.post(
            "/runs",
            data={
                "instruction": "Summarize the data.",
            },
            files={"files": ("data.csv", BytesIO(b"a,b\n1,2\n"), "text/csv")},
        )
        assert res.status_code == 200
        run = res.json()["data"]
        assert run["status"] == "failed"
        # If not stubbed, integration would execute; here just assert envelope exists
        assert "error_message" in run


def test_frontend_served_at_app():
    with _client() as client:
        res = client.get("/app/")
        assert res.status_code == 200
        assert "CrimAnalyze" in res.text
        assert "styles.css" in res.text
        assert "app.js" in res.text
