"""AgentTrace SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AgentTrace(Base):
    __tablename__ = "agent_traces"
    __table_args__ = (
        UniqueConstraint("trace_id", "sequence", name="uq_trace_traceid_seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    node_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    node_input: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    node_output: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    routing_decision: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    llm_call: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    tool_calls_summary: Mapped[list[dict] | None] = mapped_column(
        JSONB, nullable=True
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    is_success: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    error_detail: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    sequence: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
