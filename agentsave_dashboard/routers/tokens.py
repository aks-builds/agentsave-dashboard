from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, status

from agentsave_dashboard.auth import generate_api_token, require_jwt
from agentsave_dashboard.database import get_db
from agentsave_dashboard.models import TokenCreateRequest, TokenResponse

router = APIRouter()


@router.post("/api/tokens", status_code=201)
async def create_token(
    body: TokenCreateRequest,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    jwt_payload: Annotated[dict, Depends(require_jwt)],
) -> dict:
    user_id = jwt_payload["sub"]
    raw_token, token_hash = generate_api_token()
    token_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """
        INSERT INTO api_tokens
            (id, user_id, project_id, token_hash, name, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (token_id, user_id, body.project_id, token_hash, body.name, now),
    )
    await db.commit()
    return {"token": raw_token, "id": token_id}


@router.get("/api/tokens", response_model=list[TokenResponse])
async def list_tokens(
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    jwt_payload: Annotated[dict, Depends(require_jwt)],
) -> list[TokenResponse]:
    user_id = jwt_payload["sub"]
    cursor = await db.execute(
        """
        SELECT id, name, project_id, created_at, last_used_at
        FROM api_tokens
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [
        TokenResponse(
            id=row["id"],
            name=row["name"],
            project_id=row["project_id"],
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
        )
        for row in rows
    ]
