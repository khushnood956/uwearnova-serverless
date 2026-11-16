"""
Staff Operations, Support Tickets, and Task Assignment Domain Models (Module M20)
Defines staff profiles, role-filtered work queues, operational task assignments,
and customer support case workflows.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.fulfillment.models import Shipment
    from app.modules.orders.models import Order
    from app.modules.returns.models import ReturnRequest


class StaffProfile(Base, IDMixin, TimestampMixin):
    """
    Operational staff profile linked 1:1 to a User account with user_type='staff'.
    Tracks employee code, departmental affiliation, operational role, and active status.
    """

    __tablename__ = "staff_profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
        comment="Associated staff user ID",
    )

    employee_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique employee identifier (e.g. EMP-1042)",
    )

    department: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="operations",
        index=True,
        comment="Department: operations, fulfillment, inventory, support, merchandising, finance",
    )

    job_title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Job title (e.g. Fulfillment Specialist, Order Manager, Support Concierge)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the staff member is currently active and eligible for assignments",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="staff_profile")


class SupportTicket(Base, IDMixin, TimestampMixin):
    """
    Customer support case inquiry and issue tracking.
    Enables Customer Support staff to manage customer communications, inquiries, and complaints.
    """

    __tablename__ = "support_tickets"

    ticket_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Human-readable support reference (e.g. TKT-20261111-849201)",
    )

    customer_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated customer user ID if registered",
    )

    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Customer email address",
    )

    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Customer full name",
    )

    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional related order",
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Ticket subject/summary",
    )

    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="general",
        index=True,
        comment="Category: order_inquiry, fulfillment, return_exchange, sizing_styling, payment_issue, complaint, general",
    )

    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="normal",
        index=True,
        comment="Priority: low, normal, high, urgent",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
        index=True,
        comment="Status: open, in_progress, waiting_customer, resolved, closed",
    )

    assigned_staff_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Staff user assigned to this ticket",
    )

    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when ticket was assigned to staff",
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when ticket was resolved",
    )

    # Relationships
    messages: Mapped[List["SupportTicketMessage"]] = relationship(
        "SupportTicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportTicketMessage.created_at",
    )
    assigned_staff: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_staff_id],
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[order_id],
    )


class SupportTicketMessage(Base, IDMixin):
    """
    Chronological conversation thread message in a support ticket.
    Supports customer replies, staff responses, and private internal notes.
    """

    __tablename__ = "support_ticket_messages"

    ticket_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent support ticket ID",
    )

    sender_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Sender user ID (null for guest customer)",
    )

    sender_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="staff",
        comment="Sender type: staff, customer, system",
    )

    sender_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Name of person or system sending message",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Message body content",
    )

    is_internal_note: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="If true, note is visible only to staff, never shown to customer",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Message creation timestamp",
    )

    # Relationships
    ticket: Mapped["SupportTicket"] = relationship(
        "SupportTicket",
        back_populates="messages",
    )


class StaffTask(Base, IDMixin, TimestampMixin):
    """
    Actionable operational work item assigned to staff.
    Used for task assignment in order fulfillment, warehouse packing, inventory cycle counting, etc.
    """

    __tablename__ = "staff_tasks"

    task_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique task reference (e.g. TSK-20261111-829104)",
    )

    task_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Task type: order_processing, fulfillment_pack, fulfillment_dispatch, inventory_cycle_count, return_inspection, customer_support, general",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Brief description of task to execute",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed instructions or specifications",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
        comment="Status: pending, in_progress, completed, cancelled",
    )

    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="normal",
        index=True,
        comment="Priority: low, normal, high, urgent",
    )

    assigned_staff_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Assigned staff member ID",
    )

    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Staff or admin who created the task",
    )

    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated order if applicable",
    )

    shipment_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("shipments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated shipment if applicable",
    )

    return_request_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("return_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated return request if applicable",
    )

    support_ticket_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("support_tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated support ticket if applicable",
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Target deadline for task completion",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when task was completed",
    )

    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Closing remarks, findings, or operational report",
    )

    # Relationships
    assigned_staff: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_staff_id],
    )
