from agentsave_dashboard.license import resolve_tier


async def run_retention(db) -> int:
    tier_info = await resolve_tier(db)
    history_days = tier_info.features["history_days"]
    cursor = await db.execute(
        "DELETE FROM runs WHERE timestamp < DATETIME('now', ?)",
        (f"-{history_days} days",),
    )
    await db.commit()
    return cursor.rowcount
