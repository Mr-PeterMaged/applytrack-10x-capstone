import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APPLYTRACK_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("APPLYTRACK_WORKER", "0")
    with TestClient(app) as client:
        yield client


def register(client, email="person@example.test"):
    import secrets
    response = client.post("/api/auth/register", json={"email": email, "password": secrets.token_urlsafe(18)})
    assert response.status_code == 201, response.text
    return response.json()
