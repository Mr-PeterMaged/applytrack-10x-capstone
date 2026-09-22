"""Argon2 passwords and revocable, hashed, eight-hour session tokens."""
import hashlib
import secrets
import time
from fastapi import HTTPException, Request
from pwdlib import PasswordHash
from app.db import connect

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(24))
COOKIE_NAME = "applytrack_session"
SESSION_SECONDS = 8 * 60 * 60


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Sign in to continue")
    with connect() as db:
        user = db.execute("SELECT users.id,users.email FROM users JOIN sessions ON users.id=sessions.user_id WHERE token_hash=? AND expires_at>?", (token_digest(token), time.time())).fetchone()
    if not user:
        raise HTTPException(401, "Session expired; sign in again")
    return dict(user)


def check_auth_limit(request):
    key = request.client.host if request.client else "unknown"
    now = time.time()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM auth_attempts WHERE reset_at<=?", (now,))
        row = db.execute("SELECT * FROM auth_attempts WHERE key=?", (key,)).fetchone()
        if row and row["count"] >= 20:
            raise HTTPException(429, "Too many attempts; try again in five minutes", headers={"Retry-After": str(max(1, int(row["reset_at"] - now)))})
        db.execute("INSERT INTO auth_attempts(key,count,reset_at) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1", (key, now + 300))


def create_session(user_id, response, secure=False):
    token = secrets.token_urlsafe(32)
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE expires_at<=?", (time.time(),))
        db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_digest(token), user_id, time.time() + SESSION_SECONDS))
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True, secure=secure, samesite="strict", path="/")
