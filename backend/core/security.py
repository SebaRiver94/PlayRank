from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from core.config import (
    SECRET_KEY, JWT_ALGORITHM, JWT_ISSUER, JWT_AUDIENCE, ACCESS_TOKEN_EXPIRE_MINUTES,
)
from core.db import db
from core.utils import parse_oid_or_none

# Verifies the existing $2a/$2b bcrypt hashes created by previous versions.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DUMMY_HASH = pwd_context.hash("playrank-timing-equalizer")

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: Optional[str]) -> bool:
    return pwd_context.verify(plain, hashed or DUMMY_HASH)


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(claims, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    """Returns the user id (sub) or None when the token is invalid/expired."""
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER, audience=JWT_AUDIENCE,
        )
    except jwt.PyJWTError:
        return None
    return payload.get("sub")


async def get_user_from_token(token: str) -> Optional[dict]:
    user_oid = parse_oid_or_none(decode_token(token) or "")
    if not user_oid:
        return None
    return await db.users.find_one({"_id": user_oid})


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise unauthorized
    user = await get_user_from_token(credentials.credentials)
    if not user:
        raise unauthorized
    return user
