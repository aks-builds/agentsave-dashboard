import pytest
import aiosqlite
from agentsave_dashboard.database import init_db


@pytest.mark.asyncio
async def test_init_db_creates_all_tables():
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in await cursor.fetchall()}
    assert tables == {"users", "projects", "api_tokens", "events", "metrics_cache"}


@pytest.mark.asyncio
async def test_init_db_is_idempotent():
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        await init_db(db)  # should not raise
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        )
        row = await cursor.fetchone()
    assert row[0] == 5


@pytest.mark.asyncio
async def test_users_table_columns():
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        cursor = await db.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in await cursor.fetchall()}
    assert {"id", "email", "stripe_customer_id", "tier", "created_at"} <= cols


@pytest.mark.asyncio
async def test_events_table_columns():
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        cursor = await db.execute("PRAGMA table_info(events)")
        cols = {row[1] for row in await cursor.fetchall()}
    expected = {
        "id", "project_id", "run_id", "framework", "model_name",
        "tokens_before", "tokens_after", "iterations_total",
        "iterations_saved", "task_success", "timestamp",
    }
    assert expected <= cols
