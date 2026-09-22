import time
from datetime import date, timedelta
from app.db import connect
from tests.conftest import register


def test_cache_invalidation_expiry_and_calendar(client):
    register(client)
    assert client.get("/api/summary").headers["X-Cache"] == "MISS"
    assert client.get("/api/summary").headers["X-Cache"] == "HIT"
    payload = {"company": "Cache Co", "role": "Intern", "status": "applied", "follow_up_on": (date.today() - timedelta(days=1)).isoformat()}
    item = client.post("/api/applications", json=payload).json()
    summary = client.get("/api/summary")
    assert summary.headers["X-Cache"] == "MISS"
    assert summary.json()["overdue"] == 1
    assert client.put(f"/api/applications/{item['id']}", json={**payload, "status": "offer"}).status_code == 200
    assert client.get("/api/summary").json()["overdue"] == 0
    assert client.get("/api/summary").headers["X-Cache"] == "HIT"
    with connect() as db:
        db.execute("UPDATE summary_cache SET expires_at=?", (time.time() - 1,))
    assert client.get("/api/summary").headers["X-Cache"] == "MISS"
    with connect() as db:
        db.execute("UPDATE summary_cache SET calendar_day='2000-01-01'")
    assert client.get("/api/summary").headers["X-Cache"] == "MISS"
    client.delete(f"/api/applications/{item['id']}")
    assert client.get("/api/summary").json()["total"] == 0


def test_seed_is_idempotent_and_private(client):
    register(client)
    assert client.post("/api/demo/seed").json()["inserted"] == 8
    assert client.post("/api/demo/seed").json()["inserted"] == 0
    summary = client.get("/api/summary").json()
    assert summary["total"] == 8
    assert summary["by_status"]["interview"] == 2
    client.cookies.clear()
    register(client, "second@example.test")
    assert client.get("/api/summary").json()["total"] == 0
