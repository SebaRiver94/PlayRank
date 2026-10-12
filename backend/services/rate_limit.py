"""MongoDB-backed login throttling (works across workers and restarts)."""
import hashlib
from datetime import datetime, timedelta

from fastapi import HTTPException, Request

from core.config import LOGIN_WINDOW_SECONDS, LOGIN_MAX_FAILURES_PER_EMAIL, LOGIN_MAX_FAILURES_PER_IP
from core.db import db


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _keys(email_normalized: str, request: Request):
    email_key = "email:" + hashlib.sha256(email_normalized.encode()).hexdigest()
    ip_key = "ip:" + _client_ip(request)
    return email_key, ip_key


async def ensure_login_allowed(email_normalized: str, request: Request):
    email_key, ip_key = _keys(email_normalized, request)
    since = datetime.utcnow() - timedelta(seconds=LOGIN_WINDOW_SECONDS)
    email_failures = await db.login_attempts.count_documents({"key": email_key, "created_at": {"$gte": since}})
    ip_failures = await db.login_attempts.count_documents({"key": ip_key, "created_at": {"$gte": since}})
    if email_failures >= LOGIN_MAX_FAILURES_PER_EMAIL or ip_failures >= LOGIN_MAX_FAILURES_PER_IP:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)},
        )


async def record_login_failure(email_normalized: str, request: Request):
    now = datetime.utcnow()
    await db.login_attempts.insert_many([
        {"key": key, "created_at": now} for key in _keys(email_normalized, request)
    ])


async def clear_login_failures(email_normalized: str, request: Request):
    email_key, _ = _keys(email_normalized, request)
    await db.login_attempts.delete_many({"key": email_key})
