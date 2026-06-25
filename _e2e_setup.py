"""Setup RSA keys and seed E2E test database."""
import os, sys, asyncio, hashlib, secrets, json
from datetime import datetime, timezone, timedelta
import random

# Ensure keys exist
os.makedirs("agentsave_dashboard/keys", exist_ok=True)
os.makedirs("scripts", exist_ok=True)

if not os.path.exists("agentsave_dashboard/keys/public.pem"):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    pk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    open("agentsave_dashboard/keys/public.pem", "w").write(
        pk.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    )
    open("scripts/private.pem", "w").write(
        pk.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()).decode()
    )
    print("Keys generated")
else:
    print("Keys already exist")

# Seed the E2E database
import tempfile as _tempfile
db_path = os.environ.get("E2E_DB_PATH", os.path.join(_tempfile.gettempdir(), "agentsave-e2e.db"))

async def seed():
    import agentsave_dashboard.db as dbmod
    dbmod._db_path_override = db_path

    from agentsave_dashboard.db import init_db, get_db
    await init_db()

    raw_key = "ask-e2e-" + secrets.token_hex(8)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    FRAMEWORKS = ["langchain", "autogen", "crewai", "smolagents", "langgraph"]
    MODELS = ["gpt-4o", "claude-sonnet-4-6", "gemini-2.5-pro", "gpt-4o-mini"]

    async with get_db() as db:
        # Seed API key
        await db.execute(
            "INSERT OR REPLACE INTO api_keys (key_hash, label, created_at) VALUES (?,?,?)",
            (key_hash, "e2e-test", datetime.now(timezone.utc).isoformat())
        )
        # Seed 30 realistic runs spread over 30 days
        total_saved = 0
        for i in range(30):
            tokens_before = random.randint(800, 4000)
            reduction = random.uniform(0.18, 0.42)
            tokens_after = int(tokens_before * (1 - reduction))
            ts = (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 29), hours=random.randint(0,23))).isoformat()
            await db.execute(
                "INSERT OR IGNORE INTO runs VALUES (?,?,?,?,?,?,?)",
                (
                    f"e2e-run-{i:04d}",
                    FRAMEWORKS[i % len(FRAMEWORKS)],
                    MODELS[i % len(MODELS)],
                    tokens_before,
                    tokens_after,
                    1 if random.random() > 0.07 else 0,
                    ts,
                )
            )
            total_saved += tokens_before - tokens_after
        await db.commit()

    print(f"Seeded 30 runs, {total_saved:,} tokens saved, API key: {raw_key}")
    print(f"DB: {db_path}")
    # Write key for the test runner to consume
    with open(os.path.join(os.path.dirname(db_path), "e2e-api-key.txt"), "w") as f:
        f.write(raw_key)

asyncio.run(seed())
