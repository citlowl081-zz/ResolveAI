"""RefundRecord SQLAlchemy model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import RefundType


class RefundRecord(Base):
    __tablename__ = "refund_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    refund_type: Mapped[RefundType] = mapped_column(
        Enum(RefundType, name="refund_type", create_constraint=False),
        nullable=False,
    )
    refund_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_items: Mapped[dict] = mapped_column(JSONB, nullable=False)
    calculation_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
