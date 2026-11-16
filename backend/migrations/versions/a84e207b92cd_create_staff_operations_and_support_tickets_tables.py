"""create_staff_operations_and_support_tickets_tables

Revision ID: a84e207b92cd
Revises: 9f41b238d81c
Create Date: 2026-11-11 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a84e207b92cd'
down_revision: Union[str, Sequence[str], None] = '9f41b238d81c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # 1. Create staff_profiles
    op.create_table(
        "staff_profiles",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("employee_code", sa.String(32), nullable=False, unique=True),
        sa.Column("department", sa.String(64), nullable=False, server_default="operations"),
        sa.Column("job_title", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_staff_profiles_user_id", "staff_profiles", ["user_id"])
    op.create_index("ix_staff_profiles_employee_code", "staff_profiles", ["employee_code"])
    op.create_index("ix_staff_profiles_department", "staff_profiles", ["department"])

    # 2. Create support_tickets
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ticket_number", sa.String(64), nullable=False, unique=True),
        sa.Column("customer_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="general"),
        sa.Column("priority", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("assigned_staff_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_support_tickets_ticket_number", "support_tickets", ["ticket_number"])
    op.create_index("ix_support_tickets_customer_id", "support_tickets", ["customer_id"])
    op.create_index("ix_support_tickets_customer_email", "support_tickets", ["customer_email"])
    op.create_index("ix_support_tickets_order_id", "support_tickets", ["order_id"])
    op.create_index("ix_support_tickets_category", "support_tickets", ["category"])
    op.create_index("ix_support_tickets_priority", "support_tickets", ["priority"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index("ix_support_tickets_assigned_staff_id", "support_tickets", ["assigned_staff_id"])

    # 3. Create support_ticket_messages
    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sender_type", sa.String(32), nullable=False, server_default="staff"),
        sa.Column("sender_name", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_internal_note", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"])
    op.create_index("ix_support_ticket_messages_sender_user_id", "support_ticket_messages", ["sender_user_id"])

    # 4. Create staff_tasks
    op.create_table(
        "staff_tasks",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("task_number", sa.String(64), nullable=False, unique=True),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("assigned_staff_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shipment_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("return_request_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("return_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("support_ticket_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey("support_tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_staff_tasks_task_number", "staff_tasks", ["task_number"])
    op.create_index("ix_staff_tasks_task_type", "staff_tasks", ["task_type"])
    op.create_index("ix_staff_tasks_status", "staff_tasks", ["status"])
    op.create_index("ix_staff_tasks_priority", "staff_tasks", ["priority"])
    op.create_index("ix_staff_tasks_assigned_staff_id", "staff_tasks", ["assigned_staff_id"])
    op.create_index("ix_staff_tasks_created_by_user_id", "staff_tasks", ["created_by_user_id"])


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index("ix_staff_tasks_created_by_user_id", table_name="staff_tasks")
    op.drop_index("ix_staff_tasks_assigned_staff_id", table_name="staff_tasks")
    op.drop_index("ix_staff_tasks_priority", table_name="staff_tasks")
    op.drop_index("ix_staff_tasks_status", table_name="staff_tasks")
    op.drop_index("ix_staff_tasks_task_type", table_name="staff_tasks")
    op.drop_index("ix_staff_tasks_task_number", table_name="staff_tasks")
    op.drop_table("staff_tasks")

    op.drop_index("ix_support_ticket_messages_sender_user_id", table_name="support_ticket_messages")
    op.drop_index("ix_support_ticket_messages_ticket_id", table_name="support_ticket_messages")
    op.drop_table("support_ticket_messages")

    op.drop_index("ix_support_tickets_assigned_staff_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_priority", table_name="support_tickets")
    op.drop_index("ix_support_tickets_category", table_name="support_tickets")
    op.drop_index("ix_support_tickets_order_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_customer_email", table_name="support_tickets")
    op.drop_index("ix_support_tickets_customer_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_ticket_number", table_name="support_tickets")
    op.drop_table("support_tickets")

    op.drop_index("ix_staff_profiles_department", table_name="staff_profiles")
    op.drop_index("ix_staff_profiles_employee_code", table_name="staff_profiles")
    op.drop_index("ix_staff_profiles_user_id", table_name="staff_profiles")
    op.drop_table("staff_profiles")
