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


async def test_health_no_auth(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_events_post_success(client):
    key = await _seed_key(client)
    payload = {
        "run_id": "test-run-1",
        "framework": "langchain",
        "model_name": "gpt-4o",
        "tokens_before": 1000,
        "tokens_after": 700,
        "iterations_total": 3,
        "iterations_saved": 0,
        "task_success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    resp = await client.post(
        "/api/events", json=payload, headers={"Authorization": f"Bearer {key}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_events_post_rejected_without_key(client):
    payload = {
        "run_id": "x", "framework": "langchain", "model_name": "gpt-4o",
        "tokens_before": 100, "tokens_after": 70, "iterations_total": 1,
        "iterations_saved": 0, "task_success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    resp = await client.post("/api/events", json=payload)
    assert resp.status_code == 401


async def test_runs_returns_posted_event(client):
    key = await _seed_key(client)
    payload = {
        "run_id": "test-run-get-1",
        "framework": "crewai",
        "model_name": "claude-sonnet-4-6",
        "tokens_before": 2000,
        "tokens_after": 1400,
        "iterations_total": 5,
        "iterations_saved": 0,
        "task_success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await client.post("/api/events", json=payload, headers={"Authorization": f"Bearer {key}"})
    resp = await client.get("/api/runs", headers={"Authorization": f"Bearer {key}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    run_ids = [r["run_id"] for r in data["runs"]]
    assert "test-run-get-1" in run_ids


async def test_runs_reduction_pct_correct(client):
    key = await _seed_key(client)
    payload = {
        "run_id": "test-run-pct-1",
        "framework": "autogen",
        "model_name": "gpt-4o",
        "tokens_before": 1000,
        "tokens_after": 700,
        "iterations_total": 1,
        "iterations_saved": 0,
        "task_success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await client.post("/api/events", json=payload, headers={"Authorization": f"Bearer {key}"})
    resp = await client.get("/api/runs", headers={"Authorization": f"Bearer {key}"})
    runs = resp.json()["runs"]
    run = next(r for r in runs if r["run_id"] == "test-run-pct-1")
    assert abs(run["reduction_pct"] - 30.0) < 0.1
