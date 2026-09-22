"""Short-lived SQLite connections; every mutation uses a transaction."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def database_path():
    return Path(os.environ.get("APPLYTRACK_DB", "data/applytrack.db"))


@contextmanager
def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize():
    with connect() as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('saved','applied','interview','offer','rejected')),
            applied_on TEXT NOT NULL,
            follow_up_on TEXT,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS applications_owner ON applications(user_id, status);
        CREATE TABLE IF NOT EXISTS summary_cache (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            payload TEXT NOT NULL,
            expires_at REAL NOT NULL,
            calendar_day TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS report_jobs (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed')),
            snapshot TEXT NOT NULL,
            pdf BLOB,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT
        );
        CREATE INDEX IF NOT EXISTS jobs_owner ON report_jobs(user_id, created_at);
        CREATE TABLE IF NOT EXISTS auth_attempts (
            key TEXT PRIMARY KEY,
            count INTEGER NOT NULL,
            reset_at REAL NOT NULL
        );
        """)
