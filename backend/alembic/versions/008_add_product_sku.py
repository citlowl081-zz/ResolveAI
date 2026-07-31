"""Add a nullable SKU used to identify the stable demo catalog.

Revision ID: 008
Revises: 007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008"
down_revision: str | Sequence[str] | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("sku", sa.String(length=40), nullable=True))
    op.create_index("ix_products_sku", "products", ["sku"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_column("products", "sku")
