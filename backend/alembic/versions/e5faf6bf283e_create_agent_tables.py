"""create_agent_tables

Revision ID: e5faf6bf283e
Revises: 003
Create Date: 2026-07-14

Creates 2 enums + 4 tables for agent infrastructure:
- enums: session_status, message_role
- tables: agent_sessions, agent_messages, agent_tool_logs, agent_traces

Downgrade blocked unless all 4 tables are empty (4 assertions).
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5faf6bf283e"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create session_status, message_role enums and 4 agent tables."""
    # ── 1. Enums ──────────────────────────────────────────────────────
    op.execute("CREATE TYPE session_status AS ENUM ('ACTIVE', 'COMPLETED', 'EXPIRED')")
    op.execute("CREATE TYPE message_role AS ENUM ('USER', 'ASSISTANT', 'TOOL', 'SYSTEM')")

    # ── 2. agent_sessions ────────────────────────────────────────────
    op.create_table(
        "agent_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False),
        sa.Column("status", postgresql.ENUM("ACTIVE", "COMPLETED", "EXPIRED",
                  name="session_status", create_type=False), nullable=False,
                  server_default="ACTIVE"),
        sa.Column("context_snapshot", postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        # Persistent turn lock (6 columns)
        sa.Column("active_turn_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active_turn_trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active_turn_idempotency_key_hash", sa.String(64), nullable=True),
        sa.Column("active_turn_request_hash", sa.String(64), nullable=True),
        sa.Column("active_turn_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_turn_expires_at", sa.DateTime(timezone=True), nullable=True),
        # Version, timestamps
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + interval '24 hours'")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_sessions_user_id", "agent_sessions", ["user_id"])
    op.create_index("ix_sessions_active", "agent_sessions", ["user_id"],
                    postgresql_where=sa.text("status = 'ACTIVE'"))

    # CHECK: message_count >= 0, active_turn all-or-nothing + expires_at > started_at
    op.create_check_constraint(
        "ck_sessions_message_count", "agent_sessions",
        "message_count >= 0",
    )
    op.create_check_constraint(
        "ck_active_turn_consistency", "agent_sessions",
        "(active_turn_id IS NULL "
        " AND active_turn_trace_id IS NULL "
        " AND active_turn_idempotency_key_hash IS NULL "
        " AND active_turn_request_hash IS NULL "
        " AND active_turn_started_at IS NULL "
        " AND active_turn_expires_at IS NULL) "
        "OR "
        "(active_turn_id IS NOT NULL "
        " AND active_turn_trace_id IS NOT NULL "
        " AND active_turn_idempotency_key_hash IS NOT NULL "
        " AND active_turn_request_hash IS NOT NULL "
        " AND active_turn_started_at IS NOT NULL "
        " AND active_turn_expires_at IS NOT NULL "
        " AND active_turn_expires_at > active_turn_started_at)",
    )

    # ── 3. agent_messages ────────────────────────────────────────────
    op.create_table(
        "agent_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agent_sessions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", postgresql.ENUM("USER", "ASSISTANT", "TOOL", "SYSTEM",
                  name="message_role", create_type=False), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("turn_sequence", sa.SmallInteger(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB, nullable=True),
        sa.Column("tool_call_id", sa.String(100), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_unique_constraint("uq_msg_session_seq", "agent_messages",
                                ["session_id", "sequence_number"])
    op.create_unique_constraint("uq_msg_session_turn_turnseq", "agent_messages",
                                ["session_id", "turn_id", "turn_sequence"])
    op.create_index("ix_messages_session_created", "agent_messages",
                    ["session_id", "created_at"])

    # ── 4. agent_tool_logs ───────────────────────────────────────────
    op.create_table(
        "agent_tool_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agent_sessions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agent_messages.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_call_id", sa.String(100), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_input", postgresql.JSONB, nullable=False),
        sa.Column("tool_output", postgresql.JSONB, nullable=True),
        sa.Column("is_success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_index("ix_tool_logs_session", "agent_tool_logs", ["session_id"])
    op.create_index("ix_tool_logs_turn", "agent_tool_logs", ["session_id", "turn_id"])
    op.create_index("ix_tool_logs_trace_id", "agent_tool_logs", ["trace_id"])
    op.create_index("ix_tool_logs_tool_name", "agent_tool_logs", ["tool_name"])
    op.create_index("ix_tool_logs_tool_call_id", "agent_tool_logs", ["tool_call_id"])

    # Partial unique: one successful log per tool_call per turn
    op.execute(
        "CREATE UNIQUE INDEX uq_successful_tool_call "
        "ON agent_tool_logs (session_id, turn_id, tool_call_id) "
        "WHERE is_success = TRUE"
    )

    # ── 5. agent_traces ──────────────────────────────────────────────
    op.create_table(
        "agent_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agent_sessions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_name", sa.String(50), nullable=False),
        sa.Column("node_input", postgresql.JSONB, nullable=True),
        sa.Column("node_output", postgresql.JSONB, nullable=True),
        sa.Column("routing_decision", sa.String(50), nullable=True),
        sa.Column("llm_call", postgresql.JSONB, nullable=True),
        sa.Column("tool_calls_summary", postgresql.JSONB, nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("is_success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_detail", postgresql.JSONB, nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_unique_constraint("uq_trace_traceid_seq", "agent_traces",
                                ["trace_id", "sequence"])
    op.create_index("ix_traces_session", "agent_traces", ["session_id"])
    op.create_index("ix_traces_turn", "agent_traces", ["session_id", "turn_id"])
    op.create_index("ix_traces_node_name", "agent_traces", ["node_name"])


def downgrade() -> None:
    """Downgrade after verifying all agent tables are empty (4 assertions)."""
    # ── Assertion 1: agent_traces must be empty ───────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM agent_traces) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: agent_traces is not empty. "
        "Delete all rows first.'; "
        "END IF; END $$"
    )

    # ── Assertion 2: agent_tool_logs must be empty ───────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM agent_tool_logs) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: agent_tool_logs is not empty. "
        "Delete all rows first.'; "
        "END IF; END $$"
    )

    # ── Assertion 3: agent_messages must be empty ────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM agent_messages) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: agent_messages is not empty. "
        "Delete all rows first.'; "
        "END IF; END $$"
    )

    # ── Assertion 4: agent_sessions must be empty ────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM agent_sessions) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: agent_sessions is not empty. "
        "Delete all rows first.'; "
        "END IF; END $$"
    )

    # All assertions passed. Proceed with DDL.
    op.drop_table("agent_traces")
    op.drop_table("agent_tool_logs")
    op.drop_table("agent_messages")
    op.drop_table("agent_sessions")

    op.execute("DROP TYPE message_role")
    op.execute("DROP TYPE session_status")
