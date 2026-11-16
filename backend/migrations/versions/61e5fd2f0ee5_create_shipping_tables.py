"""create_shipping_tables

Revision ID: 61e5fd2f0ee5
Revises: 79afb81abaa2
Create Date: 2026-11-10 21:56:44.069918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61e5fd2f0ee5'
down_revision: Union[str, Sequence[str], None] = '79afb81abaa2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. shipping_zones table
    op.create_table(
        'shipping_zones',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False, comment='Zone display title'),
        sa.Column('code', sa.String(length=64), nullable=False, comment='Unique zone identifier'),
        sa.Column('description', sa.String(length=255), nullable=True, comment='Zone description'),
        sa.Column('cities', sa.Text(), nullable=False, comment='JSON array of serviced cities'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False, comment='Active toggle'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_shipping_zones_code'), 'shipping_zones', ['code'], unique=True)
    op.create_index(op.f('ix_shipping_zones_is_active'), 'shipping_zones', ['is_active'], unique=False)

    # 2. shipping_methods table
    op.create_table(
        'shipping_methods',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('zone_id', sa.BigInteger(), nullable=True, comment='Target zone constraint'),
        sa.Column('name', sa.String(length=128), nullable=False, comment='Service title'),
        sa.Column('code', sa.String(length=64), nullable=False, comment='Unique method code'),
        sa.Column('description', sa.String(length=255), nullable=True, comment='Timeline note'),
        sa.Column('base_fee', sa.Numeric(precision=10, scale=2), server_default='350.00', nullable=False, comment='Base shipping fee'),
        sa.Column('free_shipping_threshold', sa.Numeric(precision=10, scale=2), server_default='15000.00', nullable=True, comment='Free threshold'),
        sa.Column('estimated_days_min', sa.Integer(), server_default='2', nullable=False, comment='Min business days'),
        sa.Column('estimated_days_max', sa.Integer(), server_default='4', nullable=False, comment='Max business days'),
        sa.Column('is_cod_supported', sa.Boolean(), server_default=sa.text('1'), nullable=False, comment='COD accepted'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False, comment='Active toggle'),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='Sort priority'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['zone_id'], ['shipping_zones.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_shipping_methods_code'), 'shipping_methods', ['code'], unique=True)
    op.create_index(op.f('ix_shipping_methods_zone_id'), 'shipping_methods', ['zone_id'], unique=False)
    op.create_index(op.f('ix_shipping_methods_is_active'), 'shipping_methods', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_table('shipping_methods')
    op.drop_table('shipping_zones')
