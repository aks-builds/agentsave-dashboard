import pytest
import aiosqlite
from agentsave_dashboard.auth import (
    hash_token,
    generate_api_token,
    verify_api_token,
    create_jwt,
    decode_jwt,
)
from agentsave_dashboard.database import init_db
import uuid
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_hash_token_is_deterministic():
    assert hash_token("abc") == hash_token("abc")


@pytest.mark.asyncio
async def test_hash_token_differs_from_input():
    assert hash_token("abc") != "abc"
    assert len(hash_token("abc")) == 64  # SHA-256 hex is 64 chars


@pytest.mark.asyncio
async def test_generate_api_token_returns_tuple():
    raw, hashed = generate_api_token()
    assert raw.startswith("aks_")
    assert hashed == hash_token(raw)
    assert len(raw) > 20


@pytest.mark.asyncio
async def test_verify_api_token_happy_path(db):
    # Insert a user, project, and api_token row
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    token_id = str(uuid.uuid4())
    raw_token = "aks_test_token_12345"
    hashed = hash_token(raw_token)
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO users (id, email, tier, created_at) VALUES (?, ?, ?, ?)",
        (user_id, "test@example.com", "pro", now),
    )
    await db.execute(
        "INSERT INTO projects (id, user_id, name, created_at) VALUES (?, ?, ?, ?)",
        (project_id, user_id, "Test Project", now),
    )
    await db.execute(
        "INSERT INTO api_tokens (id, user_id, project_id, token_hash, name, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (token_id, user_id, project_id, hashed, "test-token", now),
    )
    await db.commit()

    result = await verify_api_token(raw_token, db)
    assert result == project_id


@pytest.mark.asyncio
async def test_verify_api_token_invalid_raises_401(db):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_token("aks_invalid_token", db)
    assert exc_info.value.status_code == 401


def test_jwt_round_trip():
    token = create_jwt("user-1", "test@example.com", "pro")
    payload = decode_jwt(token)
    assert payload["sub"] == "user-1"
    assert payload["email"] == "test@example.com"
    assert payload["tier"] == "pro"


def test_decode_jwt_invalid_raises_401():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        decode_jwt("not.a.valid.jwt")
    assert exc_info.value.status_code == 401
