"""Health check endpoint."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.common import APIResponse

router = APIRouter(tags=["health"])

# Module-level singleton for FastAPI dependency
_GetDB = Depends(get_db)


@router.get("/health", response_model=APIResponse[dict[str, Any]])
async def health_check(db: AsyncSession = _GetDB) -> APIResponse[dict[str, Any]]:
    """Check application and database health.

    Returns the application status and database connectivity.
    """
    db_status = "disconnected"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return APIResponse(
        success=True,
        code="OK",
        message="Service is healthy",
        data={
            "status": "healthy",
            "database": db_status,
            "version": "1.0.1",
        },
    )
