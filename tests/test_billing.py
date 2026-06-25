import time
import jwt
from datetime import datetime, timezone

from agentsave_dashboard.db import get_db, init_db
from agentsave_dashboard.auth import generate_api_key


async def _seed_key(client):
    await init_db()
    raw, hashed = generate_api_key()
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO api_keys (key_hash, label, created_at) VALUES (?, ?, ?)",
            (hashed, "test", datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()
    return raw


async def test_billing_returns_free_when_no_license(client):
    key = await _seed_key(client)
    resp = await client.get("/api/billing", headers={"Authorization": f"Bearer {key}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "free"
    assert data["features"]["history_days"] == 7
    assert data["features"]["webhook_alerts"] is False


async def test_billing_returns_pro_with_valid_license(client):
    key = await _seed_key(client)
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    with open("scripts/private.pem", "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    token = jwt.encode(
        {"tier": "pro", "seats": 5, "exp": int(time.time()) + 86400,
         "iss": "agentsave", "org": "Test", "email": "t@t.com"},
        private_key, algorithm="RS256"
    )
    async with get_db() as db:
        await db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('license_key', ?)", (token,))
        await db.commit()

    resp = await client.get("/api/billing", headers={"Authorization": f"Bearer {key}"})
    data = resp.json()
    assert data["tier"] == "pro"
    assert data["features"]["webhook_alerts"] is True
    assert data["expired"] is False


async def test_billing_returns_401_without_key(client):
    resp = await client.get("/api/billing")
    assert resp.status_code == 401
