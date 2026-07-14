"""AgentToolLog SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AgentToolLog(Base):
    __tablename__ = "agent_tool_logs"

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
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_messages.id", ondelete="RESTRICT"),
        nullable=False
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    tool_call_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    tool_input: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )
    tool_output: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    is_success: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
