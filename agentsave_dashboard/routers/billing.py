from fastapi import APIRouter, Depends
from agentsave_dashboard.auth import require_auth
from agentsave_dashboard.db import get_db
from agentsave_dashboard.license import resolve_tier

router = APIRouter()


@router.get("/api/billing")
async def billing(_: str = Depends(require_auth)):
    async with get_db() as db:
        info = await resolve_tier(db)
        seats_cursor = await db.execute("SELECT COUNT(*) FROM api_keys")
        seats_used = (await seats_cursor.fetchone())[0]

    return {
        "tier": info.tier,
        "org": info.org,
        "seats_allowed": info.seats_allowed,
        "seats_used": seats_used,
        "expires_at": info.expires_at,
        "expired": info.expired,
        "features": info.features,
    }
