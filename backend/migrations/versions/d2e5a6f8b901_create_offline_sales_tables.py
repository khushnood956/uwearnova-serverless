"""create_offline_sales_tables

Revision ID: d2e5a6f8b901
Revises: c10d3e5a7b9f
Create Date: 2026-11-12 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e5a6f8b901'
down_revision: Union[str, Sequence[str], None] = 'c10d3e5a7b9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create offline_sales table
    op.create_table(
        "offline_sales",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("receipt_number", sa.String(64), nullable=False),
        sa.Column("sale_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("customer_name", sa.String(128), nullable=True),
        sa.Column("customer_phone", sa.String(32), nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("payment_method", sa.String(32), server_default="cash", nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(10, 2), server_default="0.00", nullable=False),
        sa.Column("tax_amount", sa.Numeric(10, 2), server_default="0.00", nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(32), server_default="completed", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("staff_id", sa.BigInteger(), nullable=True),
        sa.Column("staff_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["staff_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_number"),
    )
    op.create_index("ix_offline_sales_receipt_number", "offline_sales", ["receipt_number"])
    op.create_index("ix_offline_sales_sale_date", "offline_sales", ["sale_date"])
    op.create_index("ix_offline_sales_customer_phone", "offline_sales", ["customer_phone"])
    op.create_index("ix_offline_sales_status", "offline_sales", ["status"])

    # 2. Create offline_sale_items table
    op.create_table(
        "offline_sale_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sale_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("variant_id", sa.BigInteger(), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("variant_label", sa.String(128), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sale_id"], ["offline_sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offline_sale_items_sale_id", "offline_sale_items", ["sale_id"])
    op.create_index("ix_offline_sale_items_product_id", "offline_sale_items", ["product_id"])
    op.create_index("ix_offline_sale_items_variant_id", "offline_sale_items", ["variant_id"])


def downgrade() -> None:
    op.drop_table("offline_sale_items")
    op.drop_table("offline_sales")
