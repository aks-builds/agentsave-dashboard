import os
import pytest

os.environ["AGENTSAVE_TEST_MODE"] = "1"

from httpx import AsyncClient, ASGITransport
import agentsave_dashboard.db as _db_module
from agentsave_dashboard.main import create_app


@pytest.fixture(autouse=True)
def fresh_test_db(tmp_path):
    """Give every test its own temp DB file so connections share state."""
    db_path = str(tmp_path / "test.db")
    _db_module._db_path_override = db_path
    yield db_path
    _db_module._db_path_override = None


@pytest.fixture
async def client(fresh_test_db):
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
