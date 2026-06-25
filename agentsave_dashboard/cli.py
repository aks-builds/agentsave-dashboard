import asyncio
import os
from datetime import datetime, timezone

import click
import uvicorn
from rich.console import Console

console = Console()


@click.group()
def cli():
    """AgentSave Dashboard — self-hosted backend."""
    pass


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--license-key", default=None, help="JWT license key to activate Pro/Enterprise tier")
def serve(host: str, port: int, license_key: str | None):
    """Start the AgentSave Dashboard server."""
    from agentsave_dashboard.db import DB_DIR, DB_PATH, get_db_path, init_db
    from agentsave_dashboard.auth import generate_api_key

    if os.environ.get("AGENTSAVE_TEST_MODE") != "1":
        os.makedirs(DB_DIR, exist_ok=True)

    async def _setup():
        await init_db()
        import aiosqlite
        async with aiosqlite.connect(get_db_path()) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM api_keys")
            count = (await cursor.fetchone())[0]
            if count == 0:
                raw, hashed = generate_api_key()
                now = datetime.now(timezone.utc).isoformat()
                await db.execute(
                    "INSERT INTO api_keys (key_hash, label, created_at) VALUES (?, ?, ?)",
                    (hashed, "default", now),
                )
                await db.commit()
                console.print("\n[bold cyan]AgentSave Dashboard[/bold cyan]")
                console.print(f"API key: [bold yellow]{raw}[/bold yellow]  <- save this, shown once")
                console.print("[bold]agentsave login[/bold] and enter this key\n")
            if license_key:
                await db.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES ('license_key', ?)",
                    (license_key,),
                )
                await db.commit()
                console.print("[green]✓ License key applied.[/green]")

    asyncio.run(_setup())
    console.print(f"[bold green]Running at http://{host}:{port}[/bold green]")
    from agentsave_dashboard.main import create_app
    uvicorn.run(create_app(), host=host, port=port)
