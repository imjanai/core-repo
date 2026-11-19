"""apps/api/routers/health.py — liveness- en readiness-endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.database import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    db: str


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    """
    Readiness-check: controleert of de API en de database bereikbaar zijn.
    Gebruikt door Docker Compose healthcheck en load-balancer probes.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        db=db_status,
    )
