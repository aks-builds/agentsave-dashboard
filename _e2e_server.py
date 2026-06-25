"""E2E test server — file-based DB + test_utils router mounted via AGENTSAVE_TEST_MODE=1."""
import os, sys
sys.path.insert(0, '.')

os.environ["AGENTSAVE_TEST_MODE"] = "1"

# Use a fixed E2E DB path — must match _e2e_setup.py
E2E_DB = os.path.join(os.environ.get("TEMP", "/tmp"), "agentsave-e2e.db")

import agentsave_dashboard.db as dbmod
dbmod._db_path_override = E2E_DB

print(f"Using DB: {E2E_DB}", flush=True)

from agentsave_dashboard.main import create_app
import uvicorn

uvicorn.run(create_app(), host="127.0.0.1", port=8000)
