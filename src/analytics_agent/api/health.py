from fastapi import APIRouter

from analytics_agent.api._common import ok

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return ok({"status": "ok"})
