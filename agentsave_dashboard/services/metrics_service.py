from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import aiosqlite

from agentsave_dashboard.models import MetricsResponse

Period = Literal["7d", "30d", "90d"]

_PERIOD_DAYS: dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}


async def compute_metrics(
    project_id: str,
    period: str,
    db: aiosqlite.Connection,
    cost_per_token: float,
) -> MetricsResponse:
    """Aggregate events for a project over the given period and return metrics."""
    days = _PERIOD_DAYS[period]  # KeyError propagates as 422 via router validation
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    cursor = await db.execute(
        """
        SELECT
            COUNT(*) AS event_count,
            COALESCE(SUM(tokens_before - tokens_after), 0) AS tokens_saved,
            COALESCE(AVG(task_success), 0.0) AS success_rate
        FROM events
        WHERE project_id = ? AND timestamp >= ?
        """,
        (project_id, since),
    )
    row = await cursor.fetchone()
    tokens_saved = int(row["tokens_saved"])
    cost_saved = tokens_saved * cost_per_token
    success_rate = float(row["success_rate"])
    event_count = int(row["event_count"])

    # Upsert into metrics_cache
    cache_id = str(uuid.uuid4())
    computed_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT INTO metrics_cache (id, project_id, period, tokens_saved,
            cost_saved_usd, success_rate, computed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, period) DO UPDATE SET
            tokens_saved = excluded.tokens_saved,
            cost_saved_usd = excluded.cost_saved_usd,
            success_rate = excluded.success_rate,
            computed_at = excluded.computed_at
        """,
        (cache_id, project_id, period, tokens_saved, cost_saved, success_rate, computed_at),
    )
    await db.commit()

    return MetricsResponse(
        project_id=project_id,
        period=period,
        tokens_saved=tokens_saved,
        cost_saved_usd=cost_saved,
        success_rate=success_rate,
        event_count=event_count,
    )
