"""create_payment_events_and_refunds_tables

Revision ID: 073a8073cb18
Revises: 16d42444d379
Create Date: 2026-11-11 09:39:47.459992

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '073a8073cb18'
down_revision: Union[str, Sequence[str], None] = '16d42444d379'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create payment_events table
    op.create_table(
        "payment_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("payment_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_code", sa.String(64), nullable=False),
        sa.Column("provider_event_id", sa.String(255), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payment_events_payment_id", "payment_events", ["payment_id"])
    op.create_index("ix_payment_events_provider_code", "payment_events", ["provider_code"])
    op.create_index("ix_payment_events_provider_event_id", "payment_events", ["provider_event_id"])
    op.create_index("ix_payment_events_event_type", "payment_events", ["event_type"])
    op.create_index("ix_payment_events_processing_status", "payment_events", ["processing_status"])
    op.create_index("ix_payment_events_created_at", "payment_events", ["created_at"])

    # 2. Create refunds table
    op.create_table(
        "refunds",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refund_number", sa.String(64), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_refunds_order_id", "refunds", ["order_id"])
    op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"])
    op.create_index("ix_refunds_refund_number", "refunds", ["refund_number"])
    op.create_index("ix_refunds_status", "refunds", ["status"])
    op.create_index("ix_refunds_provider_reference", "refunds", ["provider_reference"])
    op.create_index("ix_refunds_created_by_user_id", "refunds", ["created_by_user_id"])
    op.create_index("ix_refunds_created_at", "refunds", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("refunds")
    op.drop_table("payment_events")
