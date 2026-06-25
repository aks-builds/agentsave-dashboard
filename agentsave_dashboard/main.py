from __future__ import annotations

from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI

from agentsave_dashboard.config import get_settings
from agentsave_dashboard.database import init_db
from agentsave_dashboard.routers import events, metrics, tokens, billing


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        await init_db(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AgentSave Dashboard API", version="0.1.0", lifespan=lifespan)
    app.include_router(events.router)
    app.include_router(metrics.router)
    app.include_router(tokens.router)
    app.include_router(billing.router)
    return app


app = create_app()
