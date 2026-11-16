"""create_returns_and_return_items_tables

Revision ID: eb3475f7833b
Revises: 71ea9085ba8d
Create Date: 2026-11-11 12:14:44.821903

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb3475f7833b'
down_revision: Union[str, Sequence[str], None] = '71ea9085ba8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create return_requests table
    op.create_table(
        "return_requests",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("request_number", sa.String(64), nullable=False, unique=True),
        sa.Column("order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_type", sa.String(32), nullable=False, server_default="return"),
        sa.Column("status", sa.String(32), nullable=False, server_default="requested"),
        sa.Column("resolution_type", sa.String(32), nullable=False, server_default="refund"),
        sa.Column("refund_payout_method", sa.String(32), nullable=True),
        sa.Column("payout_account_details", sa.Text(), nullable=True),
        sa.Column("customer_notes", sa.Text(), nullable=True),
        sa.Column("staff_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("refund_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("refunds.id", ondelete="SET NULL"), nullable=True),
        sa.Column("replacement_order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("total_refund_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("reviewed_by_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_return_requests_request_number", "return_requests", ["request_number"])
    op.create_index("ix_return_requests_order_id", "return_requests", ["order_id"])
    op.create_index("ix_return_requests_user_id", "return_requests", ["user_id"])
    op.create_index("ix_return_requests_request_type", "return_requests", ["request_type"])
    op.create_index("ix_return_requests_status", "return_requests", ["status"])
    op.create_index("ix_return_requests_refund_id", "return_requests", ["refund_id"])
    op.create_index("ix_return_requests_replacement_order_id", "return_requests", ["replacement_order_id"])
    op.create_index("ix_return_requests_created_at", "return_requests", ["created_at"])

    # 2. Create return_items table
    op.create_table(
        "return_items",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("return_request_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("return_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("customer_comments", sa.String(500), nullable=True),
        sa.Column("exchange_variant_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("exchange_size", sa.String(32), nullable=True),
        sa.Column("exchange_color", sa.String(64), nullable=True),
        sa.Column("inspection_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("restock_condition", sa.String(32), nullable=True),
        sa.Column("restock_action", sa.String(32), nullable=True),
        sa.Column("restocked_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inspector_notes", sa.String(500), nullable=True),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("product_name_snapshot", sa.String(255), nullable=False),
        sa.Column("sku_snapshot", sa.String(64), nullable=False),
        sa.Column("size_snapshot", sa.String(32), nullable=False),
        sa.Column("color_snapshot", sa.String(64), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
    )
    op.create_index("ix_return_items_return_request_id", "return_items", ["return_request_id"])
    op.create_index("ix_return_items_order_item_id", "return_items", ["order_item_id"])
    op.create_index("ix_return_items_exchange_variant_id", "return_items", ["exchange_variant_id"])
    op.create_index("ix_return_items_inspection_status", "return_items", ["inspection_status"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("return_items")
    op.drop_table("return_requests")
