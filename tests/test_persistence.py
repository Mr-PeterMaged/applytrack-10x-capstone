from fastapi.testclient import TestClient

from app.db import connect
from app.main import app
from tests.conftest import register


def test_data_and_session_survive_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("APPLYTRACK_DB", str(tmp_path / "restart.db"))
    monkeypatch.setenv("APPLYTRACK_WORKER", "0")
    with TestClient(app) as first:
        register(first)
        first.post("/api/demo/seed")
        cookie = first.cookies.get("applytrack_session")
    with TestClient(app) as second:
        second.cookies.set("applytrack_session", cookie)
        assert second.get("/api/applications").json()["total"] == 8
        assert second.get("/api/auth/me").status_code == 200
        with connect() as db:
            row = db.execute("SELECT password_hash FROM users").fetchone()
            assert row["password_hash"].startswith("$argon2id$")
            assert db.execute("SELECT token_hash FROM sessions").fetchone()[0] != cookie


def test_ui_and_documentation_are_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/reports/{job_id}/download" in schema["paths"]
