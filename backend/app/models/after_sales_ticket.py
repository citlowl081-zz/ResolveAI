"""AfterSalesTicket SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import IntentType, ResolutionType, TicketStatus


class AfterSalesTicket(Base):
    __tablename__ = "after_sales_tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    intent: Mapped[IntentType] = mapped_column(
        Enum(IntentType, name="intent_type", create_constraint=False),
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", create_constraint=False),
        nullable=False, index=True,
    )
    resolution_type: Mapped[ResolutionType | None] = mapped_column(
        Enum(ResolutionType, name="resolution_type", create_constraint=False),
        nullable=True,
    )
    customer_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_items: Mapped[dict] = mapped_column(JSONB, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_solution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolution_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reject_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
