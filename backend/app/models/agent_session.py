"""AgentSession SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        CheckConstraint("message_count >= 0", name="ck_sessions_message_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        ENUM("ACTIVE", "COMPLETED", "EXPIRED", name="session_status", create_type=False),
        nullable=False, server_default="ACTIVE"
    )
    context_snapshot: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    # Persistent turn lock (6 columns)
    active_turn_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    active_turn_trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    active_turn_idempotency_key_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    active_turn_request_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    active_turn_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active_turn_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.text("now() + interval '24 hours'")
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
