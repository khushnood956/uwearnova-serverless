"""create_cart_and_wishlist_tables

Revision ID: 79afb81abaa2
Revises: 05ed229b0f54
Create Date: 2026-11-10 21:45:58.069918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79afb81abaa2'
down_revision: Union[str, Sequence[str], None] = '05ed229b0f54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. carts table
    op.create_table(
        'carts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='Associated customer user ID'),
        sa.Column('anonymous_token', sa.String(length=64), nullable=True, comment='Guest session token'),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False, comment='Cart status'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_carts_user_id'), 'carts', ['user_id'], unique=False)
    op.create_index(op.f('ix_carts_anonymous_token'), 'carts', ['anonymous_token'], unique=False)
    op.create_index(op.f('ix_carts_status'), 'carts', ['status'], unique=False)

    # 2. cart_items table
    op.create_table(
        'cart_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('cart_id', sa.BigInteger(), nullable=False, comment='Foreign key to parent cart'),
        sa.Column('variant_id', sa.BigInteger(), nullable=False, comment='Foreign key to product SKU variant'),
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=False, comment='Item quantity'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cart_id', 'variant_id', name='uq_cart_items_cart_variant'),
    )
    op.create_index(op.f('ix_cart_items_cart_id'), 'cart_items', ['cart_id'], unique=False)
    op.create_index(op.f('ix_cart_items_variant_id'), 'cart_items', ['variant_id'], unique=False)

    # 3. wishlists table
    op.create_table(
        'wishlists',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='Foreign key to customer account'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_wishlists_user_id'),
    )
    op.create_index(op.f('ix_wishlists_user_id'), 'wishlists', ['user_id'], unique=True)

    # 4. wishlist_items table
    op.create_table(
        'wishlist_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('wishlist_id', sa.BigInteger(), nullable=False, comment='Foreign key to parent wishlist'),
        sa.Column('product_id', sa.BigInteger(), nullable=False, comment='Foreign key to bookmarked product'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wishlist_id'], ['wishlists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wishlist_id', 'product_id', name='uq_wishlist_items_wishlist_product'),
    )
    op.create_index(op.f('ix_wishlist_items_wishlist_id'), 'wishlist_items', ['wishlist_id'], unique=False)
    op.create_index(op.f('ix_wishlist_items_product_id'), 'wishlist_items', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_table('wishlist_items')
    op.drop_table('wishlists')
    op.drop_table('cart_items')
    op.drop_table('carts')
