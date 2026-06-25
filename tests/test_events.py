import pytest
import uuid
from datetime import datetime, timezone


async def _seed_project(db) -> tuple[str, str, str]:
    """Insert user+project+api_token, return (project_id, raw_token, user_id)."""
    from agentsave_dashboard.auth import hash_token

    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    token_id = str(uuid.uuid4())
    raw_token = "aks_test_events_token"
    hashed = hash_token(raw_token)
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO users (id, email, tier, created_at) VALUES (?, ?, ?, ?)",
        (user_id, "events@example.com", "pro", now),
    )
    await db.execute(
        "INSERT INTO projects (id, user_id, name, created_at) VALUES (?, ?, ?, ?)",
        (project_id, user_id, "Events Project", now),
    )
    await db.execute(
        "INSERT INTO api_tokens (id, user_id, project_id, token_hash, name, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (token_id, user_id, project_id, hashed, "events-token", now),
    )
    await db.commit()
    return project_id, raw_token, user_id


VALID_PAYLOAD = {
    "run_id": "run-abc-123",
    "framework": "langchain",
    "model_name": "gpt-4o",
    "tokens_before": 12400,
    "tokens_after": 8650,
    "iterations_total": 8,
    "iterations_saved": 0,
    "task_success": True,
    "timestamp": "2026-06-23T10:00:00Z",
}


@pytest.mark.asyncio
async def test_post_event_happy_path(client, db):
    project_id, raw_token, _ = await _seed_project(db)
    response = await client.post(
        "/api/events",
        json=VALID_PAYLOAD,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    assert "event_id" in body


@pytest.mark.asyncio
async def test_post_event_persists_to_db(client, db):
    project_id, raw_token, _ = await _seed_project(db)
    await client.post(
        "/api/events",
        json=VALID_PAYLOAD,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    cursor = await db.execute("SELECT COUNT(*) FROM events")
    row = await cursor.fetchone()
    assert row[0] == 1


@pytest.mark.asyncio
async def test_post_event_wrong_token_returns_401(client, db):
    response = await client.post(
        "/api/events",
        json=VALID_PAYLOAD,
        headers={"Authorization": "Bearer aks_invalid"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_event_missing_auth_returns_403(client, db):
    response = await client.post("/api/events", json=VALID_PAYLOAD)
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_post_event_invalid_payload_returns_422(client, db):
    _, raw_token, _ = await _seed_project(db)
    bad = dict(VALID_PAYLOAD)
    bad["tokens_before"] = -1  # violates ge=0 constraint
    response = await client.post(
        "/api/events",
        json=bad,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_recent_events_endpoint(client, db):
    """GET /api/events/recent returns events for the project, newest first, limited."""
    from agentsave_dashboard.auth import create_jwt

    project_id, raw_token, user_id = await _seed_project(db)

    payload1 = dict(VALID_PAYLOAD, run_id="run-001", timestamp="2026-06-23T10:00:00Z")
    payload2 = dict(VALID_PAYLOAD, run_id="run-002", timestamp="2026-06-23T11:00:00Z")
    await client.post("/api/events", json=payload1, headers={"Authorization": f"Bearer {raw_token}"})
    await client.post("/api/events", json=payload2, headers={"Authorization": f"Bearer {raw_token}"})

    cursor = await db.execute("SELECT tier FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    jwt = create_jwt(user_id, "events@example.com", row["tier"])

    response = await client.get(
        f"/api/events/recent?project_id={project_id}&limit=10",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["run_id"] == "run-002"
    assert data[1]["run_id"] == "run-001"
    assert "id" in data[0]
    assert "framework" in data[0]
    assert "tokens_before" in data[0]
    assert "tokens_after" in data[0]
    assert "task_success" in data[0]
    assert "timestamp" in data[0]


@pytest.mark.asyncio
async def test_recent_events_endpoint_requires_jwt(client, db):
    """GET /api/events/recent rejects raw API tokens (requires JWT, not SDK token)."""
    project_id, raw_token, _ = await _seed_project(db)
    response = await client.get(
        f"/api/events/recent?project_id={project_id}&limit=10",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_recent_events_limit_respected(client, db):
    """GET /api/events/recent returns at most `limit` events."""
    from agentsave_dashboard.auth import create_jwt

    project_id, raw_token, user_id = await _seed_project(db)

    for i in range(5):
        p = dict(VALID_PAYLOAD, run_id=f"run-{i:03d}", timestamp=f"2026-06-23T{10+i:02d}:00:00Z")
        await client.post("/api/events", json=p, headers={"Authorization": f"Bearer {raw_token}"})

    cursor = await db.execute("SELECT tier FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    jwt = create_jwt(user_id, "events@example.com", row["tier"])

    response = await client.get(
        f"/api/events/recent?project_id={project_id}&limit=3",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 3
