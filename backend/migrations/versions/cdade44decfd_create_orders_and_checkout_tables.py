"""create_orders_and_checkout_tables

Revision ID: cdade44decfd
Revises: 61e5fd2f0ee5
Create Date: 2026-11-10 22:43:29.069918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdade44decfd'
down_revision: Union[str, Sequence[str], None] = '61e5fd2f0ee5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_number', sa.String(length=64), nullable=False, comment='Unique order reference'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='Associated customer ID'),
        sa.Column('customer_email', sa.String(length=255), nullable=False, comment='Customer email'),
        sa.Column('customer_phone', sa.String(length=32), nullable=False, comment='Customer phone'),
        sa.Column('customer_name', sa.String(length=128), nullable=False, comment='Recipient name'),
        sa.Column('status', sa.String(length=32), server_default='pending_confirmation', nullable=False, comment='Order state'),
        sa.Column('payment_status', sa.String(length=32), server_default='unpaid', nullable=False, comment='Payment state'),
        sa.Column('fulfillment_status', sa.String(length=32), server_default='unfulfilled', nullable=False, comment='Fulfillment state'),
        sa.Column('payment_method', sa.String(length=32), server_default='cod', nullable=False, comment='Payment method'),
        sa.Column('currency_code', sa.String(length=3), server_default='PKR', nullable=False, comment='Currency'),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False, comment='Subtotal'),
        sa.Column('discount_total', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False),
        sa.Column('shipping_total', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_total', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False),
        sa.Column('grand_total', sa.Numeric(precision=10, scale=2), nullable=False, comment='Final payable total'),
        sa.Column('shipping_method_code', sa.String(length=64), nullable=False),
        sa.Column('shipping_method_name', sa.String(length=128), nullable=False),
        sa.Column('shipping_address_snapshot', sa.Text(), nullable=False),
        sa.Column('billing_address_snapshot', sa.Text(), nullable=True),
        sa.Column('customer_note', sa.String(length=500), nullable=True),
        sa.Column('placed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_orders_order_number'), 'orders', ['order_number'], unique=True)
    op.create_index(op.f('ix_orders_user_id'), 'orders', ['user_id'], unique=False)
    op.create_index(op.f('ix_orders_customer_email'), 'orders', ['customer_email'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index(op.f('ix_orders_payment_status'), 'orders', ['payment_status'], unique=False)
    op.create_index(op.f('ix_orders_fulfillment_status'), 'orders', ['fulfillment_status'], unique=False)
    op.create_index(op.f('ix_orders_placed_at'), 'orders', ['placed_at'], unique=False)

    # 2. order_items table
    op.create_table(
        'order_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=True),
        sa.Column('variant_id', sa.BigInteger(), nullable=True),
        sa.Column('product_name_snapshot', sa.String(length=255), nullable=False),
        sa.Column('product_slug_snapshot', sa.String(length=255), nullable=False),
        sa.Column('sku_snapshot', sa.String(length=64), nullable=False),
        sa.Column('size_snapshot', sa.String(length=32), nullable=False),
        sa.Column('color_snapshot', sa.String(length=64), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('line_discount', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False),
        sa.Column('line_total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('image_url_snapshot', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_order_items_order_id'), 'order_items', ['order_id'], unique=False)
    op.create_index(op.f('ix_order_items_sku_snapshot'), 'order_items', ['sku_snapshot'], unique=False)

    # 3. order_status_history table
    op.create_table(
        'order_status_history',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=False),
        sa.Column('from_status', sa.String(length=32), nullable=False),
        sa.Column('to_status', sa.String(length=32), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('changed_by_user_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_order_status_history_order_id'), 'order_status_history', ['order_id'], unique=False)
    op.create_index(op.f('ix_order_status_history_created_at'), 'order_status_history', ['created_at'], unique=False)

    # 4. checkout_idempotency table
    op.create_table(
        'checkout_idempotency',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('request_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=True),
        sa.Column('order_number', sa.String(length=64), nullable=True),
        sa.Column('response_payload', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_checkout_idempotency_idempotency_key'), 'checkout_idempotency', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_checkout_idempotency_request_fingerprint'), 'checkout_idempotency', ['request_fingerprint'], unique=False)
    op.create_index(op.f('ix_checkout_idempotency_expires_at'), 'checkout_idempotency', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_table('checkout_idempotency')
    op.drop_table('order_status_history')
    op.drop_table('order_items')
    op.drop_table('orders')
