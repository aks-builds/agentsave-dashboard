"""
Integration test: simulates the full SDK → backend → metrics pipeline.

Flow:
  1. A user and project exist in the DB (seeded directly)
  2. SDK client POSTs 10 events to POST /api/events with Bearer API token
  3. Dashboard calls GET /api/metrics with JWT
  4. Metrics correctly reflect all 10 events
  5. A second user's data is invisible to the first user's project query
"""
import pytest
import uuid
from datetime import datetime, timezone

from agentsave_dashboard.auth import create_jwt, hash_token


async def _create_user_and_project(db, email: str) -> tuple[str, str, str]:
    """
    Insert a user, project, and API token.
    Returns (user_id, project_id, raw_api_token).
    """
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    token_id = str(uuid.uuid4())
    raw_token = f"aks_integration_{uuid.uuid4().hex[:12]}"
    hashed = hash_token(raw_token)
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO users (id, email, tier, created_at) VALUES (?, ?, ?, ?)",
        (user_id, email, "pro", now),
    )
    await db.execute(
        "INSERT INTO projects (id, user_id, name, created_at) VALUES (?, ?, ?, ?)",
        (project_id, user_id, f"Project for {email}", now),
    )
    await db.execute(
        "INSERT INTO api_tokens (id, user_id, project_id, token_hash, name, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (token_id, user_id, project_id, hashed, "integration-token", now),
    )
    await db.commit()
    return user_id, project_id, raw_token


EVENT_PAYLOAD = {
    "run_id": "run-integration-001",
    "framework": "langchain",
    "model_name": "gpt-4o",
    "tokens_before": 12400,
    "tokens_after": 8650,
    "iterations_total": 8,
    "iterations_saved": 0,
    "task_success": True,
    "timestamp": "2026-06-23T10:00:00Z",
}

# Expected savings per event
_TOKENS_SAVED_PER_EVENT = 12400 - 8650  # = 3750
_COST_PER_TOKEN = 0.000003


@pytest.mark.asyncio
async def test_full_event_to_metrics_pipeline(client, db):
    """Post 10 events, then verify metrics aggregation."""
    user_id, project_id, raw_token = await _create_user_and_project(
        db, "pipeline@example.com"
    )
    jwt_token = create_jwt(user_id, "pipeline@example.com", "pro")

    # Post 10 events as the SDK would
    for i in range(10):
        payload = dict(EVENT_PAYLOAD, run_id=f"run-{i}")
        response = await client.post(
            "/api/events",
            json=payload,
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert response.status_code == 201, f"Event {i} failed: {response.text}"

    # Fetch metrics via dashboard JWT
    response = await client.get(
        f"/api/metrics?project_id={project_id}&period=7d",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["event_count"] == 10
    assert body["tokens_saved"] == 10 * _TOKENS_SAVED_PER_EVENT
    assert abs(body["cost_saved_usd"] - 10 * _TOKENS_SAVED_PER_EVENT * _COST_PER_TOKEN) < 1e-9
    assert body["success_rate"] == 1.0
    assert body["project_id"] == project_id
    assert body["period"] == "7d"


@pytest.mark.asyncio
async def test_two_projects_do_not_share_metrics(client, db):
    """Events from project A must not appear in project B's metrics."""
    user_a_id, project_a_id, token_a = await _create_user_and_project(
        db, "user_a@example.com"
    )
    user_b_id, project_b_id, token_b = await _create_user_and_project(
        db, "user_b@example.com"
    )
    jwt_b = create_jwt(user_b_id, "user_b@example.com", "pro")

    # Post 5 events to project A only
    for i in range(5):
        await client.post(
            "/api/events",
            json=dict(EVENT_PAYLOAD, run_id=f"run-a-{i}"),
            headers={"Authorization": f"Bearer {token_a}"},
        )

    # Project B should show zero events
    response = await client.get(
        f"/api/metrics?project_id={project_b_id}&period=7d",
        headers={"Authorization": f"Bearer {jwt_b}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["event_count"] == 0
    assert body["tokens_saved"] == 0


@pytest.mark.asyncio
async def test_api_token_last_used_at_is_updated(client, db):
    """verify_api_token must stamp last_used_at on every successful call."""
    _, project_id, raw_token = await _create_user_and_project(db, "stamp@example.com")

    # last_used_at starts as NULL
    cursor = await db.execute(
        "SELECT last_used_at FROM api_tokens WHERE token_hash = ?",
        (hash_token(raw_token),),
    )
    row = await cursor.fetchone()
    assert row["last_used_at"] is None

    await client.post(
        "/api/events",
        json=EVENT_PAYLOAD,
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    cursor = await db.execute(
        "SELECT last_used_at FROM api_tokens WHERE token_hash = ?",
        (hash_token(raw_token),),
    )
    row = await cursor.fetchone()
    assert row["last_used_at"] is not None


@pytest.mark.asyncio
async def test_metrics_cache_populated_after_query(client, db):
    """After GET /api/metrics, metrics_cache must contain an entry."""
    user_id, project_id, raw_token = await _create_user_and_project(
        db, "cache@example.com"
    )
    jwt_token = create_jwt(user_id, "cache@example.com", "pro")

    await client.post(
        "/api/events",
        json=EVENT_PAYLOAD,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    await client.get(
        f"/api/metrics?project_id={project_id}&period=7d",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    cursor = await db.execute(
        "SELECT tokens_saved FROM metrics_cache WHERE project_id = ? AND period = '7d'",
        (project_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["tokens_saved"] == _TOKENS_SAVED_PER_EVENT
