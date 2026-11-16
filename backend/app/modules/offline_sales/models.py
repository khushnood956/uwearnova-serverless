"""
Offline Sales Domain Models
Tracks in-store walk-in purchases, cash/card register payments, line items, and audit details.
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


class OfflineSale(Base, IDMixin, TimestampMixin):
    """
    Primary physical storefront transaction record.
    Represents an over-the-counter walk-in sale at a physical shop or boutique.
    """

    __tablename__ = "offline_sales"

    receipt_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique physical receipt / invoice number (e.g. POS-20261112-7A8B)",
    )

    sale_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        comment="Timestamp when transaction was rung up",
    )

    customer_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Walk-in client name if provided",
    )

    customer_phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="Contact phone for SMS receipt or loyalty",
    )

    customer_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional email for e-receipt",
    )

    payment_method: Mapped[str] = mapped_column(
        String(32),
        default="cash",
        nullable=False,
        comment="Tender type: cash, pos_card, bank_transfer, split",
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Pre-discount sum of line items in PKR",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="In-store manual discount or promotion reduction",
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Sales tax or VAT if applicable",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Final payable tender in PKR",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="completed",
        nullable=False,
        index=True,
        comment="Transaction state: completed, voided, refunded",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Cashier notes (e.g. register number, VIP walk-in, exchange note)",
    )

    staff_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID of cashier or store manager ringing up sale",
    )

    staff_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Snapshot of staff/cashier name at sale time",
    )

    # Relationships
    items: Mapped[List["OfflineSaleItem"]] = relationship(
        "OfflineSaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OfflineSaleItem.id",
    )


class OfflineSaleItem(Base, IDMixin, TimestampMixin):
    """
    Individual SKU line item within an offline shop transaction.
    """

    __tablename__ = "offline_sale_items"

    sale_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("offline_sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent offline sale record",
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Product catalogue reference",
    )

    variant_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Product variant SKU reference",
    )

    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Snapshot of product title at time of sale",
    )

    sku: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Snapshot of SKU code",
    )

    variant_label: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Formatted size & color (e.g. Size: M | Color: Crimson Red)",
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Selling price per unit in PKR",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Units sold in this line",
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="unit_price * quantity in PKR",
    )

    # Relationships
    sale: Mapped["OfflineSale"] = relationship(
        "OfflineSale",
        back_populates="items",
    )
