"""create_after_sales_tables

Revision ID: 003
Revises: bc03591cd96c
Create Date: 2026-07-14

Creates 5 enums + 2 sequences + 3 tables for after-sales:
- enums: intent_type, ticket_status, resolution_type, refund_type, reshipment_status
- order_status extended: +REFUNDED
- sequences: ticket_number_seq, reshipment_number_seq
- ALTER order_items: +refunded_quantity, +reshipped_quantity
- tables: after_sales_tickets, refund_records, reshipment_orders
- constraints: UNIQUE(ticket_id) on refunds & reshipments,
  partial unique index on active tickets
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "bc03591cd96c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- 1. Sequences ----
    op.execute(sa.text("CREATE SEQUENCE ticket_number_seq START 100001"))
    op.execute(sa.text("CREATE SEQUENCE reshipment_number_seq START 100001"))

    # ---- 2. Extend order_status enum ----
    # CREATE TYPE new → convert → DROP old → RENAME
    order_status_new = postgresql.ENUM(
        "PENDING_PAYMENT", "PAID", "SHIPPED", "DELIVERED",
        "CANCELLED", "REFUNDED",
        name="order_status_new", create_type=True,
    )
    op.execute(sa.text(
        "ALTER TABLE orders ALTER COLUMN status TYPE order_status_new "
        "USING status::text::order_status_new"
    ))
    # Drop old type
    sa.Enum(name="order_status").drop(op.get_bind(), checkfirst=True)
    order_status_new_rename = postgresql.ENUM(
        "PENDING_PAYMENT", "PAID", "SHIPPED", "DELIVERED",
        "CANCELLED", "REFUNDED",
        name="order_status", create_type=False,
    )
    order_status_new_rename.create(op.get_bind(), checkfirst=True)
    op.execute(sa.text(
        "ALTER TABLE orders ALTER COLUMN status TYPE order_status "
        "USING status::text::order_status"
    ))
    sa.Enum(name="order_status_new").drop(op.get_bind(), checkfirst=True)
    # Re-add any server_default if needed — orders.status has no default, skip.

    # ---- 3. New Enums (5) ----
    intent_type = postgresql.ENUM(
        "LOGISTICS_INQUIRY", "PRE_SHIP_REFUND", "QUALITY_REFUND",
        "EXCHANGE", "MISSING_PARTS", "OTHER",
        name="intent_type", create_type=True,
    )
    ticket_status = postgresql.ENUM(
        "APPROVED", "REJECTED", "COMPLETED", "CANCELLED", "NEEDS_REVIEW",
        name="ticket_status", create_type=True,
    )
    resolution_type = postgresql.ENUM(
        "REFUND", "EXCHANGE", "RESHIPMENT", "INFO_ONLY",
        name="resolution_type", create_type=True,
    )
    refund_type = postgresql.ENUM(
        "FULL", "PARTIAL", "SHIPPING_FEE",
        name="refund_type", create_type=True,
    )
    reshipment_status = postgresql.ENUM(
        "CREATED", "SHIPPED", "DELIVERED", "CANCELLED",
        name="reshipment_status", create_type=True,
    )

    # ---- 4. ALTER order_items ----
    op.add_column("order_items", sa.Column("refunded_quantity", sa.Integer, nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("reshipped_quantity", sa.Integer, nullable=False, server_default="0"))
    op.create_check_constraint("ck_order_items_refunded_qty_nonnegative", "order_items", sa.text("refunded_quantity >= 0"))
    op.create_check_constraint("ck_order_items_reshipped_qty_nonnegative", "order_items", sa.text("reshipped_quantity >= 0"))
    op.create_check_constraint("ck_order_items_refund_reshipped_sum", "order_items", sa.text("refunded_quantity + reshipped_quantity <= quantity"))

    # ---- 5. after_sales_tickets ----
    op.create_table(
        "after_sales_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_number", sa.String(30), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("intent", intent_type, nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("resolution_type", resolution_type, nullable=True),
        sa.Column("customer_request", sa.Text, nullable=True),
        sa.Column("requested_items", postgresql.JSONB, nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("operator_notes", sa.Text, nullable=True),
        sa.Column("proposed_solution", postgresql.JSONB, nullable=True),
        sa.Column("resolution_result", postgresql.JSONB, nullable=True),
        sa.Column("reject_reason", sa.Text, nullable=True),
        sa.Column("reject_code", sa.String(20), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tickets_user_id", "after_sales_tickets", ["user_id"])
    op.create_index("ix_tickets_order_id", "after_sales_tickets", ["order_id"])
    op.create_index("ix_tickets_status", "after_sales_tickets", ["status"])
    op.create_index("ix_tickets_number", "after_sales_tickets", ["ticket_number"], unique=True)
    # Partial unique index for active ticket dedup
    op.execute(sa.text(
        "CREATE UNIQUE INDEX uq_active_ticket_fingerprint "
        "ON after_sales_tickets (order_id, intent, request_fingerprint) "
        "WHERE status IN ('APPROVED', 'NEEDS_REVIEW')"
    ))

    # ---- 6. refund_records ----
    op.create_table(
        "refund_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("after_sales_tickets.id"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("shipping_refund_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("refund_type", refund_type, nullable=False),
        sa.Column("refund_reason", sa.Text, nullable=True),
        sa.Column("refund_items", postgresql.JSONB, nullable=False),
        sa.Column("calculation_breakdown", postgresql.JSONB, nullable=True),
        sa.Column("rule_version", sa.String(20), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("processed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_refunds_ticket_id", "refund_records", ["ticket_id"], unique=True)
    op.create_index("ix_refunds_order_id", "refund_records", ["order_id"])
    op.create_check_constraint("ck_refund_amount_positive", "refund_records", sa.text("refund_amount > 0"))
    op.create_check_constraint("ck_shipping_refund_nonnegative", "refund_records", sa.text("shipping_refund_amount >= 0"))

    # ---- 7. reshipment_orders ----
    op.create_table(
        "reshipment_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("after_sales_tickets.id"), nullable=False),
        sa.Column("original_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reshipment_number", sa.String(30), nullable=False, unique=True),
        sa.Column("missing_items", postgresql.JSONB, nullable=False),
        sa.Column("shipping_address", sa.Text, nullable=False),
        sa.Column("status", reshipment_status, nullable=False),
        sa.Column("tracking_number", sa.String(50), nullable=True, unique=True),
        sa.Column("carrier", sa.String(50), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("processed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reshipments_ticket_id", "reshipment_orders", ["ticket_id"], unique=True)
    op.create_index("ix_reshipments_order_id", "reshipment_orders", ["original_order_id"])
    op.create_index("ix_reshipments_number", "reshipment_orders", ["reshipment_number"], unique=True)
    op.create_index("ix_reshipments_tracking", "reshipment_orders", ["tracking_number"], unique=True)


def downgrade() -> None:
    # ---- Assertion 1: No after_sales_tickets data ----
    op.execute(sa.text(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM after_sales_tickets) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: after_sales_tickets is not empty. Delete all rows first.'; "
        "END IF; END $$"
    ))

    # ---- Assertion 2: No refund_records data ----
    op.execute(sa.text(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM refund_records) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: refund_records is not empty. Delete all rows first.'; "
        "END IF; END $$"
    ))

    # ---- Assertion 3: No reshipment_orders data ----
    op.execute(sa.text(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM reshipment_orders) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: reshipment_orders is not empty. Delete all rows first.'; "
        "END IF; END $$"
    ))

    # ---- Assertion 4: No REFUNDED orders ----
    op.execute(sa.text(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM orders WHERE status = 'REFUNDED') THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: orders with REFUNDED status exist. Revert orders to previous status first.'; "
        "END IF; END $$"
    ))

    # ---- Assertion 5: No refunded quantities ----
    op.execute(sa.text(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM order_items WHERE refunded_quantity > 0) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: order_items have non-zero refunded_quantity. Reset to 0 first.'; "
        "END IF; END $$"
    ))

    # ---- Assertion 6: No reshipped quantities ----
    op.execute(sa.text(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM order_items WHERE reshipped_quantity > 0) THEN "
        "RAISE EXCEPTION 'DOWNGRADE BLOCKED: order_items have non-zero reshipped_quantity. Reset to 0 first.'; "
        "END IF; END $$"
    ))

    # All assertions passed — proceed with DDL

    # Drop tables
    op.drop_table("reshipment_orders")
    op.drop_table("refund_records")
    op.drop_table("after_sales_tickets")

    # Drop sequences
    op.execute(sa.text("DROP SEQUENCE reshipment_number_seq"))
    op.execute(sa.text("DROP SEQUENCE ticket_number_seq"))

    # Revert order_status enum
    order_status_old = postgresql.ENUM(
        "PENDING_PAYMENT", "PAID", "SHIPPED", "DELIVERED", "CANCELLED",
        name="order_status_old", create_type=True,
    )
    op.execute(sa.text(
        "ALTER TABLE orders ALTER COLUMN status TYPE order_status_old "
        "USING status::text::order_status_old"
    ))
    sa.Enum(name="order_status").drop(op.get_bind(), checkfirst=True)
    order_status_old_rename = postgresql.ENUM(
        "PENDING_PAYMENT", "PAID", "SHIPPED", "DELIVERED", "CANCELLED",
        name="order_status", create_type=False,
    )
    order_status_old_rename.create(op.get_bind(), checkfirst=True)
    op.execute(sa.text(
        "ALTER TABLE orders ALTER COLUMN status TYPE order_status "
        "USING status::text::order_status"
    ))
    sa.Enum(name="order_status_old").drop(op.get_bind(), checkfirst=True)

    # Drop new enums
    sa.Enum(name="reshipment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="refund_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="resolution_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ticket_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="intent_type").drop(op.get_bind(), checkfirst=True)

    # Drop order_items columns
    op.drop_constraint("ck_order_items_refund_reshipped_sum", "order_items", type_="check")
    op.drop_constraint("ck_order_items_reshipped_qty_nonnegative", "order_items", type_="check")
    op.drop_constraint("ck_order_items_refunded_qty_nonnegative", "order_items", type_="check")
    op.drop_column("order_items", "reshipped_quantity")
    op.drop_column("order_items", "refunded_quantity")
