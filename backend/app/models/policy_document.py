"""PolicyDocument SQLAlchemy model — version-per-row with policy_key stable identity."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import PolicyCategory, PolicyStatus


class PolicyDocument(Base):
    """After-sales policy document — one row per (policy_key, version).

    The stable business identity is ``policy_key``.  Each edit produces a
    new row with an incremented ``version``.  At most one version per
    ``policy_key`` may be ``ACTIVE`` at any time (enforced by a partial
    unique index in the migration).
    """

    __tablename__ = "policy_documents"

    # ── Primary key (internal, never exposed) ──────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # ── Versioned identity ─────────────────────────────────────────────
    policy_key: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Stable business key, e.g. POL-REF-001"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1", comment="Monotonic per policy_key"
    )

    # ── Content ────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[PolicyCategory] = mapped_column(
        Enum(PolicyCategory, name="policy_category", create_constraint=False),
        nullable=False,
    )
    issue_types: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="BLAKE2b hex digest of normalised semantic fields",
    )

    # ── Metadata ───────────────────────────────────────────────────────
    metadata_filter: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="'{}'::jsonb"
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Lifecycle ──────────────────────────────────────────────────────
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus, name="policy_status", create_constraint=False),
        nullable=False,
        server_default="DRAFT",
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Version chain ──────────────────────────────────────────────────
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_documents.id", ondelete="SET NULL"),
        nullable=True,
        comment="Points to the newer version that replaced this one",
    )

    # ── Timestamps ─────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Table-level constraints ────────────────────────────────────────
    # Partial unique index uq_policy_docs_key_active (UNIQUE (policy_key)
    # WHERE status = 'ACTIVE') is declared in the migration — SQLAlchemy
    # does not natively express partial indexes in __table_args__.
    __table_args__ = (
        UniqueConstraint("policy_key", "version", name="uq_policy_docs_key_version"),
        CheckConstraint("version >= 1", name="ck_policy_docs_version_positive"),
    )

    def __repr__(self) -> str:
        return (
            f"<PolicyDocument(policy_key={self.policy_key!r}, "
            f"version={self.version}, status={self.status!r})>"
        )
