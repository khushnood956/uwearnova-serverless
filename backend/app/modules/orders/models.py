"""
Order and Checkout Domain Models (M12)
Defines immutable order headers, purchased line items with product snapshots,
order status audit history, and checkout idempotency records.
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
    from app.modules.catalog.models import Product, ProductVariant
    from app.modules.fulfillment.models import Shipment
    from app.modules.payments.models import Payment
    from app.modules.returns.models import ReturnRequest


class Order(Base, IDMixin, TimestampMixin):
    """
    Customer purchase order header.
    Stores immutable billing and shipping snapshots, financial totals, and lifecycle states.
    """

    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable unique order identifier (e.g. UNV-20261110-847291)",
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated customer user ID (null for guest checkout)",
    )

    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Customer contact email",
    )

    customer_phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Customer contact mobile phone",
    )

    customer_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Recipient full name",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending_confirmation",
        nullable=False,
        index=True,
        comment="Order state: pending_confirmation, confirmed, processing, packed, shipped, delivered, cancelled, return_requested, returned, refunded",
    )

    payment_status: Mapped[str] = mapped_column(
        String(32),
        default="unpaid",
        nullable=False,
        index=True,
        comment="Payment state: unpaid, authorized, paid, refunded, failed",
    )

    fulfillment_status: Mapped[str] = mapped_column(
        String(32),
        default="unfulfilled",
        nullable=False,
        index=True,
        comment="Fulfillment state: unfulfilled, partially_fulfilled, fulfilled, cancelled",
    )

    payment_method: Mapped[str] = mapped_column(
        String(32),
        default="cod",
        nullable=False,
        comment="Payment method key: cod, card, bank_transfer",
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        default="PKR",
        nullable=False,
        comment="Three-letter ISO currency code",
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total of line items before discounts and shipping",
    )

    discount_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Applied promotion or coupon discount in PKR",
    )

    shipping_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Calculated delivery freight charges in PKR",
    )

    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Tax total in PKR",
    )

    grand_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Final payable order amount in PKR",
    )

    shipping_method_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Selected shipping method code",
    )

    shipping_method_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Selected shipping method title",
    )

    shipping_address_snapshot: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON-serialized snapshot of delivery address at checkout time",
    )

    billing_address_snapshot: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialized snapshot of billing address at checkout time",
    )

    customer_note: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Customer delivery notes or gate instructions",
    )

    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        comment="Order placement timestamp",
    )

    # Relationships
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OrderItem.id.asc()",
    )

    status_history: Mapped[List["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OrderStatusHistory.created_at.asc()",
    )

    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Payment.id.asc()",
    )

    shipments: Mapped[List["Shipment"]] = relationship(
        "Shipment",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Shipment.id.asc()",
    )

    returns: Mapped[List["ReturnRequest"]] = relationship(
        "ReturnRequest",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReturnRequest.id.asc()",
        primaryjoin="Order.id == ReturnRequest.order_id",
    )

    user: Mapped[Optional["User"]] = relationship("User")


class OrderItem(Base, IDMixin):
    """
    Immutable line item snapshot preserving garment title, size, color,
    and purchase price regardless of future catalogue changes.
    """

    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent order",
    )

    product_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional reference to live catalog product",
    )

    variant_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional reference to live catalog variant",
    )

    product_name_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Product title at time of order creation",
    )

    product_slug_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Product slug at time of order creation",
    )

    sku_snapshot: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Garment SKU at time of order creation",
    )

    size_snapshot: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Size selected at purchase",
    )

    color_snapshot: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Color description at purchase",
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Agreed item unit price at purchase in PKR",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Purchased item unit count",
    )

    line_discount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Line-specific discount",
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Unit price times quantity minus line discount",
    )

    image_url_snapshot: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="Thumbnail image URL at time of purchase",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )

    product: Mapped[Optional["Product"]] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")


class OrderStatusHistory(Base, IDMixin):
    """
    Immutable state machine transition ledger for order processing.
    """

    __tablename__ = "order_status_history"

    order_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to affected order",
    )

    from_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Previous order lifecycle state",
    )

    to_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="New order lifecycle state",
    )

    note: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Operator note or automated system event explanation",
    )

    changed_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Staff member or system actor initiating the status transition",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        comment="Timestamp when transition occurred",
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="status_history",
    )

    changed_by_user: Mapped[Optional["User"]] = relationship("User")


class CheckoutIdempotency(Base, IDMixin):
    """
    Guarantees duplicate checkout requests do not produce duplicate orders or double-billing.
    Stores cryptographic request fingerprints and cached response payloads.
    """

    __tablename__ = "checkout_idempotency"

    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique client or frontend checkout idempotency key",
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Customer account ID if authenticated",
    )

    request_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash of the checkout request body",
    )

    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=True,
        comment="Created order ID resulting from this idempotency key",
    )

    order_number: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Created order number for fast replay",
    )

    response_payload: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Cached JSON response payload returned upon duplicate submission",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Expiry timestamp after which key can be recycled",
    )
