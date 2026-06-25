from fastapi import APIRouter
from agentsave_dashboard import __version__

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"status": "ok", "version": __version__}
