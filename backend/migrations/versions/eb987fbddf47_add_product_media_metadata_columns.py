"""add_product_media_metadata_columns

Revision ID: eb987fbddf47
Revises: d4fc55d592df
Create Date: 2026-11-10 20:06:30.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb987fbddf47'
down_revision: Union[str, Sequence[str], None] = 'd4fc55d592df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('product_images', sa.Column('storage_key', sa.String(length=255), nullable=True))
    op.add_column('product_images', sa.Column('file_size_bytes', sa.BigInteger(), nullable=True))
    op.add_column('product_images', sa.Column('mime_type', sa.String(length=64), nullable=True))
    op.add_column('product_images', sa.Column('width', sa.Integer(), nullable=True))
    op.add_column('product_images', sa.Column('height', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_product_images_storage_key'), 'product_images', ['storage_key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_product_images_storage_key'), table_name='product_images')
    op.drop_column('product_images', 'height')
    op.drop_column('product_images', 'width')
    op.drop_column('product_images', 'mime_type')
    op.drop_column('product_images', 'file_size_bytes')
    op.drop_column('product_images', 'storage_key')
