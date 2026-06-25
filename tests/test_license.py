import time
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from agentsave_dashboard.license import resolve_tier, TierInfo, FEATURES_BY_TIER
from agentsave_dashboard.db import get_db, init_db


def _load_private_key():
    with open("scripts/private.pem", "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())


def _make_jwt(tier="pro", seats=5, exp_offset=86400, org="Test Org"):
    private_key = _load_private_key()
    payload = {
        "tier": tier,
        "seats": seats,
        "exp": int(time.time()) + exp_offset,
        "iss": "agentsave",
        "org": org,
        "email": "test@test.com",
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


async def test_no_license_key_returns_free_tier():
    await init_db()
    async with get_db() as db:
        info = await resolve_tier(db)
    assert info.tier == "free"
    assert info.features["history_days"] == 7


async def test_valid_pro_license_returns_pro_tier():
    await init_db()
    token = _make_jwt(tier="pro", seats=5)
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('license_key', ?)", (token,)
        )
        await db.commit()
        info = await resolve_tier(db)
    assert info.tier == "pro"
    assert info.seats_allowed == 5
    assert info.features["history_days"] == 90
    assert info.features["webhook_alerts"] is True
    assert info.expired is False


async def test_expired_license_falls_back_to_free():
    await init_db()
    token = _make_jwt(exp_offset=-3600)
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('license_key', ?)", (token,)
        )
        await db.commit()
        info = await resolve_tier(db)
    assert info.tier == "free"
    assert info.expired is True


async def test_tampered_license_falls_back_to_free():
    await init_db()
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('license_key', ?)",
            ("not.a.real.jwt",),
        )
        await db.commit()
        info = await resolve_tier(db)
    assert info.tier == "free"
    assert info.expired is False


async def test_enterprise_license_unlocks_all_features():
    await init_db()
    token = _make_jwt(tier="enterprise", seats=50)
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('license_key', ?)", (token,)
        )
        await db.commit()
        info = await resolve_tier(db)
    assert info.tier == "enterprise"
    assert info.features["sso_saml"] is True
    assert info.features["audit_logs"] is True
    assert info.features["inferroute"] is True
