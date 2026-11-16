"""add_is_coming_soon_to_categories

Revision ID: c10d3e5a7b9f
Revises: b39e318cf142
Create Date: 2026-11-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c10d3e5a7b9f'
down_revision: Union[str, Sequence[str], None] = 'b39e318cf142'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_coming_soon column to categories table for future departments."""
    op.add_column(
        "categories",
        sa.Column("is_coming_soon", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_categories_is_coming_soon", "categories", ["is_coming_soon"])


def downgrade() -> None:
    """Remove is_coming_soon column from categories table."""
    op.drop_index("ix_categories_is_coming_soon", table_name="categories")
    op.drop_column("categories", "is_coming_soon")
