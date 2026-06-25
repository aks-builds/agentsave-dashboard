from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import aiosqlite
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from agentsave_dashboard.config import get_settings

_BEARER = HTTPBearer()
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_HOURS = 24


def hash_token(raw: str) -> str:
    """Return SHA-256 hex digest of the raw token string."""
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_api_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). raw_token has 'aks_' prefix."""
    raw = "aks_" + secrets.token_urlsafe(32)
    return raw, hash_token(raw)


async def verify_api_token(token: str, db: aiosqlite.Connection) -> str:
    """
    Validate a raw Bearer API token against the api_tokens table.
    Returns the project_id on success.
    Raises HTTP 401 on failure and updates last_used_at on success.
    """
    hashed = hash_token(token)
    cursor = await db.execute(
        "SELECT id, project_id FROM api_tokens WHERE token_hash = ?",
        (hashed,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE api_tokens SET last_used_at = ? WHERE id = ?",
        (now, row["id"]),
    )
    await db.commit()
    return row["project_id"]


def create_jwt(user_id: str, email: str, tier: str) -> str:
    """Create a signed JWT for dashboard user sessions."""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "email": email,
        "tier": tier,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT. Raises HTTP 401 on failure."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_BEARER)],
) -> dict:
    """FastAPI dependency: extract and validate JWT from Authorization header."""
    return decode_jwt(credentials.credentials)
