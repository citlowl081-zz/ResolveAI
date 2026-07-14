"""PolicyChunk SQLAlchemy model — one embedding per chunk of a policy version."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PolicyChunk(Base):
    """A chunk of a ``PolicyDocument`` version with its pgvector embedding.

    Each row holds one text segment and its ``vector(1536)`` embedding.
    Chunks are re-generated (and old rows deleted) whenever a policy
    version's content changes.
    """

    __tablename__ = "policy_chunks"

    # ── Primary key ────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # ── Parent document version ────────────────────────────────────────
    policy_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Chunk data ─────────────────────────────────────────────────────
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="0-based position within the version"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
        comment="pgvector embedding (1536 dimensions)",
    )
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Timestamp ──────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Table-level constraints ────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "policy_document_id", "chunk_index", name="uq_policy_chunks_doc_idx"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PolicyChunk(doc_id={self.policy_document_id!r}, "
            f"chunk={self.chunk_index})>"
        )
