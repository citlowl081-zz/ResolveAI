"""CustomerMemory SQLAlchemy model — long-term user memory for the Agent."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import MemoryStatus, MemoryType


class CustomerMemory(Base):
    __tablename__ = "customer_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        Enum(MemoryType, name="memory_type", create_constraint=False),
        nullable=False,
    )
    key: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Stable dedup key within (user_id, memory_type)",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Human-readable memory text shown to the LLM",
    )
    structured_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Machine-readable metadata (e.g. preferred_channel, risk_score)",
    )
    source: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="agent_inferred",
        comment="How this memory was created: explicit_remember, agent_inferred, session_summary",
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0",
        comment="0.0–1.0 confidence score for agent-inferred memories",
    )
    status: Mapped[MemoryStatus] = mapped_column(
        Enum(MemoryStatus, name="memory_status", create_constraint=False),
        nullable=False, server_default="ACTIVE",
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_memories.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
