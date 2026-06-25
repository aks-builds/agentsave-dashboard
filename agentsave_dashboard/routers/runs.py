from fastapi import APIRouter, Depends, Query
from agentsave_dashboard.auth import require_auth
from agentsave_dashboard.db import get_db

router = APIRouter()


@router.get("/api/runs")
async def get_runs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    _: str = Depends(require_auth),
):
    offset = (page - 1) * per_page
    async with get_db() as db:
        count_cursor = await db.execute("SELECT COUNT(*) FROM runs")
        total = (await count_cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        )
        rows = await cursor.fetchall()

    runs = []
    for row in rows:
        tb = row["tokens_before"]
        ta = row["tokens_after"]
        reduction_pct = round((tb - ta) / tb * 100, 1) if tb > 0 else 0.0
        runs.append({
            "run_id": row["run_id"],
            "framework": row["framework"],
            "model_name": row["model_name"],
            "tokens_before": tb,
            "tokens_after": ta,
            "reduction_pct": reduction_pct,
            "task_success": bool(row["task_success"]),
            "timestamp": row["timestamp"],
        })
    return {"runs": runs, "total": total, "page": page, "per_page": per_page}
