"""Health endpoint test (no external API calls)."""
from src.config import config


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # We never expose the key value — only presence.
    assert "gemini_key_present" in body
    assert body["gemini_key_present"] is True


def test_cast_listed(client):
    r = client.get("/api/podcast/cast")
    assert r.status_code == 200
    cast = r.json()["cast"]
    assert len(cast) >= 3
    ids = {c["id"] for c in cast}
    assert {"maya", "leo", "nova"}.issubset(ids)


def test_rejects_bad_hosts(client):
    r = client.post(
        "/api/podcast/generate",
        json={"topic": "remote work", "hosts": ["maya", "ghost"]},
    )
    assert r.status_code == 400
