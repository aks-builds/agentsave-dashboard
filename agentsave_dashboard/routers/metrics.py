from __future__ import annotations

from typing import Annotated, Literal

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, status

from agentsave_dashboard.auth import require_jwt
from agentsave_dashboard.config import get_settings
from agentsave_dashboard.database import get_db
from agentsave_dashboard.models import MetricsResponse
from agentsave_dashboard.services.metrics_service import compute_metrics

router = APIRouter()

_VALID_PERIODS = {"7d", "30d", "90d"}


@router.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(
    project_id: str,
    period: str = Query(..., pattern="^(7d|30d|90d)$"),
    db: Annotated[aiosqlite.Connection, Depends(get_db)] = None,
    _jwt: Annotated[dict, Depends(require_jwt)] = None,
) -> MetricsResponse:
    settings = get_settings()
    return await compute_metrics(project_id, period, db, settings.cost_per_token_usd)
