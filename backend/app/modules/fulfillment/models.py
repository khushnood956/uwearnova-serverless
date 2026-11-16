"""
Fulfillment and Shipment Domain Models (Module M15)
Defines shipment records, allocated line items, tracking events,
carrier assignments, and fulfillment lifecycle tracking.
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
    from app.modules.orders.models import Order, OrderItem


class Shipment(Base, IDMixin, TimestampMixin):
    """
    Physical shipment parcel created to fulfill order items.
    Tracks courier carrier, airway bill / consignment number, weight,
    delivery address snapshot, and fulfillment status transitions.
    """

    __tablename__ = "shipments"

    shipment_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable shipment identifier (e.g. SHP-20261111-829104)",
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent order",
    )

    courier_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="manual",
        index=True,
        comment="Carrier provider code: leopards, tcs, trax, call_courier, postex, manual",
    )

    courier_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="Direct Logistics Partner",
        comment="Carrier display name (e.g. TCS Express, Leopards Courier)",
    )

    tracking_number: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Carrier Airway Bill (AWB) or Consignment Note (CN) number",
    )

    tracking_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Direct link to public courier consignment tracking webpage",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="allocated",
        nullable=False,
        index=True,
        comment=(
            "Fulfillment state: allocated, packing, packed, ready_for_pickup, "
            "dispatched, in_transit, out_for_delivery, delivered, delivery_failed, returned_to_origin, cancelled"
        ),
    )

    shipping_method_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="standard_delivery",
        comment="Shipping method code snapshot from order",
    )

    shipping_address_snapshot: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON snapshot of destination address at dispatch time",
    )

    destination_city: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Destination city for routing and filtering",
    )

    total_weight_grams: Mapped[int] = mapped_column(
        Integer,
        default=500,
        nullable=False,
        comment="Estimated or scaled package weight in grams",
    )

    package_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of parcel boxes comprising this consignment",
    )

    cod_amount_to_collect: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Cash on Delivery amount courier must collect before parcel handover",
    )

    dispatch_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Special delivery instructions or warehouse packing remarks",
    )

    # Lifecycle Timestamps
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        comment="Time shipment parcel was allocated from order items",
    )

    packed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Time parcel was packaged and sealed by warehouse staff",
    )

    dispatched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Time parcel was handed over to courier rider or dispatch hub",
    )

    estimated_delivery_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expected delivery timestamp provided by courier SLA",
    )

    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Time parcel was confirmed delivered to customer",
    )

    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Staff user who initiated parcel creation",
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="shipments")

    items: Mapped[List["ShipmentItem"]] = relationship(
        "ShipmentItem",
        back_populates="shipment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ShipmentItem.id.asc()",
    )

    events: Mapped[List["ShipmentEvent"]] = relationship(
        "ShipmentEvent",
        back_populates="shipment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ShipmentEvent.occurred_at.asc()",
    )

    created_by: Mapped[Optional["User"]] = relationship("User")


class ShipmentItem(Base, IDMixin):
    """
    Preserves line-item association for items assigned to this shipment parcel.
    Enables split or partial fulfillment of large customer orders.
    """

    __tablename__ = "shipment_items"

    shipment_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent shipment",
    )

    order_item_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent order line item",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Quantity of this line item included in this shipment parcel",
    )

    product_name_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Product title snapshot",
    )

    sku_snapshot: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Garment SKU snapshot",
    )

    size_snapshot: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Garment size snapshot",
    )

    color_snapshot: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Garment color snapshot",
    )

    # Relationships
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="items")
    order_item: Mapped["OrderItem"] = relationship("OrderItem")


class ShipmentEvent(Base, IDMixin):
    """
    Chronological audit ledger of shipment lifecycle tracking events.
    Records physical movements, warehouse milestones, courier checkpoints, and delivery updates.
    """

    __tablename__ = "shipment_events"

    shipment_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent shipment",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Fulfillment status milestone reached",
    )

    location: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Geographic checkpoint (e.g. Karachi Hub, Lahore Sorting Center)",
    )

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Explanatory description of the tracking checkpoint",
    )

    source: Mapped[str] = mapped_column(
        String(32),
        default="staff",
        nullable=False,
        comment="Event origin: staff, courier_webhook, courier_sync, system",
    )

    recorded_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who logged the checkpoint",
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        comment="Actual timestamp when the physical event occurred",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional internal notes or carrier remarks",
    )

    # Relationships
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="events")
    recorded_by: Mapped[Optional["User"]] = relationship("User")
