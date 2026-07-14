"""ReshipmentOrder SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import ReshipmentStatus


class ReshipmentOrder(Base):
    __tablename__ = "reshipment_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    original_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    reshipment_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    missing_items: Mapped[dict] = mapped_column(JSONB, nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReshipmentStatus] = mapped_column(
        Enum(ReshipmentStatus, name="reshipment_status", create_constraint=False),
        nullable=False,
    )
    tracking_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, unique=True
    )
    carrier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
