"""create_policy_tables

Revision ID: 005
Revises: e5faf6bf283e
Create Date: 2026-07-14

Creates 2 enums + 2 tables for the RAG policy knowledge base:
- enums: policy_category, policy_status
- tables: policy_documents, policy_chunks

Downgrade blocked unless both tables are empty.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "e5faf6bf283e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create policy_category, policy_status enums and policy_documents, policy_chunks tables."""
    # ── 1. Enums ──────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE policy_category AS ENUM ("
        "'RETURN', 'REFUND', 'EXCHANGE', 'RESHIPMENT', "
        "'LOGISTICS', 'RISK', 'SOP', 'GENERAL'"
        ")"
    )
    op.execute(
        "CREATE TYPE policy_status AS ENUM ("
        "'DRAFT', 'ACTIVE', 'SUPERSEDED', 'ARCHIVED'"
        ")"
    )

    # ── 2. policy_documents ───────────────────────────────────────────
    op.create_table(
        "policy_documents",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("policy_key", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "RETURN", "REFUND", "EXCHANGE", "RESHIPMENT",
                "LOGISTICS", "RISK", "SOP", "GENERAL",
                name="policy_category", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "issue_types", postgresql.JSONB, nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=True),
        sa.Column(
            "content_hash", sa.String(128), nullable=True,
            comment="BLAKE2b hex digest of normalised semantic fields",
        ),
        sa.Column(
            "metadata_filter", postgresql.JSONB, nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED",
                name="policy_status", create_type=False,
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column(
            "superseded_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("policy_documents.id", ondelete="SET NULL"),
            nullable=True,
            comment="Points to the newer version that replaced this one",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── Indexes & constraints: policy_documents ───────────────────────
    op.create_unique_constraint(
        "uq_policy_docs_key_version", "policy_documents",
        ["policy_key", "version"],
    )
    # Partial unique: at most one ACTIVE per policy_key
    op.execute(
        "CREATE UNIQUE INDEX uq_policy_docs_key_active "
        "ON policy_documents (policy_key) "
        "WHERE status = 'ACTIVE'"
    )
    op.create_check_constraint(
        "ck_policy_docs_version_positive", "policy_documents",
        "version >= 1",
    )
    op.create_index("ix_policy_docs_category", "policy_documents", ["category"])
    op.create_index("ix_policy_docs_status", "policy_documents", ["status"])
    op.create_index(
        "ix_policy_docs_superseded_by", "policy_documents", ["superseded_by"]
    )

    # ── 3. policy_chunks ──────────────────────────────────────────────
    # Use pgvector's SQLAlchemy Vector type so the column is created with
    # the correct type in a single step.
    from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

    op.create_table(
        "policy_chunks",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "policy_document_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("policy_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_index", sa.Integer(), nullable=False,
            comment="0-based position within the version",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "embedding", Vector(1536), nullable=False,
            comment="pgvector embedding (1536 dimensions)",
        ),
        sa.Column("char_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── Indexes & constraints: policy_chunks ──────────────────────────
    op.create_unique_constraint(
        "uq_policy_chunks_doc_idx", "policy_chunks",
        ["policy_document_id", "chunk_index"],
    )
    op.create_index(
        "ix_policy_chunks_doc_id", "policy_chunks", ["policy_document_id"]
    )


def downgrade() -> None:
    """Downgrade after verifying both policy tables are empty."""
    # ── Assertion 1: policy_chunks must be empty ──────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM policy_chunks) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: policy_chunks is not empty. "
        "Delete all rows first.'; "
        "END IF; END $$"
    )

    # ── Assertion 2: policy_documents must be empty ───────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM policy_documents) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: policy_documents is not empty. "
        "Delete all rows first.'; "
        "END IF; END $$"
    )

    # All assertions passed. Proceed with DDL.
    op.drop_table("policy_chunks")
    op.drop_table("policy_documents")

    op.execute("DROP TYPE policy_status")
    op.execute("DROP TYPE policy_category")
