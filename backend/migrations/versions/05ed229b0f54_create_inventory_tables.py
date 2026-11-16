"""create_inventory_tables

Revision ID: 05ed229b0f54
Revises: eb987fbddf47
Create Date: 2026-11-10 21:31:05.066727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05ed229b0f54'
down_revision: Union[str, Sequence[str], None] = 'eb987fbddf47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. inventory_locations table
    op.create_table(
        'inventory_locations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False, comment='Facility display name'),
        sa.Column('code', sa.String(length=64), nullable=False, comment='Unique facility code'),
        sa.Column('address_line_1', sa.String(length=255), nullable=True, comment='Street address'),
        sa.Column('city', sa.String(length=128), nullable=True, comment='Facility city'),
        sa.Column('postal_code', sa.String(length=32), nullable=True, comment='Postal code'),
        sa.Column('country_code', sa.String(length=2), server_default='PK', nullable=False, comment='ISO country code'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False, comment='Active toggle'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inventory_locations_code'), 'inventory_locations', ['code'], unique=True)
    op.create_index(op.f('ix_inventory_locations_is_active'), 'inventory_locations', ['is_active'], unique=False)

    # 2. inventory_items table
    op.create_table(
        'inventory_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('variant_id', sa.BigInteger(), nullable=False, comment='Foreign key to product variant'),
        sa.Column('location_id', sa.BigInteger(), nullable=False, comment='Foreign key to warehouse location'),
        sa.Column('quantity_on_hand', sa.Integer(), server_default='0', nullable=False, comment='Physical units in facility'),
        sa.Column('quantity_reserved', sa.Integer(), server_default='0', nullable=False, comment='Reserved for checkouts'),
        sa.Column('reorder_threshold', sa.Integer(), server_default='5', nullable=False, comment='Replenishment threshold'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['inventory_locations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('variant_id', 'location_id', name='uq_inventory_items_variant_location'),
    )
    op.create_index(op.f('ix_inventory_items_variant_id'), 'inventory_items', ['variant_id'], unique=False)
    op.create_index(op.f('ix_inventory_items_location_id'), 'inventory_items', ['location_id'], unique=False)

    # 3. inventory_movements table
    op.create_table(
        'inventory_movements',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('variant_id', sa.BigInteger(), nullable=False, comment='Foreign key to affected variant'),
        sa.Column('location_id', sa.BigInteger(), nullable=False, comment='Foreign key to affected location'),
        sa.Column('movement_type', sa.String(length=32), nullable=False, comment='Classification of movement'),
        sa.Column('quantity_delta', sa.Integer(), nullable=False, comment='Signed delta'),
        sa.Column('quantity_on_hand_before', sa.Integer(), nullable=False),
        sa.Column('quantity_on_hand_after', sa.Integer(), nullable=False),
        sa.Column('quantity_reserved_before', sa.Integer(), nullable=False),
        sa.Column('quantity_reserved_after', sa.Integer(), nullable=False),
        sa.Column('reference_type', sa.String(length=64), nullable=True),
        sa.Column('reference_id', sa.String(length=64), nullable=True),
        sa.Column('reason_notes', sa.String(length=255), nullable=True),
        sa.Column('created_by_user_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['location_id'], ['inventory_locations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inventory_movements_variant_id'), 'inventory_movements', ['variant_id'], unique=False)
    op.create_index(op.f('ix_inventory_movements_location_id'), 'inventory_movements', ['location_id'], unique=False)
    op.create_index(op.f('ix_inventory_movements_movement_type'), 'inventory_movements', ['movement_type'], unique=False)
    op.create_index(op.f('ix_inventory_movements_created_by_user_id'), 'inventory_movements', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_inventory_movements_created_at'), 'inventory_movements', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('inventory_movements')
    op.drop_table('inventory_items')
    op.drop_table('inventory_locations')
