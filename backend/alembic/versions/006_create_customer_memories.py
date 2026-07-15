"""create_customer_memories

Revision ID: 006
Revises: 005
Create Date: 2026-07-15

Creates 2 enums + 1 table for the long-term user memory system:
- enums: memory_type, memory_status
- table: customer_memories

Downgrade blocked unless the table is empty.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, Sequence[str], None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create memory_type, memory_status enums and customer_memories table."""
    # ── 1. Enums ──────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE memory_type AS ENUM ("
        "'PREFERENCE', 'FACT', 'SUMMARY', 'COMMITMENT', 'RISK_PROFILE'"
        ")"
    )
    op.execute(
        "CREATE TYPE memory_status AS ENUM ("
        "'ACTIVE', 'ARCHIVED', 'SUPERSEDED'"
        ")"
    )

    # ── 2. customer_memories ─────────────────────────────────────────
    op.create_table(
        "customer_memories",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "memory_type",
            postgresql.ENUM(
                "PREFERENCE", "FACT", "SUMMARY", "COMMITMENT", "RISK_PROFILE",
                name="memory_type", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "key", sa.String(200), nullable=True,
            comment="Stable dedup key within (user_id, memory_type)",
        ),
        sa.Column(
            "content", sa.Text(), nullable=False,
            comment="Human-readable memory text shown to the LLM",
        ),
        sa.Column(
            "structured_data", postgresql.JSONB, nullable=True,
            comment="Machine-readable metadata (e.g. preferred_channel, risk_score)",
        ),
        sa.Column(
            "source", sa.String(100), nullable=False,
            server_default="agent_inferred",
            comment="How this memory was created: explicit_remember, agent_inferred, session_summary",
        ),
        sa.Column(
            "confidence", sa.Float(), nullable=False, server_default="1.0",
            comment="0.0–1.0 confidence score for agent-inferred memories",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE", "ARCHIVED", "SUPERSEDED",
                name="memory_status", create_type=False,
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "superseded_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customer_memories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default="1",
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

    # ── 3. Indexes & constraints ─────────────────────────────────────
    op.create_index("ix_customer_memories_user_id", "customer_memories", ["user_id"])
    op.create_index("ix_customer_memories_type", "customer_memories", ["memory_type"])
    op.create_index("ix_customer_memories_status", "customer_memories", ["status"])
    op.create_index("ix_customer_memories_source", "customer_memories", ["source"])
    # Composite index for common query: user's active memories filtered by type
    op.create_index(
        "ix_customer_memories_user_type_status",
        "customer_memories", ["user_id", "memory_type", "status"],
    )
    # Unique constraint: one active key per (user_id, memory_type)
    op.execute(
        "CREATE UNIQUE INDEX uq_customer_memories_user_type_key "
        "ON customer_memories (user_id, memory_type, key) "
        "WHERE status = 'ACTIVE' AND key IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade after verifying the table is empty."""
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM customer_memories) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: customer_memories is not empty. "
        "Delete all rows first.'; "
        "END IF; END $$"
    )

    op.drop_table("customer_memories")

    op.execute("DROP TYPE memory_status")
    op.execute("DROP TYPE memory_type")
