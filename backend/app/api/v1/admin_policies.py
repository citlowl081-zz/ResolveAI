"""Admin policy management API — CRUD, status transitions, and ingestion."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.database.session import get_db
from app.exceptions import ConflictError, NotFoundError
from app.rag.embeddings import build_embedding_provider
from app.rag.ingestion import PolicyIngestionService
from app.schemas.admin_policy import (
    PolicyCreateRequest,
    PolicyIngestRequest,
    PolicyStatusRequest,
    PolicyUpdateRequest,
)
from app.schemas.common import APIResponse
from app.security.dependencies import require_role
from app.services.policy_service import PolicyService

router = APIRouter(prefix="/admin/policies", tags=["admin-policies"])

# Resolve project root from this file's location
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_POLICIES_DIR = _PROJECT_ROOT / "data" / "policies"


def _get_service(db: AsyncSession) -> PolicyService:
    """Build PolicyService using a new engine from settings (short-lived)."""
    from sqlalchemy.ext.asyncio import create_async_engine as _create

    eng = _create(
        settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
    )
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]
    provider = build_embedding_provider()
    return PolicyService(session_factory=factory, embedding_provider=provider)


def _user_id(user: dict) -> uuid.UUID | None:
    sub = user.get("sub")
    return uuid.UUID(sub) if sub else None


# ── CRUD ──────────────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_policy(
    req: PolicyCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    svc = _get_service(db)
    result = await svc.create_policy(
        policy_key=req.policy_key,
        title=req.title,
        category=req.category,
        content=req.content,
        effective_date=req.effective_date,
        issue_types=req.issue_types,
        content_summary=req.content_summary,
        expiration_date=req.expiration_date,
        source=req.source,
        metadata_filter=req.metadata_filter,
        status=req.status,
    )
    return APIResponse(success=True, code="CREATED", data=result)


@router.get("")
async def list_policies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    svc = _get_service(db)
    items, total = await svc.list_policies(page, page_size, category, status)
    return APIResponse(success=True, code="OK", data={
        "items": items, "total": total,
        "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    })


@router.get("/by-key/{policy_key}")
async def get_active(
    policy_key: str,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    svc = _get_service(db)
    try:
        result = await svc.get_active_or_raise(policy_key)
        return APIResponse(success=True, code="OK", data=result)
    except NotFoundError as exc:
        exc.code = "POLICY_ACTIVE_NOT_FOUND"
        raise


@router.get("/by-key/{policy_key}/versions")
async def list_versions(
    policy_key: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    svc = _get_service(db)
    items, total = await svc.list_versions(policy_key, page, page_size)
    return APIResponse(success=True, code="OK", data={
        "items": items, "total": total,
        "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    })


@router.put("/by-key/{policy_key}")
async def update_policy(
    policy_key: str,
    req: PolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    svc = _get_service(db)
    result = await svc.update_policy(
        policy_key=policy_key,
        title=req.title,
        category=req.category,
        content=req.content,
        effective_date=req.effective_date,
        issue_types=req.issue_types,
        content_summary=req.content_summary,
        expiration_date=req.expiration_date,
        source=req.source,
        metadata_filter=req.metadata_filter,
    )
    if result.get("status") == "unchanged":
        return APIResponse(success=True, code="OK", message="Content unchanged", data=result)
    return APIResponse(success=True, code="OK", data=result)


@router.patch("/by-key/{policy_key}/versions/{version}/status")
async def transition_status(
    policy_key: str,
    version: int,
    req: PolicyStatusRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    svc = _get_service(db)
    try:
        result = await svc.transition_status(policy_key, version, req.status)
        return APIResponse(success=True, code="OK", data=result)
    except (NotFoundError, ConflictError):
        raise


# ── Ingestion ─────────────────────────────────────────────────────────


@router.post("/ingest")
async def ingest_policies(
    req: PolicyIngestRequest = PolicyIngestRequest(),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    provider = build_embedding_provider()
    ingester = PolicyIngestionService(
        session_factory=factory,
        embedding_provider=provider,
        policies_dir=_POLICIES_DIR,
    )
    try:
        report = await ingester.ingest_all(activate=req.activate)
        return APIResponse(success=True, code="OK", data={"report": report})
    finally:
        await engine.dispose()
