import secrets


def test_configured_frontend_origin_can_register_through_proxy(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://apply.example.com")
    response = client.post(
        "/api/auth/register",
        json={"email": "proxy@example.test", "password": secrets.token_urlsafe(18)},
        headers={"Origin": "https://apply.example.com"},
    )
    assert response.status_code == 201
    assert client.get("/api/auth/me").status_code == 200


def test_configured_origin_rejects_wrong_scheme_and_other_hosts(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://apply.example.com")
    for origin in ["http://apply.example.com", "https://evil.example.com", "http://testserver"]:
        response = client.post("/api/auth/logout", headers={"Origin": origin})
        assert response.status_code == 403
