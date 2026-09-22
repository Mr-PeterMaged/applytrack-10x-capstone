import secrets
import time
from app.db import connect
from tests.conftest import register


def test_auth_logout_and_expiry(client):
    assert client.get("/api/applications").status_code == 401
    credentials = {"email": "Owner@example.test", "password": secrets.token_urlsafe(18)}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    assert client.get("/api/auth/me").json()["email"] == "owner@example.test"
    token = client.cookies.get("applytrack_session")
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set("applytrack_session", token)
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.clear()
    assert client.post("/api/auth/login", json={**credentials, "password": "incorrect-password"}).status_code == 401
    assert client.post("/api/auth/login", json=credentials).status_code == 200
    with connect() as db:
        db.execute("UPDATE sessions SET expires_at=?", (time.time() - 1,))
    assert client.get("/api/auth/me").status_code == 401


def test_ownership_validation_and_filters(client):
    register(client)
    payload = {"company": "Fictional Studio", "role": "Backend intern", "status": "applied"}
    response = client.post("/api/applications", json=payload)
    assert response.status_code == 201
    application_id = response.json()["id"]
    assert client.get("/api/applications?q=STUDIO&status=applied").json()["total"] == 1
    assert client.post("/api/applications", json={**payload, "company": "  "}).status_code == 422
    assert client.post("/api/applications", json={**payload, "status": "unknown"}).status_code == 422
    assert client.post("/api/applications", json={**payload, "user_id": 2}).status_code == 422
    assert client.post("/api/applications", json=payload, headers={"Origin": "https://attacker.example"}).status_code == 403
    client.cookies.clear()
    register(client, "another@example.test")
    assert client.get("/api/applications").json()["total"] == 0
    assert client.put(f"/api/applications/{application_id}", json=payload).status_code == 404
    assert client.delete(f"/api/applications/{application_id}").status_code == 404


def test_auth_quota(client):
    with connect() as db:
        db.execute("INSERT INTO auth_attempts VALUES('testclient',20,?)", (time.time() + 300,))
    result = client.post("/api/auth/login", json={"email": "nobody@example.test", "password": secrets.token_urlsafe(18)})
    assert result.status_code == 429
    assert int(result.headers["Retry-After"]) > 0
