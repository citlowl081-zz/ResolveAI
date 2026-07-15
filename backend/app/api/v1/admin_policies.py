"""Admin policy management API — CRUD, status transitions, and ingestion."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
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
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
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


# ── Upload (Phase 04C) ─────────────────────────────────────────────────


_ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx"})
_ALLOWED_MIME = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
})
_MAX_UPLOAD_MB = 10


@router.post("/upload", status_code=201)
async def upload_policy(
    file: UploadFile = File(...),
    policy_key: str = Form(...),
    title: str = Form(...),
    category: str = Form(...),
    effective_date: str = Form(...),
    activate: bool = Form(False),
    issue_types: str = Form(""),
    content_summary: str = Form(""),
    expiration_date: str = Form(""),
    source: str = Form(""),
    metadata_filter: str = Form("{}"),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    import json
    from pathlib import Path as P

    from app.rag.document_parser import DocumentParseError, parse_upload

    # ── Validate extension ──────────────────────────────────────────
    filename = file.filename or "unknown"
    suffix = P(filename).suffix.lower()
    name_only = P(filename).name
    if ".." in name_only or "/" in name_only or "\\" in name_only:
        return APIResponse(success=False, code="INVALID_FILENAME",
                          message="文件名包含非法字符")
    if suffix not in _ALLOWED_EXTENSIONS:
        return APIResponse(success=False, code="UNSUPPORTED_FORMAT",
                          message=f"不支持的文件格式 {suffix}，仅支持 PDF 和 DOCX")

    # ── Validate size ───────────────────────────────────────────────
    content = await file.read()
    if len(content) == 0:
        return APIResponse(success=False, code="EMPTY_FILE", message="上传的文件为空")
    if len(content) > _MAX_UPLOAD_MB * 1024 * 1024:
        return APIResponse(success=False, code="FILE_TOO_LARGE",
                          message=f"文件超过最大限制 {_MAX_UPLOAD_MB}MB")

    # ── Parse document ──────────────────────────────────────────────
    try:
        body_text = parse_upload(content, filename)
    except DocumentParseError as exc:
        return APIResponse(success=False, code="PARSE_ERROR", message=str(exc))

    if not body_text.strip():
        return APIResponse(success=False, code="EMPTY_BODY",
                          message="文件中未提取到文本内容")

    # ── Ingest via existing pipeline ────────────────────────────────
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    provider = build_embedding_provider()

    try:
        issue_list = json.loads(issue_types) if issue_types else []
    except json.JSONDecodeError:
        issue_list = []
    try:
        meta_filter = json.loads(metadata_filter) if metadata_filter else {}
    except json.JSONDecodeError:
        meta_filter = {}

    svc = PolicyService(session_factory=factory, embedding_provider=provider)
    try:
        result = await svc.create_policy(
            policy_key=policy_key, title=title, category=category,
            content=body_text, effective_date=effective_date,  # type: ignore[arg-type]
            issue_types=issue_list, content_summary=content_summary,
            expiration_date=expiration_date or None,  # type: ignore[arg-type]
            source=source, metadata_filter=meta_filter,
            status="ACTIVE" if activate else "DRAFT",
        )
        return APIResponse(success=True, code="CREATED", data=result)
    except Exception as exc:
        return APIResponse(success=False, code="INGEST_FAILED",
                          message=f"入库失败: {exc}")
    finally:
        await engine.dispose()
