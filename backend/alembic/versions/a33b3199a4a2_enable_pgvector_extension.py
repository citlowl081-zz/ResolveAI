"""enable_pgvector_extension

Revision ID: a33b3199a4a2
Revises: 
Create Date: 2026-07-13 16:56:27.066222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a33b3199a4a2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pgvector extension."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Remove pgvector extension."""
    op.execute("DROP EXTENSION IF EXISTS vector")
