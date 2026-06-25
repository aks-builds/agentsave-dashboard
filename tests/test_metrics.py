from datetime import datetime, timezone, timedelta

from agentsave_dashboard.db import get_db, init_db
from agentsave_dashboard.auth import generate_api_key
from agentsave_dashboard.services.aggregator import get_metrics, get_token_buckets


async def _seed_runs(n: int = 3, framework: str = "langchain"):
    await init_db()
    raw, hashed = generate_api_key()
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO api_keys (key_hash, label, created_at) VALUES (?, ?, ?)",
            (hashed, "test", datetime.now(timezone.utc).isoformat()),
        )
        for i in range(n):
            ts = (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat()
            await db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"run-{i}", framework, "gpt-4o", 1000, 700, 1, ts),
            )
        await db.commit()
    return raw


async def test_get_metrics_aggregates_correctly():
    await _seed_runs(n=3)
    async with get_db() as db:
        result = await get_metrics(db)
    assert result["total_runs"] == 3
    assert result["total_tokens_saved"] == 3 * 300
    assert result["reduction_pct"] == 30.0
    assert result["success_rate"] == 100.0
    assert "langchain" in result["by_framework"]


async def test_get_token_buckets_returns_days():
    await _seed_runs(n=2)
    async with get_db() as db:
        buckets = await get_token_buckets(db, days=7)
    assert isinstance(buckets, list)


async def test_metrics_endpoint_requires_auth(client):
    resp = await client.get("/api/metrics")
    assert resp.status_code == 401


async def test_metrics_endpoint_returns_data(client):
    key = await _seed_runs(n=2)
    resp = await client.get("/api/metrics", headers={"Authorization": f"Bearer {key}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] == 2
