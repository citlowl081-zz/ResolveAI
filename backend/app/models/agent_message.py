"""AgentMessage SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AgentMessage(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence_number", name="uq_msg_session_seq"),
        UniqueConstraint("session_id", "turn_id", "turn_sequence", name="uq_msg_session_turn_turnseq"),
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
    role: Mapped[str] = mapped_column(
        ENUM("USER", "ASSISTANT", "TOOL", "SYSTEM", name="message_role", create_type=False),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=""
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    turn_sequence: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )
    tool_calls: Mapped[list[dict] | None] = mapped_column(
        JSONB, nullable=True
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    message_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
