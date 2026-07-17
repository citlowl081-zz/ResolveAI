"""PolicyService — retrieval (Batch 3) + lifecycle management (Batch 4)."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.exceptions import ConflictError, NotFoundError
from app.models.enums import PolicyStatus
from app.models.policy_chunk import PolicyChunk
from app.models.policy_document import PolicyDocument
from app.rag.chunking import chunk_text
from app.rag.content_hash import compute_content_hash
from app.rag.embeddings import EmbeddingProvider
from app.rag.validation import validate_policy_key_and_category
from app.repositories.policy_chunk import PolicyChunkRepository
from app.repositories.policy_document import PolicyDocumentRepository
from app.services.audit import AuditService


def _expand_policy_query(query: str) -> str:
    """Add policy vocabulary for common customer synonyms before embedding."""
    hints: list[str] = []
    if any(term in query for term in ("少发", "少件", "漏件", "错发")):
        hints.append("少件 漏件 错发 补发")
    if any(term in query for term in ("耳机", "耳麦")):
        hints.append("耳机 数码产品 拆封 合理试用 商品完好 七日无理由")
    if any(term in query for term in ("衣服", "衣物", "试穿")):
        hints.append("服装 试穿 合理试用 商品完好 退货")
    return f"{query} {' '.join(hints)}".strip()


class PolicyService:
    """Service for policy retrieval and lifecycle management."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._session_factory = session_factory
        self._embedding = embedding_provider

    # ── Retrieval (Batch 3) ──────────────────────────────────────────

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_similarity: float | None = None,
    ) -> list[dict]:
        if self._embedding.dimension != 1536:
            raise RuntimeError("Embedding dimension mismatch")
        query_vector = await self._embedding.embed_query(_expand_policy_query(query))
        async with self._session_factory() as session:
            repo = PolicyChunkRepository(session)
            return await repo.search_similar(
                query_vector=query_vector,
                top_k=top_k,
                category=category,
                min_similarity=min_similarity,
            )

    # ── Write: Create ────────────────────────────────────────────────

    async def create_policy(
        self,
        policy_key: str,
        title: str,
        category: str,
        content: str,
        effective_date: date,
        issue_types: list[str] | None = None,
        content_summary: str = "",
        expiration_date: date | None = None,
        source: str = "",
        metadata_filter: dict | None = None,
        status: str = "DRAFT",
    ) -> dict:
        validate_policy_key_and_category(policy_key, category)
        if status not in ("DRAFT", "ACTIVE"):
            raise ValueError("status must be DRAFT or ACTIVE")

        doc_data = {
            "title": title, "category": category, "content": content,
            "issue_types": issue_types or [],
            "content_summary": content_summary or " ".join(content.split())[:200],
            "effective_date": effective_date, "expiration_date": expiration_date,
            "source": source, "metadata_filter": metadata_filter or {},
        }
        content_hash = compute_content_hash(doc_data)

        chunks = chunk_text(content)
        if not chunks:
            raise ValueError("Content produced no chunks")
        vectors = await self._embedding.embed(chunks)

        async with self._session_factory() as session, session.begin():
            repo = PolicyDocumentRepository(session)
            latest = await repo.get_latest(policy_key)
            new_version = (latest.version if latest else 0) + 1

            doc = PolicyDocument(
                policy_key=policy_key, version=new_version,
                title=title, category=category,
                issue_types=issue_types or [],
                content=content, content_summary=content_summary,
                content_hash=content_hash,
                metadata_filter=metadata_filter or {},
                effective_date=effective_date,
                expiration_date=expiration_date,
                status=status, source=source,
            )
            session.add(doc)
            await session.flush()

            for i, (c, v) in enumerate(zip(chunks, vectors, strict=True)):
                session.add(PolicyChunk(
                    policy_document_id=doc.id, chunk_index=i,
                    content=c, embedding=v, char_count=len(c),
                ))

            if status == "ACTIVE":
                active = await repo.get_active(policy_key)
                if active is not None and active.id != doc.id:
                    active.status = PolicyStatus.SUPERSEDED
                    active.superseded_by = doc.id

            audit = AuditService(session)
            await audit.log(
                user_id=None, action="CREATE",
                resource_type="POLICY", resource_id=doc.id,
                changes={"policy_key": policy_key, "version": new_version, "status": status},
            )

            return _doc_to_public(doc)

    # ── Write: Update (creates new DRAFT) ────────────────────────────

    async def update_policy(
        self, policy_key: str, **fields: object,
    ) -> dict:
        title = str(fields["title"])
        category = str(fields["category"])
        content = str(fields["content"])
        effective_date_obj = fields["effective_date"]
        if isinstance(effective_date_obj, str):
            effective_date_obj = date.fromisoformat(effective_date_obj)

        validate_policy_key_and_category(policy_key, category)

        doc_data = {
            "title": title, "category": category, "content": content,
            "issue_types": fields.get("issue_types", []),
            "content_summary": str(fields.get("content_summary", "")),
            "effective_date": effective_date_obj,
            "expiration_date": fields.get("expiration_date"),
            "source": str(fields.get("source", "")),
            "metadata_filter": fields.get("metadata_filter", {}),
        }
        content_hash = compute_content_hash(doc_data)

        chunks = chunk_text(content)
        if not chunks:
            raise ValueError("Content produced no chunks")
        vectors = await self._embedding.embed(chunks)

        async with self._session_factory() as session, session.begin():
            repo = PolicyDocumentRepository(session)
            latest = await repo.get_latest(policy_key)

            if latest is not None and latest.content_hash == content_hash:
                return {"policy_key": policy_key, "status": "unchanged"}

            new_version = (latest.version if latest else 0) + 1

            doc = PolicyDocument(
                policy_key=policy_key, version=new_version,
                title=title, category=category,
                issue_types=_cast_to_str_list(fields.get("issue_types")),
                content=content,
                content_summary=str(fields.get("content_summary", "")),
                content_hash=content_hash,
                metadata_filter=fields.get("metadata_filter", {}) or {},
                effective_date=effective_date_obj,
                expiration_date=fields.get("expiration_date"),
                status="DRAFT", source=str(fields.get("source", "")),
            )
            session.add(doc)
            await session.flush()

            for i, (c, v) in enumerate(zip(chunks, vectors, strict=True)):
                session.add(PolicyChunk(
                    policy_document_id=doc.id, chunk_index=i,
                    content=c, embedding=v, char_count=len(c),
                ))

            audit = AuditService(session)
            await audit.log(
                user_id=None, action="UPDATE",
                resource_type="POLICY", resource_id=doc.id,
                changes={"policy_key": policy_key, "version": new_version},
            )

            return _doc_to_public(doc)

    # ── Status transitions ───────────────────────────────────────────

    async def transition_status(
        self, policy_key: str, version: int, new_status: str,
    ) -> dict:
        if new_status not in ("ACTIVE", "ARCHIVED"):
            raise ValueError("status must be ACTIVE or ARCHIVED")

        async with self._session_factory() as session, session.begin():
            repo = PolicyDocumentRepository(session)
            doc = await repo.get_by_key_and_version(policy_key, version)
            if doc is None:
                raise NotFoundError(
                    f"Policy {policy_key} version {version} not found"
                )

            current = doc.status

            # Validate transition
            if current == "DRAFT" and new_status in ("ACTIVE", "ARCHIVED") or current == "ACTIVE" and new_status == "ARCHIVED":
                pass  # valid
            elif current in ("SUPERSEDED", "ARCHIVED"):
                raise ConflictError(
                    f"Cannot transition from terminal state '{current}'"
                )
            else:
                raise ConflictError(
                    f"Invalid transition: {current} → {new_status}"
                )

            if new_status == "ACTIVE":
                # Supersede old ACTIVE — flush before setting new ACTIVE
                # to avoid partial unique index violation
                active = await repo.get_active(policy_key)
                if active is not None and active.id != doc.id:
                    active.status = PolicyStatus.SUPERSEDED
                    active.superseded_by = doc.id
                    await session.flush()

            doc.status = PolicyStatus(new_status)

            audit = AuditService(session)
            await audit.log(
                user_id=None, action="STATUS_CHANGE",
                resource_type="POLICY", resource_id=doc.id,
                changes={
                    "policy_key": policy_key, "version": version,
                    "from": current, "to": new_status,
                },
            )

            return {
                "policy_key": doc.policy_key,
                "version": doc.version,
                "status": doc.status,
            }

    # ── Queries ──────────────────────────────────────────────────────

    async def get_active(self, policy_key: str) -> dict | None:
        async with self._session_factory() as session:
            repo = PolicyDocumentRepository(session)
            doc = await repo.get_active(policy_key)
            if doc is None:
                return None
            return _doc_to_dict(doc)

    async def get_active_or_raise(self, policy_key: str) -> dict:
        result = await self.get_active(policy_key)
        if result is None:
            exc = NotFoundError(
                f"No ACTIVE version found for policy '{policy_key}'",
            )
            exc.code = "POLICY_ACTIVE_NOT_FOUND"
            raise exc
        return result

    async def list_versions(
        self, policy_key: str, page: int = 1, page_size: int = 20,
    ) -> tuple[list[dict], int]:
        async with self._session_factory() as session:
            repo = PolicyDocumentRepository(session)
            rows, total = await repo.list_versions(policy_key, page, page_size)
            return ([_doc_to_dict(r) for r in rows], total)

    async def list_policies(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict], int]:
        async with self._session_factory() as session:
            repo = PolicyDocumentRepository(session)
            rows, total = await repo.list_all(page, page_size, category, status)
            return ([_doc_to_dict(r) for r in rows], total)


def _cast_to_str_list(val: object) -> list[str]:
    """Safely cast a value to ``list[str]``."""
    if isinstance(val, list):
        return [str(v) for v in val]
    return []


def _doc_to_public(doc: PolicyDocument) -> dict:
    """Convert a PolicyDocument to a JSON-safe public dict."""
    return {
        "policy_key": doc.policy_key,
        "version": doc.version,
        "title": doc.title,
        "category": str(doc.category) if doc.category else "",
        "status": str(doc.status) if doc.status else "",
        "effective_date": doc.effective_date.isoformat() if doc.effective_date else None,
        "expiration_date": doc.expiration_date.isoformat() if doc.expiration_date else None,
        "source": doc.source or "",
        "content_summary": doc.content_summary or "",
        "id": str(doc.id),
    }


def _doc_to_dict(doc: PolicyDocument) -> dict:
    return {
        "policy_key": doc.policy_key,
        "version": doc.version,
        "title": doc.title,
        "category": doc.category,
        "status": doc.status,
        "effective_date": str(doc.effective_date) if doc.effective_date else None,
        "expiration_date": str(doc.expiration_date) if doc.expiration_date else None,
        "source": doc.source,
        "content_summary": doc.content_summary,
        "id": str(doc.id),
    }
