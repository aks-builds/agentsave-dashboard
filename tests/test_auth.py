import hashlib
from datetime import datetime, timezone

from agentsave_dashboard.auth import generate_api_key, hash_key
from agentsave_dashboard.db import get_db, init_db


def test_generate_api_key_format():
    raw, hashed = generate_api_key()
    assert raw.startswith("ask-")
    assert len(raw) > 10
    assert hashed == hash_key(raw)


def test_hash_key_is_sha256():
    raw, hashed = generate_api_key()
    expected = hashlib.sha256(raw.encode()).hexdigest()
    assert hashed == expected


async def test_valid_key_passes(client):
    await init_db()
    raw, hashed = generate_api_key()
    async with get_db() as db:
        await db.execute(
            "INSERT INTO api_keys (key_hash, label, created_at) VALUES (?, ?, ?)",
            (hashed, "test", datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()

    resp = await client.get("/api/health")
    assert resp.status_code == 200


async def test_missing_key_returns_401(client):
    resp = await client.get("/api/billing")
    assert resp.status_code == 401
