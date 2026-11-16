"""create_fulfillment_and_shipment_tables

Revision ID: 71ea9085ba8d
Revises: 073a8073cb18
Create Date: 2026-11-11 09:57:02.206811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71ea9085ba8d'
down_revision: Union[str, Sequence[str], None] = '073a8073cb18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create shipments table
    op.create_table(
        "shipments",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("shipment_number", sa.String(64), nullable=False, unique=True),
        sa.Column("order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("courier_code", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("courier_name", sa.String(128), nullable=False, server_default="Direct Logistics Partner"),
        sa.Column("tracking_number", sa.String(128), nullable=True),
        sa.Column("tracking_url", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="allocated"),
        sa.Column("shipping_method_code", sa.String(64), nullable=False, server_default="standard_delivery"),
        sa.Column("shipping_address_snapshot", sa.Text(), nullable=False),
        sa.Column("destination_city", sa.String(128), nullable=False),
        sa.Column("total_weight_grams", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("package_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cod_amount_to_collect", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("dispatch_notes", sa.Text(), nullable=True),
        sa.Column("allocated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("packed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_shipments_shipment_number", "shipments", ["shipment_number"])
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"])
    op.create_index("ix_shipments_courier_code", "shipments", ["courier_code"])
    op.create_index("ix_shipments_tracking_number", "shipments", ["tracking_number"])
    op.create_index("ix_shipments_status", "shipments", ["status"])
    op.create_index("ix_shipments_destination_city", "shipments", ["destination_city"])
    op.create_index("ix_shipments_created_at", "shipments", ["created_at"])

    # 2. Create shipment_items table
    op.create_table(
        "shipment_items",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("shipment_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("product_name_snapshot", sa.String(255), nullable=False),
        sa.Column("sku_snapshot", sa.String(64), nullable=False),
        sa.Column("size_snapshot", sa.String(32), nullable=False),
        sa.Column("color_snapshot", sa.String(64), nullable=False),
    )
    op.create_index("ix_shipment_items_shipment_id", "shipment_items", ["shipment_id"])
    op.create_index("ix_shipment_items_order_item_id", "shipment_items", ["order_item_id"])
    op.create_index("ix_shipment_items_sku_snapshot", "shipment_items", ["sku_snapshot"])

    # 3. Create shipment_events table
    op.create_table(
        "shipment_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("shipment_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("location", sa.String(128), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="staff"),
        sa.Column("recorded_by_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_shipment_events_shipment_id", "shipment_events", ["shipment_id"])
    op.create_index("ix_shipment_events_status", "shipment_events", ["status"])
    op.create_index("ix_shipment_events_occurred_at", "shipment_events", ["occurred_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("shipment_events")
    op.drop_table("shipment_items")
    op.drop_table("shipments")
