from fastapi import APIRouter
from agentsave_dashboard.db import get_db, init_db

router = APIRouter()


@router.delete("/api/test/reset")
async def reset():
    """Clear runs and config only — api_keys are preserved so callers can still auth."""
    async with get_db() as db:
        await db.execute("DELETE FROM runs")
        await db.execute("DELETE FROM config")
        await db.commit()
    return {"status": "reset"}


@router.delete("/api/test/reset-all")
async def reset_all():
    """Hard reset: clears everything including api_keys. Use only when re-seeding."""
    async with get_db() as db:
        await db.execute("DELETE FROM runs")
        await db.execute("DELETE FROM api_keys")
        await db.execute("DELETE FROM config")
        await db.commit()
    return {"status": "reset-all"}
