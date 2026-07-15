"""Memory API — customer-scoped CRUD for long-term user memories.

All endpoints require authentication.  Users can only access their own memories.
Transaction commits are handled by the ``get_db`` dependency — endpoints must not
commit explicitly to avoid double-commit expiration issues.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.memory import (
    MemoryCreateRequest,
    MemoryListResponse,
    MemoryResponse,
    MemoryUpdateRequest,
)
from app.security.dependencies import require_role
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["memories"])


def _memory_to_response(m: Any) -> MemoryResponse:
    return MemoryResponse(
        id=str(m.id),
        memory_type=m.memory_type.value if m.memory_type else "",
        key=m.key,
        content=m.content,
        structured_data=m.structured_data,
        source=m.source,
        confidence=m.confidence,
        status=m.status.value if m.status else "",
        version=m.version or 1,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


@router.post("", status_code=201)
async def create_memory(
    req: MemoryCreateRequest,
    request: Request,
    current_user: dict = Depends(require_role("CUSTOMER")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MemoryResponse]:
    """Create a new memory for the current user.

    If ``key`` is provided and an ACTIVE memory with the same (type, key)
    already exists, the content is merged (updated in place) rather than
    creating a duplicate.
    """
    user_id = uuid.UUID(current_user["sub"])
    service = MemoryService(db)

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    memory = await service.create_memory(
        user_id=user_id,
        memory_type=req.memory_type,
        content=req.content,
        source=req.source,
        key=req.key,
        structured_data=req.structured_data,
        confidence=req.confidence,
        ip_address=ip,
        user_agent=ua,
    )
    # Commit handled by get_db dependency

    return APIResponse(
        success=True, code="OK", message="Memory created",
        data=_memory_to_response(memory),
    )


@router.get("")
async def list_memories(
    memory_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_role("CUSTOMER")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MemoryListResponse]:
    """List the current user's memories, with optional type/status filters."""
    user_id = uuid.UUID(current_user["sub"])
    service = MemoryService(db)

    items, total = await service.list_memories(
        user_id=user_id,
        memory_type=memory_type,
        status=status,
        page=page,
        page_size=page_size,
    )

    return APIResponse(
        success=True, code="OK",
        data=MemoryListResponse(
            items=[_memory_to_response(m) for m in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
        ),
    )


@router.get("/{memory_id}")
async def get_memory(
    memory_id: uuid.UUID,
    current_user: dict = Depends(require_role("CUSTOMER")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MemoryResponse]:
    """Get a single memory by ID."""
    user_id = uuid.UUID(current_user["sub"])
    service = MemoryService(db)

    memory = await service.get_memory(memory_id, user_id)

    return APIResponse(
        success=True, code="OK",
        data=_memory_to_response(memory),
    )


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: uuid.UUID,
    req: MemoryUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_role("CUSTOMER")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MemoryResponse]:
    """Update an existing memory.  Only the owner can update."""
    user_id = uuid.UUID(current_user["sub"])
    service = MemoryService(db)

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    memory = await service.update_memory(
        memory_id=memory_id,
        user_id=user_id,
        content=req.content,
        structured_data=req.structured_data,
        confidence=req.confidence,
        status=req.status,
        ip_address=ip,
        user_agent=ua,
    )
    # Commit handled by get_db dependency

    return APIResponse(
        success=True, code="OK", message="Memory updated",
        data=_memory_to_response(memory),
    )


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: uuid.UUID,
    request: Request,
    current_user: dict = Depends(require_role("CUSTOMER")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    """Delete a memory.  Only the owner can delete."""
    user_id = uuid.UUID(current_user["sub"])
    service = MemoryService(db)

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    await service.delete_memory(
        memory_id=memory_id,
        user_id=user_id,
        ip_address=ip,
        user_agent=ua,
    )
    # Commit handled by get_db dependency

    return APIResponse(
        success=True, code="OK", message="Memory deleted", data=None,
    )
