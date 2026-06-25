from datetime import datetime, timezone, timedelta

from agentsave_dashboard.db import get_db, init_db
from agentsave_dashboard.services.retention import run_retention
from agentsave_dashboard.auth import generate_api_key


async def test_retention_deletes_old_runs_free_tier():
    await init_db()
    raw, hashed = generate_api_key()
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO api_keys (key_hash, label, created_at) VALUES (?, ?, ?)",
            (hashed, "test", datetime.now(timezone.utc).isoformat()),
        )
        old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        new_ts = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("old-run", "langchain", "gpt-4o", 1000, 700, 1, old_ts),
        )
        await db.execute(
            "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("new-run", "langchain", "gpt-4o", 1000, 700, 1, new_ts),
        )
        await db.commit()

        await run_retention(db)

        cursor = await db.execute("SELECT run_id FROM runs")
        remaining = {row[0] for row in await cursor.fetchall()}

    assert "old-run" not in remaining
    assert "new-run" in remaining


async def test_retention_keeps_runs_within_limit():
    await init_db()
    async with get_db() as db:
        ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        await db.execute(
            "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("recent-run", "crewai", "gpt-4o", 500, 350, 1, ts),
        )
        await db.commit()
        await run_retention(db)
        cursor = await db.execute("SELECT run_id FROM runs WHERE run_id = 'recent-run'")
        assert await cursor.fetchone() is not None
