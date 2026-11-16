"""
Returns, Exchanges, and Quality Inspection Domain Models (Module M16)
Defines customer return/exchange requests, line-item reasons and quantities,
warehouse garment condition inspection, inventory restock checkpoints, and refund linkages.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
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
    from app.modules.catalog.models import ProductVariant
    from app.modules.orders.models import Order, OrderItem
    from app.modules.payments.models import Refund


class ReturnRequest(Base, IDMixin, TimestampMixin):
    """
    Formal request submitted by a customer or staff for order return or exchange.
    Tracks review decisions, warehouse item arrival, garment inspection, and final financial or exchange resolution.
    """

    __tablename__ = "return_requests"

    request_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable return tracking identifier (e.g. RET-20261111-849201)",
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent order",
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Customer user ID who submitted request (null for guest)",
    )

    request_type: Mapped[str] = mapped_column(
        String(32),
        default="return",
        nullable=False,
        index=True,
        comment="Request nature: return (for monetary/store credit refund) or exchange (for size/color swap)",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="requested",
        nullable=False,
        index=True,
        comment=(
            "State machine: requested, under_review, approved, rejected, "
            "items_received, inspected, completed, cancelled"
        ),
    )

    resolution_type: Mapped[str] = mapped_column(
        String(32),
        default="refund",
        nullable=False,
        comment="Desired resolution: refund, exchange, store_credit",
    )

    refund_payout_method: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Refund rail: original_payment_method, bank_transfer, wallet_transfer, store_credit",
    )

    payout_account_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON snapshot of beneficiary details for manual COD refund (Bank name, Account title, IBAN/JazzCash)",
    )

    customer_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Customer description of issue or sizing feedback",
    )

    staff_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal operational notes by customer support or warehouse team",
    )

    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Documented policy reason if request is declined",
    )

    refund_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("refunds.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Linked financial refund record once payment is reversed",
    )

    replacement_order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Linked zero-total replacement order created upon exchange resolution",
    )

    total_refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Approved total refund monetary amount in PKR",
    )

    # Workflow Milestones & Attribution
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Staff member who approved or rejected the request",
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when review decision was recorded",
    )

    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when returned parcel was received at warehouse",
    )

    inspected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when physical quality inspection was concluded",
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when exchange order was dispatched or refund executed",
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="returns",
        foreign_keys=[order_id],
    )

    items: Mapped[List["ReturnItem"]] = relationship(
        "ReturnItem",
        back_populates="return_request",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReturnItem.id.asc()",
    )

    refund: Mapped[Optional["Refund"]] = relationship("Refund")
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])


class ReturnItem(Base, IDMixin):
    """
    Specific order line item included in a return or exchange request.
    Records return reason, inspection condition, restock action, and exchange target.
    """

    __tablename__ = "return_items"

    return_request_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("return_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent return request",
    )

    order_item_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to original purchased order line item",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of units of this line item being returned or exchanged",
    )

    reason: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Categorized return reason: size_fit, defective_garment, color_mismatch, not_as_described, fabric_feel, changed_mind",
    )

    customer_comments: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Customer commentary for this specific item",
    )

    # Exchange Specific Attributes
    exchange_variant_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Target product variant requested for exchange",
    )

    exchange_size: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Requested replacement garment size",
    )

    exchange_color: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Requested replacement garment color",
    )

    # Warehouse Inspection Tracking
    inspection_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
        comment="Inspection result: pending, passed, failed",
    )

    restock_condition: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Garment condition: unopened, like_new, damaged, altered, missing_tags",
    )

    restock_action: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Action taken: restock_available, write_off, return_to_customer",
    )

    restocked_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of units added back to active available inventory",
    )

    inspector_notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Quality inspector assessment remarks",
    )

    inspected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the item was inspected",
    )

    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Item-specific calculated refund amount in PKR",
    )

    # Historical Product Snapshots (preserved from original purchase)
    product_name_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    sku_snapshot: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    size_snapshot: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    color_snapshot: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # Relationships
    return_request: Mapped["ReturnRequest"] = relationship("ReturnRequest", back_populates="items")
    order_item: Mapped["OrderItem"] = relationship("OrderItem")
    exchange_variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
