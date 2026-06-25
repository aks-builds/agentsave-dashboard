async def get_metrics(db) -> dict:
    cursor = await db.execute("""
        SELECT
            framework,
            COUNT(*) as fw_count,
            SUM(tokens_before - tokens_after) as fw_saved,
            SUM(task_success) as success_count
        FROM runs
        GROUP BY framework
    """)
    rows = await cursor.fetchall()

    total_runs = 0
    total_saved = 0
    total_success = 0
    by_framework = {}

    for row in rows:
        total_runs += row["fw_count"]
        saved = row["fw_saved"] or 0
        total_saved += saved
        total_success += row["success_count"] or 0
        by_framework[row["framework"]] = {
            "runs": row["fw_count"],
            "tokens_saved": saved,
        }

    total_tokens_cursor = await db.execute("SELECT SUM(tokens_before) FROM runs")
    total_tokens_row = await total_tokens_cursor.fetchone()
    total_tokens_before = total_tokens_row[0] or 0

    reduction_pct = (
        round(total_saved / total_tokens_before * 100, 1)
        if total_tokens_before > 0 else 0.0
    )

    return {
        "total_tokens_saved": total_saved,
        "total_tokens_before": total_tokens_before,
        "reduction_pct": reduction_pct,
        "total_cost_saved_usd": round(total_saved * 0.000003, 4),
        "success_rate": round(total_success / total_runs * 100, 1) if total_runs > 0 else 0.0,
        "total_runs": total_runs,
        "by_framework": by_framework,
    }


async def get_token_buckets(db, days: int = 30) -> list[dict]:
    cursor = await db.execute("""
        SELECT
            DATE(timestamp) as date,
            SUM(tokens_before) as tokens_before,
            SUM(tokens_after) as tokens_after
        FROM runs
        WHERE timestamp >= DATE('now', ?)
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
    """, (f"-{days} days",))
    rows = await cursor.fetchall()
    return [
        {"date": row["date"], "tokens_before": row["tokens_before"], "tokens_after": row["tokens_after"]}
        for row in rows
    ]
