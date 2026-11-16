"""create_customer_profiles_and_addresses_tables

Revision ID: 9f41b238d81c
Revises: eb3475f7833b
Create Date: 2026-11-11 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f41b238d81c'
down_revision: Union[str, Sequence[str], None] = 'eb3475f7833b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # 1. Create customer_profiles table
    op.create_table(
        "customer_profiles",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("first_name", sa.String(64), nullable=True),
        sa.Column("last_name", sa.String(64), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(16), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("marketing_email_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marketing_sms_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marketing_whatsapp_opt_in", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preferred_currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("preferred_language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_customer_profiles_user_id", "customer_profiles", ["user_id"])

    # 2. Create addresses table
    op.create_table(
        "addresses",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_name", sa.String(128), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("address_line_1", sa.String(255), nullable=False),
        sa.Column("address_line_2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(128), nullable=False),
        sa.Column("area", sa.String(128), nullable=True),
        sa.Column("postal_code", sa.String(32), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=False, server_default="PK"),
        sa.Column("label", sa.String(64), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"])
    op.create_index("ix_addresses_city", "addresses", ["city"])
    op.create_index("ix_addresses_is_default", "addresses", ["is_default"])


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index("ix_addresses_is_default", table_name="addresses")
    op.drop_index("ix_addresses_city", table_name="addresses")
    op.drop_index("ix_addresses_user_id", table_name="addresses")
    op.drop_table("addresses")

    op.drop_index("ix_customer_profiles_user_id", table_name="customer_profiles")
    op.drop_table("customer_profiles")
