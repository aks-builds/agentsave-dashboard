import os
import tempfile
import aiosqlite
from agentsave_dashboard.db import init_db, DB_PATH


async def test_init_db_creates_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        await init_db(path)
        async with aiosqlite.connect(path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in await cursor.fetchall()}
        assert "runs" in tables
        assert "api_keys" in tables
        assert "config" in tables
    finally:
        os.unlink(path)


async def test_runs_table_schema():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        await init_db(path)
        async with aiosqlite.connect(path) as db:
            cursor = await db.execute("PRAGMA table_info(runs)")
            cols = {row[1] for row in await cursor.fetchall()}
        assert cols == {"run_id", "framework", "model_name", "tokens_before",
                        "tokens_after", "task_success", "timestamp"}
    finally:
        os.unlink(path)


def test_db_path_is_in_home():
    assert ".agentsave-dashboard" in DB_PATH
