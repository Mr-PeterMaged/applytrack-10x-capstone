from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import connect, initialize
from app.models import ApplicationInput, Status


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(title="ApplyTrack", version="1.0.0", lifespan=lifespan)


@app.get("/api/health")
def health():
    with connect() as db:
        db.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@app.post("/api/applications", status_code=201)
def create_application(body: ApplicationInput):
    data = body.model_dump(mode="json")
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO users(id,email,password_hash) VALUES(1,'skeleton@example.test','disabled')")
        result = db.execute(
            "INSERT INTO applications(user_id,company,role,status,applied_on,follow_up_on,notes) VALUES(1,?,?,?,?,?,?)",
            tuple(data.values()),
        )
        return dict(db.execute("SELECT * FROM applications WHERE id=?", (result.lastrowid,)).fetchone())
