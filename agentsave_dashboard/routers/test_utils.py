from fastapi import APIRouter
from agentsave_dashboard.db import get_db, init_db

router = APIRouter()


@router.delete("/api/test/reset")
async def reset():
    async with get_db() as db:
        await db.execute("DELETE FROM runs")
        await db.execute("DELETE FROM api_keys")
        await db.execute("DELETE FROM config")
        await db.commit()
    return {"status": "reset"}
