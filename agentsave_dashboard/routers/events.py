from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agentsave_dashboard.auth import require_jwt, verify_api_token
from agentsave_dashboard.database import get_db
from agentsave_dashboard.models import EventPayload

router = APIRouter()
_BEARER = HTTPBearer()


@router.post("/api/events", status_code=201)
async def receive_event(
    payload: EventPayload,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_BEARER)],
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> dict:
    project_id = await verify_api_token(credentials.credentials, db)

    event_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO events
            (id, project_id, run_id, framework, model_name,
             tokens_before, tokens_after, iterations_total,
             iterations_saved, task_success, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            project_id,
            payload.run_id,
            payload.framework,
            payload.model_name,
            payload.tokens_before,
            payload.tokens_after,
            payload.iterations_total,
            payload.iterations_saved,
            1 if payload.task_success else 0,
            payload.timestamp,
        ),
    )
    await db.commit()
    return {"status": "ok", "event_id": event_id}


@router.get("/api/events/recent")
async def get_recent_events(
    project_id: str,
    limit: int = 10,
    payload: dict = Depends(require_jwt),
    db: aiosqlite.Connection = Depends(get_db),
) -> list[dict]:
    cursor = await db.execute(
        "SELECT id, run_id, framework, model_name, tokens_before, tokens_after, "
        "iterations_total, iterations_saved, task_success, timestamp "
        "FROM events WHERE project_id = ? ORDER BY timestamp DESC LIMIT ?",
        (project_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
