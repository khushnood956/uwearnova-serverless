"""create_categories_and_collections_tables

Revision ID: 19b855e08445
Revises: 3d8042914983
Create Date: 2026-11-10 19:39:07.834002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19b855e08445'
down_revision: Union[str, Sequence[str], None] = '3d8042914983'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('parent_id', sa.BigInteger(), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=1024), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], name=op.f('fk_categories_parent_id_categories'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
        sa.UniqueConstraint('name', name=op.f('uq_categories_name')),
        sa.UniqueConstraint('slug', name=op.f('uq_categories_slug')),
    )
    op.create_index(op.f('ix_categories_id'), 'categories', ['id'], unique=False)
    op.create_index(op.f('ix_categories_parent_id'), 'categories', ['parent_id'], unique=False)
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=True)
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)
    op.create_index(op.f('ix_categories_sort_order'), 'categories', ['sort_order'], unique=False)
    op.create_index(op.f('ix_categories_is_active'), 'categories', ['is_active'], unique=False)

    # 2. collections table
    op.create_table(
        'collections',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=1024), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_collections')),
        sa.UniqueConstraint('name', name=op.f('uq_collections_name')),
        sa.UniqueConstraint('slug', name=op.f('uq_collections_slug')),
    )
    op.create_index(op.f('ix_collections_id'), 'collections', ['id'], unique=False)
    op.create_index(op.f('ix_collections_name'), 'collections', ['name'], unique=True)
    op.create_index(op.f('ix_collections_slug'), 'collections', ['slug'], unique=True)
    op.create_index(op.f('ix_collections_sort_order'), 'collections', ['sort_order'], unique=False)
    op.create_index(op.f('ix_collections_is_active'), 'collections', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_collections_is_active'), table_name='collections')
    op.drop_index(op.f('ix_collections_sort_order'), table_name='collections')
    op.drop_index(op.f('ix_collections_slug'), table_name='collections')
    op.drop_index(op.f('ix_collections_name'), table_name='collections')
    op.drop_index(op.f('ix_collections_id'), table_name='collections')
    op.drop_table('collections')

    op.drop_index(op.f('ix_categories_is_active'), table_name='categories')
    op.drop_index(op.f('ix_categories_sort_order'), table_name='categories')
    op.drop_index(op.f('ix_categories_slug'), table_name='categories')
    op.drop_index(op.f('ix_categories_name'), table_name='categories')
    op.drop_index(op.f('ix_categories_parent_id'), table_name='categories')
    op.drop_index(op.f('ix_categories_id'), table_name='categories')
    op.drop_table('categories')
