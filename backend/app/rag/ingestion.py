"""PolicyIngestionService — 3-phase ingestion with YAML parsing and advisory locks."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.enums import PolicyStatus
from app.models.policy_chunk import PolicyChunk
from app.models.policy_document import PolicyDocument
from app.rag.chunking import chunk_text
from app.rag.content_hash import compute_content_hash
from app.rag.embeddings import EmbeddingProvider
from app.rag.validation import validate_policy_key_and_category
from app.repositories.policy_document import PolicyDocumentRepository


class PolicyIngestionService:
    """Load policy files from ``data/policies/``, chunk, embed, and store.

    Implements the 3-phase ingestion protocol with ``pg_advisory_xact_lock``
    and ``lock_timeout = 5s`` for concurrent safety.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: EmbeddingProvider,
        policies_dir: Path,
    ) -> None:
        self._session_factory = session_factory
        self._embedding = embedding_provider
        self._policies_dir = policies_dir.resolve()

    # ── Public API ────────────────────────────────────────────────────

    async def ingest_all(self, activate: bool = False) -> dict[str, Any]:
        """Scan ``data/policies/`` and ingest every ``.md`` / ``.txt`` file.

        Returns a summary dict: ``{policy_key: status}`` where status is
        ``"created"``, ``"skipped"``, or ``"error"``.
        """
        report: dict[str, str] = {}
        for fpath in sorted(self._policies_dir.glob("*")):
            if fpath.suffix not in (".md", ".txt"):
                continue
            try:
                result = await self.ingest_file(fpath, activate=activate)
                report[result["policy_key"]] = result["status"]
            except Exception:
                report[fpath.name] = "error"
        return report

    async def ingest_file(
        self, path: Path, activate: bool = False,
    ) -> dict[str, Any]:
        """Ingest a single policy file through the 3-phase protocol."""
        path = path.resolve()
        if not str(path).startswith(str(self._policies_dir)):
            raise ValueError(
                f"Policy file {path} is outside the policies directory"
            )

        doc_data = _parse_policy_file(path)

        # ── Phase A: Read & Validate (short DB transaction) ──────────
        async with self._session_factory() as session_a, session_a.begin():
            await session_a.execute(text("SET LOCAL lock_timeout = '5s'"))
            lock_key = _lock_key(doc_data["policy_key"])
            await session_a.execute(
                text("SELECT pg_advisory_xact_lock(:k)"), {"k": lock_key},
            )

            repo = PolicyDocumentRepository(session_a)
            latest = await repo.get_latest(doc_data["policy_key"])
            candidate_hash = compute_content_hash(doc_data)

            # Compare against latest version
            if latest is not None and latest.content_hash == candidate_hash:
                await session_a.rollback()
                return {"policy_key": doc_data["policy_key"], "status": "skipped"}

            # Validate metadata
            validate_policy_key_and_category(
                doc_data["policy_key"], doc_data["category"],
            )
            if "effective_date" not in doc_data or not doc_data["effective_date"]:
                raise ValueError("effective_date is required")
            if isinstance(doc_data["effective_date"], str):
                doc_data["effective_date"] = date.fromisoformat(
                    doc_data["effective_date"]
                )
        # ── Phase B: Embed (NO DB connection) ────────────────────────
        chunks = chunk_text(doc_data["content"])
        if not chunks:
            raise ValueError("Policy content produced no chunks")
        vectors = await self._embedding.embed(chunks)
        if len(vectors) != len(chunks):
            raise RuntimeError(
                f"Embedding returned {len(vectors)} vectors for {len(chunks)} chunks"
            )

        # ── Phase C: Atomic Write (short DB transaction) ─────────────
        async with self._session_factory() as session_c:
            async with session_c.begin():
                await session_c.execute(text("SET LOCAL lock_timeout = '5s'"))
                await session_c.execute(
                    text("SELECT pg_advisory_xact_lock(:k)"), {"k": lock_key},
                )

                repo = PolicyDocumentRepository(session_c)
                # Re-read latest (may have changed since Phase A)
                latest2 = await repo.get_latest(doc_data["policy_key"])
                candidate_hash2 = compute_content_hash(doc_data)
                if latest2 is not None and latest2.content_hash == candidate_hash2:
                    return {
                        "policy_key": doc_data["policy_key"],
                        "status": "skipped",
                    }

                new_version = (latest2.version if latest2 else 0) + 1

                # Insert document
                doc = PolicyDocument(
                    policy_key=doc_data["policy_key"],
                    version=new_version,
                    title=doc_data["title"],
                    category=doc_data["category"],
                    issue_types=doc_data.get("issue_types", []),
                    content=doc_data["content"],
                    content_summary=doc_data.get("content_summary", ""),
                    content_hash=candidate_hash2,
                    metadata_filter=doc_data.get("metadata_filter", {}),
                    effective_date=doc_data["effective_date"],
                    expiration_date=doc_data.get("expiration_date"),
                    status="DRAFT",
                    source=doc_data.get("source", ""),
                )
                session_c.add(doc)
                await session_c.flush()

                # Insert chunks
                for i, (chunk_text_val, vec) in enumerate(zip(chunks, vectors, strict=True)):
                    session_c.add(
                        PolicyChunk(
                            policy_document_id=doc.id,
                            chunk_index=i,
                            content=chunk_text_val,
                            embedding=vec,
                            char_count=len(chunk_text_val),
                        )
                    )

                # Activate if requested
                status = "DRAFT"
                if activate:
                    # Supersede old ACTIVE
                    active = await repo.get_active(doc_data["policy_key"])
                    if active is not None:
                        active.status = PolicyStatus.SUPERSEDED  # type: ignore[assignment]
                        active.superseded_by = doc.id
                    doc.status = PolicyStatus.ACTIVE  # type: ignore[assignment]
                    status = "ACTIVE"

            return {
                "policy_key": doc_data["policy_key"],
                "status": status,
                "version": new_version,
            }


# ── Internal helpers ─────────────────────────────────────────────────


def _lock_key(policy_key: str) -> int:
    """32-bit integer lock key derived from the policy_key."""
    return (
        int.from_bytes(
            hashlib.sha256(f"policy_ingestion:{policy_key}".encode()).digest()[:4],
            "big",
        )
        % 2_147_483_647
    )


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_policy_file(path: Path) -> dict[str, Any]:
    """Parse a Markdown/TXT policy file with YAML frontmatter + body."""
    text_content = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text_content)
    if not m:
        raise ValueError(f"Policy file {path} has no YAML frontmatter")

    frontmatter_str = m.group(1)
    body = text_content[m.end():].strip()

    if not body:
        raise ValueError(f"Policy file {path} has empty body text")

    metadata: dict[str, Any] = yaml.safe_load(frontmatter_str)
    if not isinstance(metadata, dict):
        raise ValueError(f"Policy file {path} has non-dict frontmatter")

    # Required fields
    for field in ("policy_key", "title", "category", "effective_date"):
        if field not in metadata or metadata[field] is None:
            raise ValueError(
                f"Policy file {path} is missing required field '{field}'"
            )

    metadata["content"] = body
    metadata.setdefault("issue_types", [])
    metadata.setdefault("source", "")
    metadata.setdefault("metadata_filter", {})
    metadata.setdefault("expiration_date", None)

    # content_summary: auto-generate if empty
    if not metadata.get("content_summary"):
        cleaned = " ".join(body.split())[:200]
        metadata["content_summary"] = cleaned

    return metadata
