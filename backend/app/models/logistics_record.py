"""LogisticsRecord SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import LogisticsStatus


class LogisticsRecord(Base):
    __tablename__ = "logistics_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    tracking_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    carrier: Mapped[str] = mapped_column(String(50), nullable=False, server_default="SF Express")
    status: Mapped[LogisticsStatus] = mapped_column(
        Enum(LogisticsStatus, name="logistics_status", create_constraint=False),
        nullable=False,
    )
    current_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    estimated_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    events: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
