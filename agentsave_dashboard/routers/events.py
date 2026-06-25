from fastapi import APIRouter, Depends
from pydantic import BaseModel
from agentsave_dashboard.auth import require_auth
from agentsave_dashboard.db import get_db

router = APIRouter()


class SavingsEvent(BaseModel):
    run_id: str
    framework: str
    model_name: str
    tokens_before: int
    tokens_after: int
    iterations_total: int
    iterations_saved: int
    task_success: bool
    timestamp: str


@router.post("/api/events")
async def post_event(event: SavingsEvent, _: str = Depends(require_auth)):
    async with get_db() as db:
        await db.execute(
            """INSERT OR IGNORE INTO runs
               (run_id, framework, model_name, tokens_before, tokens_after, task_success, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event.run_id, event.framework, event.model_name,
             event.tokens_before, event.tokens_after,
             1 if event.task_success else 0, event.timestamp),
        )
        await db.commit()
    return {"status": "ok"}
