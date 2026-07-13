"""Admin API — config management."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.common import APIResponse
from app.security.dependencies import require_role
from app.services.system_config import SystemConfigService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/config")
async def list_config(
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[list]:
    service = SystemConfigService(db)
    configs = await service.get_all()
    return APIResponse(success=True, code="OK", data=configs)
