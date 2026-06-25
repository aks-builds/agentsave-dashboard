import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from agentsave_dashboard import __version__
from agentsave_dashboard.db import init_db
from agentsave_dashboard.routers import health, events, runs, metrics, billing


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AgentSave Dashboard", version=__version__, lifespan=lifespan)
    for router in [health.router, events.router, runs.router, metrics.router, billing.router]:
        app.include_router(router)
    if os.environ.get("AGENTSAVE_TEST_MODE") == "1":
        from agentsave_dashboard.routers import test_utils
        app.include_router(test_utils.router)
    return app
