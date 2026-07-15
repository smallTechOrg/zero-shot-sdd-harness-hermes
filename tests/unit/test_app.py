from analytics_agent.api import create_app


def test_app_creates():
    app = create_app()
    assert app.title == "Full Stack Analytics Agent"


def test_health_route():
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "ok"
