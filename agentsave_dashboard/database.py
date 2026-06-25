from __future__ import annotations

import aiosqlite
from collections.abc import AsyncGenerator

from agentsave_dashboard.config import get_settings

_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT,
    tier            TEXT NOT NULL DEFAULT 'free',
    created_at      TEXT NOT NULL
)
"""

_CREATE_PROJECTS = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL
)
"""

_CREATE_API_TOKENS = """
CREATE TABLE IF NOT EXISTS api_tokens (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id  TEXT REFERENCES projects(id) ON DELETE CASCADE,
    token_hash  TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    last_used_at TEXT
)
"""

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id               TEXT PRIMARY KEY,
    project_id       TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    run_id           TEXT NOT NULL,
    framework        TEXT NOT NULL,
    model_name       TEXT NOT NULL,
    tokens_before    INTEGER NOT NULL,
    tokens_after     INTEGER NOT NULL,
    iterations_total INTEGER NOT NULL,
    iterations_saved INTEGER NOT NULL DEFAULT 0,
    task_success     INTEGER NOT NULL DEFAULT 1,
    timestamp        TEXT NOT NULL
)
"""

_CREATE_METRICS_CACHE = """
CREATE TABLE IF NOT EXISTS metrics_cache (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    period          TEXT NOT NULL,
    tokens_saved    INTEGER NOT NULL DEFAULT 0,
    cost_saved_usd  REAL NOT NULL DEFAULT 0.0,
    success_rate    REAL NOT NULL DEFAULT 0.0,
    computed_at     TEXT NOT NULL,
    UNIQUE(project_id, period)
)
"""

_ALL_DDLS = [
    _CREATE_USERS,
    _CREATE_PROJECTS,
    _CREATE_API_TOKENS,
    _CREATE_EVENTS,
    _CREATE_METRICS_CACHE,
]


async def init_db(db: aiosqlite.Connection) -> None:
    """Create all tables. Safe to call multiple times (IF NOT EXISTS)."""
    await db.execute("PRAGMA foreign_keys = ON")
    for ddl in _ALL_DDLS:
        await db.execute(ddl)
    await db.commit()


async def get_db(db_url: str | None = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """FastAPI dependency: yields an open aiosqlite connection."""
    url = db_url or get_settings().database_url
    async with aiosqlite.connect(url) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db
