import hashlib
import secrets

from fastapi import HTTPException, Request, status


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    raw = "ask-" + secrets.token_hex(16)
    return raw, hash_key(raw)


async def require_auth(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    raw_key = auth_header[len("Bearer "):]
    key_hash = hash_key(raw_key)

    from agentsave_dashboard.db import get_db
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT key_hash FROM api_keys WHERE key_hash = ?", (key_hash,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return raw_key
