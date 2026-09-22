import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.auth import COOKIE_NAME, DUMMY_HASH, check_auth_limit, create_session, current_user, password_hasher, token_digest
from app.db import connect, initialize
from app.models import ApplicationInput, Credentials, Status
from app.analytics import get_summary
from app.seed import seed_user
from app.reports import ReportWorker, enqueue


@asynccontextmanager
async def lifespan(app):
    initialize()
    worker = ReportWorker() if os.getenv("APPLYTRACK_WORKER", "1") == "1" else None
    if worker:
        worker.start()
    try:
        yield
    finally:
        if worker:
            worker.stop()


app = FastAPI(title="ApplyTrack", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request, call_next):
    origin = request.headers.get("origin")
    if request.method in {"POST", "PUT", "DELETE", "PATCH"} and origin:
        parsed = urlsplit(origin)
        if parsed.netloc != request.headers.get("host") or parsed.scheme != request.url.scheme:
            return JSONResponse({"detail": "Cross-origin requests are not allowed"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if not request.url.path.startswith(("/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/auth/register", status_code=201)
def register(body: Credentials, request: Request, response: Response):
    check_auth_limit(request)
    hashed = password_hasher.hash(body.password)
    try:
        with connect() as db:
            result = db.execute("INSERT INTO users(email,password_hash) VALUES(?,?)", (body.email, hashed))
            user_id = result.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with this email already exists")
    create_session(user_id, response, os.getenv("COOKIE_SECURE") == "1")
    return {"id": user_id, "email": body.email}


@app.post("/api/auth/login")
def login(body: Credentials, request: Request, response: Response):
    check_auth_limit(request)
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (body.email,)).fetchone()
    valid = password_hasher.verify(body.password, user["password_hash"] if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Incorrect email or password")
    create_session(user["id"], response, os.getenv("COOKIE_SECURE") == "1")
    return {"id": user["id"], "email": user["email"]}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return user


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (token_digest(token),))
    response.delete_cookie(COOKIE_NAME, path="/")


@app.get("/api/applications")
def list_applications(status: Status | None = None, q: str = Query("", max_length=120), limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0), user=Depends(current_user)):
    filters, params = ["user_id=?"], [user["id"]]
    if status:
        filters.append("status=?")
        params.append(status.value)
    if q.strip():
        filters.append("(instr(lower(company),lower(?))>0 OR instr(lower(role),lower(?))>0)")
        params.extend([q.strip(), q.strip()])
    where = " AND ".join(filters)
    with connect() as db:
        total = db.execute(f"SELECT COUNT(*) FROM applications WHERE {where}", params).fetchone()[0]
        rows = db.execute(f"SELECT * FROM applications WHERE {where} ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
    return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@app.get("/api/health")
def health():
    with connect() as db:
        db.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@app.post("/api/applications", status_code=201)
def create_application(body: ApplicationInput, user=Depends(current_user)):
    data = body.model_dump(mode="json")
    with connect() as db:
        result = db.execute(
            "INSERT INTO applications(user_id,company,role,status,applied_on,follow_up_on,notes) VALUES(?,?,?,?,?,?,?)",
            (user["id"], *data.values()),
        )
        db.execute("DELETE FROM summary_cache WHERE user_id=?", (user["id"],))
        return dict(db.execute("SELECT * FROM applications WHERE id=?", (result.lastrowid,)).fetchone())


@app.put("/api/applications/{application_id}")
def update_application(application_id: int, body: ApplicationInput, user=Depends(current_user)):
    data = body.model_dump(mode="json")
    with connect() as db:
        result = db.execute("UPDATE applications SET company=?,role=?,status=?,applied_on=?,follow_up_on=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?", (*data.values(), application_id, user["id"]))
        if not result.rowcount:
            raise HTTPException(404, "Application not found")
        db.execute("DELETE FROM summary_cache WHERE user_id=?", (user["id"],))
        return dict(db.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone())


@app.delete("/api/applications/{application_id}", status_code=204)
def delete_application(application_id: int, user=Depends(current_user)):
    with connect() as db:
        result = db.execute("DELETE FROM applications WHERE id=? AND user_id=?", (application_id, user["id"]))
        if not result.rowcount:
            raise HTTPException(404, "Application not found")
        db.execute("DELETE FROM summary_cache WHERE user_id=?", (user["id"],))


@app.get("/api/summary")
def summary(response: Response, user=Depends(current_user)):
    result, cache_status = get_summary(user["id"])
    response.headers["X-Cache"] = cache_status
    return result


@app.post("/api/demo/seed")
def load_demo(user=Depends(current_user)):
    return {"inserted": seed_user(user["id"])}


@app.post("/api/reports", status_code=202)
def request_report(response: Response, user=Depends(current_user)):
    job = enqueue(user["id"])
    response.headers["Location"] = f"/api/reports/{job['id']}"
    return job


@app.get("/api/reports")
def list_reports(user=Depends(current_user)):
    with connect() as db:
        rows = db.execute("SELECT id,status,error,created_at,finished_at FROM report_jobs WHERE user_id=? ORDER BY created_at DESC,rowid DESC LIMIT 20", (user["id"],)).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/reports/{job_id}")
def report_status(job_id: str, user=Depends(current_user)):
    with connect() as db:
        row = db.execute("SELECT id,status,error,created_at,finished_at FROM report_jobs WHERE id=? AND user_id=?", (job_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(404, "Report not found")
    return dict(row)


@app.get("/api/reports/{job_id}/download")
def download_report(job_id: str, user=Depends(current_user)):
    with connect() as db:
        row = db.execute("SELECT status,pdf FROM report_jobs WHERE id=? AND user_id=?", (job_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(404, "Report not found")
    if row["status"] != "completed":
        raise HTTPException(409, "Report is not ready")
    return Response(bytes(row["pdf"]), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="applytrack-report-{job_id}.pdf"'})
