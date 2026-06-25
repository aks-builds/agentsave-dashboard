import os
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncIterator

DB_DIR = os.path.expanduser("~/.agentsave-dashboard")
DB_PATH = os.path.join(DB_DIR, "data.db")

_db_path_override: str | None = None


def get_db_path() -> str:
    # Override wins first (set by test fixtures for isolation)
    if _db_path_override:
        return _db_path_override
    if os.environ.get("AGENTSAVE_TEST_MODE") == "1":
        return ":memory:"
    return DB_PATH


async def init_db(db_path: str | None = None) -> None:
    path = db_path or get_db_path()
    if path != ":memory:":
        os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id        TEXT PRIMARY KEY,
                framework     TEXT NOT NULL,
                model_name    TEXT NOT NULL,
                tokens_before INTEGER NOT NULL,
                tokens_after  INTEGER NOT NULL,
                task_success  INTEGER NOT NULL,
                timestamp     TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_hash   TEXT PRIMARY KEY,
                label      TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    path = get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        yield db
