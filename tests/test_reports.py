import io
from pypdf import PdfReader
from app.db import connect
from app.reports import process_one, recover_jobs
from tests.conftest import register


def test_report_snapshot_pdf_and_isolation(client):
    register(client)
    client.post("/api/applications", json={"company": "Original & Co <safe>", "role": "Intern", "notes": "x" * 3000})
    response = client.post("/api/reports")
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert response.headers["Location"].endswith(job_id)
    assert client.get(f"/api/reports/{job_id}/download").status_code == 409
    client.post("/api/applications", json={"company": "Added after snapshot", "role": "Intern"})
    assert process_one()
    result = client.get(f"/api/reports/{job_id}/download")
    assert result.status_code == 200 and result.content.startswith(b"%PDF")
    text = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(result.content)).pages)
    assert "Original & Co <safe>" in text
    assert "Added after snapshot" not in text
    assert client.get(f"/api/reports/{job_id}").json()["status"] == "completed"
    client.cookies.clear()
    register(client, "outsider@example.test")
    assert client.get("/api/reports").json()["items"] == []
    assert client.get(f"/api/reports/{job_id}").status_code == 404
    assert client.get(f"/api/reports/{job_id}/download").status_code == 404


def test_recovery_failure_and_quota(client, monkeypatch):
    register(client)
    job = client.post("/api/reports").json()["id"]
    with connect() as db:
        db.execute("UPDATE report_jobs SET status='running' WHERE id=?", (job,))
    recover_jobs()
    assert client.get(f"/api/reports/{job}").json()["status"] == "queued"
    def fail(_):
        raise RuntimeError("private details must not leak")
    monkeypatch.setattr("app.reports.make_pdf", fail)
    assert process_one()
    result = client.get(f"/api/reports/{job}").json()
    assert result["status"] == "failed"
    assert "private details" not in result["error"]
    for _ in range(3):
        assert client.post("/api/reports").status_code == 202
    assert client.post("/api/reports").status_code == 429


def test_empty_report(client):
    register(client)
    job = client.post("/api/reports").json()["id"]
    process_one()
    pdf = client.get(f"/api/reports/{job}/download").content
    assert "No applications yet" in PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
