import pytest
import uuid
from datetime import datetime, timezone, timedelta


async def _seed_events(db, n: int = 5) -> tuple[str, str]:
    """Insert user, project, api_token, and n events. Returns (project_id, raw_token)."""
    from agentsave_dashboard.auth import hash_token

    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    token_id = str(uuid.uuid4())
    raw_token = "aks_metrics_test_token"
    hashed = hash_token(raw_token)
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO users (id, email, tier, created_at) VALUES (?, ?, ?, ?)",
        (user_id, "metrics@example.com", "pro", now),
    )
    await db.execute(
        "INSERT INTO projects (id, user_id, name, created_at) VALUES (?, ?, ?, ?)",
        (project_id, user_id, "Metrics Project", now),
    )
    await db.execute(
        "INSERT INTO api_tokens (id, user_id, project_id, token_hash, name, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (token_id, user_id, project_id, hashed, "metrics-token", now),
    )
    for i in range(n):
        ts = (datetime.now(timezone.utc) - timedelta(days=i)).isoformat()
        await db.execute(
            """
            INSERT INTO events
                (id, project_id, run_id, framework, model_name,
                 tokens_before, tokens_after, iterations_total,
                 iterations_saved, task_success, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()), project_id, f"run-{i}", "langchain",
                "gpt-4o", 12400, 8650, 8, 0, 1, ts,
            ),
        )
    await db.commit()
    return project_id, raw_token


@pytest.mark.asyncio
async def test_compute_metrics_tokens_saved(db):
    from agentsave_dashboard.services.metrics_service import compute_metrics

    project_id, _ = await _seed_events(db, n=3)
    result = await compute_metrics(project_id, "7d", db, 0.000003)

    # Each event saves 12400 - 8650 = 3750 tokens; 3 events = 11250
    assert result.tokens_saved == 11250
    assert abs(result.cost_saved_usd - 11250 * 0.000003) < 1e-9
    assert result.event_count == 3
    assert result.period == "7d"


@pytest.mark.asyncio
async def test_compute_metrics_success_rate(db):
    from agentsave_dashboard.services.metrics_service import compute_metrics
    import aiosqlite

    project_id, _ = await _seed_events(db, n=4)
    # Mark 1 event as failed
    await db.execute(
        "UPDATE events SET task_success = 0 WHERE rowid = (SELECT rowid FROM events LIMIT 1)"
    )
    await db.commit()
    result = await compute_metrics(project_id, "7d", db, 0.000003)
    assert result.success_rate == pytest.approx(0.75, abs=0.01)


@pytest.mark.asyncio
async def test_get_metrics_endpoint(client, db):
    from agentsave_dashboard.auth import create_jwt

    project_id, _ = await _seed_events(db, n=5)

    # Get user_id for JWT
    cursor = await db.execute("SELECT user_id FROM projects WHERE id = ?", (project_id,))
    row = await cursor.fetchone()
    user_id = row["user_id"]

    jwt_token = create_jwt(user_id, "metrics@example.com", "pro")

    response = await client.get(
        f"/api/metrics?project_id={project_id}&period=7d",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["tokens_saved"] == 5 * 3750
    assert body["event_count"] == 5


@pytest.mark.asyncio
async def test_get_metrics_no_auth_returns_401(client, db):
    response = await client.get("/api/metrics?project_id=x&period=7d")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_metrics_invalid_period_returns_422(client, db):
    from agentsave_dashboard.auth import create_jwt

    project_id, _ = await _seed_events(db, n=1)
    cursor = await db.execute("SELECT user_id FROM projects WHERE id = ?", (project_id,))
    row = await cursor.fetchone()
    jwt_token = create_jwt(row["user_id"], "m@example.com", "pro")

    response = await client.get(
        f"/api/metrics?project_id={project_id}&period=1d",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == 422
