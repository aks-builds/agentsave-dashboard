import pytest
import uuid
from datetime import datetime, timezone


async def _seed_user(db) -> tuple[str, str, str]:
    """Insert a user and project. Return (user_id, project_id, jwt_token)."""
    from agentsave_dashboard.auth import create_jwt

    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO users (id, email, tier, created_at) VALUES (?, ?, ?, ?)",
        (user_id, "tokens@example.com", "pro", now),
    )
    await db.execute(
        "INSERT INTO projects (id, user_id, name, created_at) VALUES (?, ?, ?, ?)",
        (project_id, user_id, "Token Project", now),
    )
    await db.commit()
    jwt_token = create_jwt(user_id, "tokens@example.com", "pro")
    return user_id, project_id, jwt_token


@pytest.mark.asyncio
async def test_create_token_returns_raw_token(client, db):
    _, project_id, jwt_token = await _seed_user(db)
    response = await client.post(
        "/api/tokens",
        json={"name": "my-ci-token", "project_id": project_id},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token"].startswith("aks_")
    assert "id" in body


@pytest.mark.asyncio
async def test_create_token_persisted_as_hash(client, db):
    from agentsave_dashboard.auth import hash_token

    _, project_id, jwt_token = await _seed_user(db)
    response = await client.post(
        "/api/tokens",
        json={"name": "hashed-token", "project_id": project_id},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    raw = response.json()["token"]
    cursor = await db.execute(
        "SELECT token_hash FROM api_tokens WHERE token_hash = ?",
        (hash_token(raw),),
    )
    row = await cursor.fetchone()
    assert row is not None  # stored as hash, not plaintext


@pytest.mark.asyncio
async def test_list_tokens(client, db):
    user_id, project_id, jwt_token = await _seed_user(db)
    # Create 2 tokens
    for name in ["token-a", "token-b"]:
        await client.post(
            "/api/tokens",
            json={"name": name, "project_id": project_id},
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
    response = await client.get(
        "/api/tokens",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    names = {t["name"] for t in items}
    assert names == {"token-a", "token-b"}


@pytest.mark.asyncio
async def test_list_tokens_no_auth_returns_401(client, db):
    response = await client.get("/api/tokens")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_raw_token_not_stored_in_db(client, db):
    _, project_id, jwt_token = await _seed_user(db)
    response = await client.post(
        "/api/tokens",
        json={"name": "plain-check", "project_id": project_id},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    raw = response.json()["token"]
    # The raw token must NOT appear anywhere in the DB
    cursor = await db.execute("SELECT token_hash FROM api_tokens")
    rows = await cursor.fetchall()
    stored_hashes = {r["token_hash"] for r in rows}
    assert raw not in stored_hashes
