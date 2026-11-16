"""create_promotions_reviews_and_content_tables

Revision ID: b39e318cf142
Revises: a84e207b92cd
Create Date: 2026-11-11 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b39e318cf142'
down_revision: Union[str, Sequence[str], None] = 'a84e207b92cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # 1. Create coupons table
    op.create_table(
        "coupons",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("discount_type", sa.String(32), nullable=False, server_default="percentage"),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_discount_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_order_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("usage_limit_total", sa.Integer(), nullable=True),
        sa.Column("usage_limit_per_customer", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("times_redeemed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_coupons_code", "coupons", ["code"])
    op.create_index("ix_coupons_is_active", "coupons", ["is_active"])

    # 2. Create coupon_redemptions table
    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("coupon_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_coupon_redemptions_coupon_id", "coupon_redemptions", ["coupon_id"])
    op.create_index("ix_coupon_redemptions_order_id", "coupon_redemptions", ["order_id"])
    op.create_index("ix_coupon_redemptions_customer_email", "coupon_redemptions", ["customer_email"])

    # 3. Create product_reviews table
    op.create_table(
        "product_reviews",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_name", sa.String(128), nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("is_verified_buyer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("moderated_by_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_product_reviews_product_id", "product_reviews", ["product_id"])
    op.create_index("ix_product_reviews_user_id", "product_reviews", ["user_id"])
    op.create_index("ix_product_reviews_customer_email", "product_reviews", ["customer_email"])
    op.create_index("ix_product_reviews_status", "product_reviews", ["status"])

    # 4. Create announcement_bars table
    op.create_table(
        "announcement_bars",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("message", sa.String(255), nullable=False),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("bg_color", sa.String(32), nullable=False, server_default="#000000"),
        sa.Column("text_color", sa.String(32), nullable=False, server_default="#FFFFFF"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_announcement_bars_is_active", "announcement_bars", ["is_active"])

    # 5. Create homepage_campaigns table
    op.create_table(
        "homepage_campaigns",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subtitle", sa.String(255), nullable=True),
        sa.Column("cta_text", sa.String(64), nullable=True, server_default="Explore Collection"),
        sa.Column("cta_link", sa.String(255), nullable=True, server_default="/collections/women"),
        sa.Column("banner_image_url", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_homepage_campaigns_is_active", "homepage_campaigns", ["is_active"])
    op.create_index("ix_homepage_campaigns_sort_order", "homepage_campaigns", ["sort_order"])

    # 6. Create content_pages table
    op.create_table(
        "content_pages",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("meta_title", sa.String(255), nullable=True),
        sa.Column("meta_description", sa.String(500), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_content_pages_slug", "content_pages", ["slug"])
    op.create_index("ix_content_pages_is_published", "content_pages", ["is_published"])


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index("ix_content_pages_is_published", table_name="content_pages")
    op.drop_index("ix_content_pages_slug", table_name="content_pages")
    op.drop_table("content_pages")

    op.drop_index("ix_homepage_campaigns_sort_order", table_name="homepage_campaigns")
    op.drop_index("ix_homepage_campaigns_is_active", table_name="homepage_campaigns")
    op.drop_table("homepage_campaigns")

    op.drop_index("ix_announcement_bars_is_active", table_name="announcement_bars")
    op.drop_table("announcement_bars")

    op.drop_index("ix_product_reviews_status", table_name="product_reviews")
    op.drop_index("ix_product_reviews_customer_email", table_name="product_reviews")
    op.drop_index("ix_product_reviews_user_id", table_name="product_reviews")
    op.drop_index("ix_product_reviews_product_id", table_name="product_reviews")
    op.drop_table("product_reviews")

    op.drop_index("ix_coupon_redemptions_customer_email", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_order_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_coupon_id", table_name="coupon_redemptions")
    op.drop_table("coupon_redemptions")

    op.drop_index("ix_coupons_is_active", table_name="coupons")
    op.drop_index("ix_coupons_code", table_name="coupons")
    op.drop_table("coupons")
