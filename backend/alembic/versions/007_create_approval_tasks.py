"""create_approval_tasks

Revision ID: 007
Revises: 006
Create Date: 2026-07-15

Creates 2 enums + 1 table for the human-in-the-loop approval system:
- enums: approval_status, approval_type
- table: approval_tasks

Downgrade blocked unless the table is empty.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create approval_status, approval_type enums and approval_tasks table."""
    # ── 1. Enums ──────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE approval_status AS ENUM ("
        "'PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED'"
        ")"
    )
    op.execute(
        "CREATE TYPE approval_type AS ENUM ("
        "'HIGH_REFUND', 'RISK_HIT', 'EXCHANGE', 'MULTI_ITEM', 'MANUAL_REQUEST'"
        ")"
    )

    # ── 2. approval_tasks ─────────────────────────────────────────────
    op.create_table(
        "approval_tasks",
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
            "agent_session_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "action_id", sa.String(64), unique=True, nullable=False,
            comment="Canonical action_id from pending_action",
        ),
        sa.Column("tool_name", sa.String(50), nullable=False),
        sa.Column(
            "sanitized_action_payload", postgresql.JSONB, nullable=False,
            comment="Verified canonical_tool_input — PII stripped, NOT client-submitted",
        ),
        sa.Column(
            "approval_type",
            postgresql.ENUM(
                "HIGH_REFUND", "RISK_HIT", "EXCHANGE", "MULTI_ITEM", "MANUAL_REQUEST",
                name="approval_type", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING", "APPROVED", "REJECTED", "EXPIRED", "CANCELLED",
                name="approval_status", create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="LOW"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "requested_by", postgresql.UUID(as_uuid=True), nullable=False,
            comment="user_id who triggered the action",
        ),
        sa.Column(
            "decided_by", postgresql.UUID(as_uuid=True), nullable=True,
            comment="admin/operator who made the decision",
        ),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now() + interval '72 hours'"),
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_approval_tasks_user_id", "approval_tasks", ["user_id"])
    op.create_index("ix_approval_tasks_status", "approval_tasks", ["status"])
    op.create_index("ix_approval_tasks_type", "approval_tasks", ["approval_type"])
    op.create_index(
        "ix_approval_tasks_user_status", "approval_tasks", ["user_id", "status"],
    )
    op.create_check_constraint(
        "ck_approval_version_positive", "approval_tasks", "version >= 1",
    )


def downgrade() -> None:
    """Downgrade after verifying the table is empty."""
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM approval_tasks) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: approval_tasks is not empty. "
        "Delete all rows first.'; "
        "END IF; END $$"
    )

    op.drop_table("approval_tasks")

    op.execute("DROP TYPE approval_type")
    op.execute("DROP TYPE approval_status")
