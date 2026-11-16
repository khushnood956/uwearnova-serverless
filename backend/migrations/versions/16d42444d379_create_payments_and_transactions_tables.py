"""create_payments_and_transactions_tables

Revision ID: 16d42444d379
Revises: cdade44decfd
Create Date: 2026-11-10 23:01:58.156489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16d42444d379'
down_revision: Union[str, Sequence[str], None] = 'cdade44decfd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create payments table
    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_method", sa.String(32), nullable=False, server_default="cod"),
        sa.Column("provider_code", sa.String(64), nullable=False, server_default="cod"),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount_collected", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("amount_outstanding", sa.Numeric(10, 2), nullable=False),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled_by_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("settlement_reference", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    op.create_index("ix_payments_payment_method", "payments", ["payment_method"])
    op.create_index("ix_payments_provider_code", "payments", ["provider_code"])
    op.create_index("ix_payments_provider_reference", "payments", ["provider_reference"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_reconciled_by_user_id", "payments", ["reconciled_by_user_id"])
    op.create_index("ix_payments_settlement_reference", "payments", ["settlement_reference"])

    # 2. Create payment_transactions table
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("payment_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("collected_by", sa.String(128), nullable=True),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payment_transactions_payment_id", "payment_transactions", ["payment_id"])
    op.create_index("ix_payment_transactions_order_id", "payment_transactions", ["order_id"])
    op.create_index("ix_payment_transactions_action", "payment_transactions", ["action"])
    op.create_index("ix_payment_transactions_recorded_by_user_id", "payment_transactions", ["recorded_by_user_id"])
    op.create_index("ix_payment_transactions_created_at", "payment_transactions", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("payment_transactions")
    op.drop_table("payments")
