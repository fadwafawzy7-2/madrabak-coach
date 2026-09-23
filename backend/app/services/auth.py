"""AuthProvider abstraction.

LocalAuthProvider: email+password with bcrypt and JWT — works fully offline.
SupabaseAuthProvider hook: when SUPABASE_URL is configured, tokens issued by
Supabase GoTrue can be verified instead (documented configuration path; the
rest of the app only depends on `get_current_user_id`).

Never logs passwords or tokens.
"""
from __future__ import annotations

import datetime as dt

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from ..db import db_conn, new_id
from ..settings import get_settings

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_token(user_id: str) -> str:
    s = get_settings()
    payload = {
        "sub": user_id,
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=s.jwt_expires_minutes),
        "iat": dt.datetime.now(dt.timezone.utc),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> str:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid_token")
    return payload["sub"]


def register_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="password_too_short")
    if "@" not in email or len(email) < 5:
        raise HTTPException(status_code=422, detail="invalid_email")
    uid = new_id()
    with db_conn() as conn:
        exists = conn.execute(text("SELECT 1 FROM users WHERE email = :e"), {"e": email}).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="email_exists")
        conn.execute(
            text("INSERT INTO users (id, email, password_hash, auth_provider) VALUES (:i, :e, :p, 'local')"),
            {"i": uid, "e": email, "p": hash_password(password)},
        )
        conn.execute(text("INSERT INTO profiles (user_id) VALUES (:i)"), {"i": uid})
        # start 14-day trial immediately
        s = get_settings()
        conn.execute(
            text(
                "INSERT INTO subscriptions (user_id, status, trial_started_at, trial_ends_at) "
                "VALUES (:i, 'trial', now(), now() + make_interval(days => :d))"
            ),
            {"i": uid, "d": s.trial_days},
        )
    return {"user_id": uid, "token": create_token(uid)}


def login_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    with db_conn() as conn:
        row = conn.execute(
            text("SELECT id, password_hash FROM users WHERE email = :e AND is_active AND deleted_at IS NULL"),
            {"e": email},
        ).fetchone()
    if not row or not row[1] or not verify_password(password, row[1]):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return {"user_id": str(row[0]), "token": create_token(str(row[0]))}


async def get_current_user_id(
    request: Request, creds: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> str:
    if creds is None:
        raise HTTPException(status_code=401, detail="missing_token")
    return decode_token(creds.credentials)
