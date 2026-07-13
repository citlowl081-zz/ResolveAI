"""Auth API endpoints — register, login, refresh, me."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from app.schemas.common import APIResponse
from app.security.dependencies import get_current_user
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> APIResponse[dict]:
    service = AuthService(db)
    user = await service.register(req.email, req.password, req.full_name)
    return APIResponse(success=True, code="OK", message="Registration successful", data=user)


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> APIResponse[dict]:
    service = AuthService(db)
    result = await service.login(req.email, req.password)
    return APIResponse(success=True, code="OK", message="Login successful", data=result)


@router.post("/refresh")
async def refresh(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = AuthService(db)
    result = await service.refresh(req.refresh_token)
    return APIResponse(success=True, code="OK", message="Token refreshed", data=result)


@router.get("/me")
async def me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> APIResponse[dict]:
    service = AuthService(db)
    user = await service.get_me(uuid.UUID(current_user["sub"]))
    return APIResponse(success=True, code="OK", data=user)
