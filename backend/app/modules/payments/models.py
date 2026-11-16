"""
Payments Domain Models (Module M13)
Defines payment ledger records, COD workflow tracking, payment transaction history,
cash collection tracking, and courier remittance reconciliation.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.orders.models import Order


class Payment(Base, IDMixin, TimestampMixin):
    """
    Payment entity tracking financial transactions for an order.
    Maintains payment status, collection progress, outstanding balance, and settlement.
    """

    __tablename__ = "payments"

    order_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated customer order ID",
    )

    payment_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="cod",
        index=True,
        comment="Payment method key: cod, card, bank_transfer",
    )

    provider_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="cod",
        index=True,
        comment="Provider identifier (cod or online gateway key)",
    )

    provider_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="External tracking/consignment ID or payment gateway charge reference",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
        comment="Payment lifecycle status: pending, confirmed, dispatched, collected, partially_collected, reconciled, failed, cancelled",
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="PKR",
        comment="ISO 4217 three-letter currency identifier",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total order payable monetary amount in PKR",
    )

    amount_collected: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total verified cash or gateway funds collected to date",
    )

    amount_outstanding: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Remaining uncollected balance (amount minus amount_collected)",
    )

    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        comment="When the payment workflow was initiated",
    )

    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When COD order verification was completed",
    )

    dispatched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When parcel was handed over to courier for delivery",
    )

    collected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When cash was collected by courier/rider",
    )

    reconciled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When courier remittance was settled and verified by staff",
    )

    reconciled_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Staff user ID who reconciled the payment",
    )

    settlement_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Courier remittance batch ID or bank deposit voucher reference",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Operational or reconciliation notes",
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="payments")

    transactions: Mapped[List["PaymentTransaction"]] = relationship(
        "PaymentTransaction",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PaymentTransaction.id.asc()",
    )

    events: Mapped[List["PaymentEvent"]] = relationship(
        "PaymentEvent",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PaymentEvent.id.asc()",
    )

    refunds: Mapped[List["Refund"]] = relationship(
        "Refund",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Refund.id.asc()",
    )

    reconciled_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reconciled_by_user_id],
    )


class PaymentTransaction(Base, IDMixin):
    """
    Immutable audit history of all payment events, collections, and reconciliations.
    """

    __tablename__ = "payment_transactions"

    payment_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent payment ID",
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent order ID",
    )

    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Event action: initiated, confirmed, dispatched, collected, partially_collected, reconciled, failed, cancelled",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Incremental monetary value involved in this transaction event",
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="PKR",
    )

    collected_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Name of collecting party, courier agent, or payment provider",
    )

    reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Consignment tracking number, bank deposit reference, or settlement voucher #",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Operational details or notes",
    )

    recorded_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Staff user who recorded this event",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="transactions")
    recorded_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[recorded_by_user_id],
    )


class PaymentEvent(Base, IDMixin):
    """
    Audit log of incoming gateway webhook callbacks and notifications.
    Supports signature validation, payload inspection, and idempotent deduplication.
    """

    __tablename__ = "payment_events"

    payment_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated payment record if resolved",
    )

    provider_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Provider key (e.g. mock, safepay, payfast, jazzcash)",
    )

    provider_event_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Unique event identifier from the payment provider for deduplication",
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Gateway event identifier (e.g. payment.succeeded, payment.failed)",
    )

    signature_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the cryptographic webhook signature was validated",
    )

    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Sanitized / redacted raw JSON callback payload",
    )

    processing_status: Mapped[str] = mapped_column(
        String(32),
        default="received",
        nullable=False,
        index=True,
        comment="Processing status: received, processed, duplicate, failed, ignored",
    )

    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when webhook processing completed",
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error explanation if processing failed",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    payment: Mapped[Optional["Payment"]] = relationship("Payment", back_populates="events")


class Refund(Base, IDMixin):
    """
    Customer refund record tracking requested, approved, and completed refunds.
    """

    __tablename__ = "refunds"

    order_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated order ID",
    )

    payment_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated payment ID",
    )

    refund_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique refund reference code (e.g. RFD-20261111-123456)",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Refund monetary amount in PKR",
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        default="PKR",
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Operational reason for refund",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
        comment="Status: pending, completed, failed",
    )

    provider_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Gateway refund transaction ID",
    )

    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Staff user who created the refund",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Audit or accounting notes",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when refund was confirmed settled",
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    payment: Mapped["Payment"] = relationship("Payment", back_populates="refunds")
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )
