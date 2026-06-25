import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport

from agentsave_dashboard.database import init_db, get_db
from agentsave_dashboard.main import create_app


@pytest_asyncio.fixture
async def db():
    """In-memory aiosqlite connection with schema applied."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await init_db(conn)
        yield conn


@pytest_asyncio.fixture
async def client(db):
    """ASGI test client with DB dependency overridden to use in-memory DB."""
    app = create_app()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
