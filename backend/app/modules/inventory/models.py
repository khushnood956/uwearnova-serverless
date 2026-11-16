"""
Inventory Domain Models (M09)
Tracks warehouse locations, physical on-hand stock, reserved stock,
reorder thresholds, and immutable inventory movement audit logs.
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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.catalog.models import ProductVariant


class InventoryLocation(Base, IDMixin, TimestampMixin):
    """
    Fulfillment location or warehouse facility.
    Supports single or multi-facility inventory management.
    """

    __tablename__ = "inventory_locations"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Facility display name (e.g., Primary Fulfillment Center)",
    )

    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique facility code (e.g., KHI-WH-01, WH-PRIMARY)",
    )

    address_line_1: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Street or facility address",
    )

    city: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Facility city",
    )

    postal_code: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Postal / ZIP code",
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        default="PK",
        nullable=False,
        comment="ISO 3166-1 alpha-2 country code",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether the location is actively receiving or fulfilling stock",
    )

    # Relationships
    items: Mapped[List["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="location",
        cascade="all, delete-orphan",
    )


class InventoryItem(Base, IDMixin, TimestampMixin):
    """
    Stock record linking a product variant SKU to an inventory location.
    Tracks quantity on hand, quantity reserved for active checkouts/orders,
    and reorder threshold.
    """

    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("variant_id", "location_id", name="uq_inventory_items_variant_location"),
    )

    variant_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to product SKU variant",
    )

    location_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("inventory_locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to inventory warehouse location",
    )

    quantity_on_hand: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total physical stock units physically present in facility",
    )

    quantity_reserved: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Stock units reserved for active checkouts or pending fulfillment",
    )

    reorder_threshold: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="Threshold at which replenishment alerts are triggered",
    )

    # Relationships
    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant",
        back_populates="inventory_items",
    )

    location: Mapped["InventoryLocation"] = relationship(
        "InventoryLocation",
        back_populates="items",
    )

    @property
    def quantity_available(self) -> int:
        """Available stock ready for purchase: physical on-hand minus active reservations."""
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    @property
    def is_low_stock(self) -> bool:
        """True if available stock is at or below the reorder threshold."""
        return self.quantity_available <= self.reorder_threshold


class InventoryMovement(Base, IDMixin):
    """
    Immutable ledger of every inventory change.
    Never relies solely on mutable stock counts; records complete audit trails.
    """

    __tablename__ = "inventory_movements"

    variant_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to affected product variant",
    )

    location_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("inventory_locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to affected inventory location",
    )

    movement_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Classification: receipt, sale, reservation, release, return, adjustment, cycle_count, damaged",
    )

    quantity_delta: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Signed delta applied to quantity (positive or negative)",
    )

    quantity_on_hand_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Snapshot of physical on-hand before the transaction",
    )

    quantity_on_hand_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Snapshot of physical on-hand after the transaction",
    )

    quantity_reserved_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Snapshot of reserved quantity before the transaction",
    )

    quantity_reserved_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Snapshot of reserved quantity after the transaction",
    )

    reference_type: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Originating reference entity (e.g. manual_adjustment, checkout_hold, order_fulfillment)",
    )

    reference_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="ID or identifier of the originating event or document",
    )

    reason_notes: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Operator note or system explanation for adjustment",
    )

    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Staff member or system actor initiating the stock movement",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        comment="Immutable timestamp when movement occurred",
    )

    # Relationships
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    location: Mapped["InventoryLocation"] = relationship("InventoryLocation")
    created_by_user: Mapped[Optional["User"]] = relationship("User")
