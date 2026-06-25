from fastapi import APIRouter, Depends, Query
from agentsave_dashboard.auth import require_auth
from agentsave_dashboard.db import get_db
from agentsave_dashboard.services.aggregator import get_metrics, get_token_buckets

router = APIRouter()


@router.get("/api/metrics")
async def metrics(_: str = Depends(require_auth)):
    async with get_db() as db:
        return await get_metrics(db)


@router.get("/api/tokens")
async def tokens(window: str = Query("30d"), _: str = Depends(require_auth)):
    days = int(window.replace("d", "")) if window.endswith("d") else 30
    async with get_db() as db:
        buckets = await get_token_buckets(db, days=days)
    return {"buckets": buckets, "window": window}
