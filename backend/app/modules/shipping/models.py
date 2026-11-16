"""
Shipping Domain Models (M11)
Defines configurable delivery zones, service areas, and shipping methods
with fee rules, free-shipping thresholds, and COD eligibility.
"""

from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IDMixin, TimestampMixin


class ShippingZone(Base, IDMixin, TimestampMixin):
    """
    Logistics service area or regional delivery tier.
    Groups cities by geographical transit tier (e.g. Major Metros vs Nationwide Outlying).
    """

    __tablename__ = "shipping_zones"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Zone display title (e.g. Major Metropolitan Hubs)",
    )

    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique zone identifier (e.g. major_metro, nationwide)",
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Zone operational description",
    )

    cities: Mapped[str] = mapped_column(
        Text,
        default="[]",
        nullable=False,
        comment="JSON-serialized array of serviced city names in this zone",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active delivery zone toggle",
    )

    # Relationships
    methods: Mapped[List["ShippingMethod"]] = relationship(
        "ShippingMethod",
        back_populates="zone",
        cascade="all, delete-orphan",
        order_by="ShippingMethod.sort_order.asc()",
    )


class ShippingMethod(Base, IDMixin, TimestampMixin):
    """
    Configurable delivery service option.
    Specifies base freight fee, free shipping qualification threshold,
    transit SLAs, and Cash on Delivery eligibility.
    """

    __tablename__ = "shipping_methods"

    zone_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("shipping_zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional zone restriction (null indicates nationwide applicability)",
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Service title displayed to customer (e.g. Standard Nationwide Delivery)",
    )

    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique method code (e.g. standard_delivery, express_metro)",
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Delivery timeline note (e.g. 2–3 business days via premier courier)",
    )

    base_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("350.00"),
        nullable=False,
        comment="Standard shipping fee in PKR",
    )

    free_shipping_threshold: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        default=Decimal("15000.00"),
        nullable=True,
        comment="Order subtotal threshold in PKR for complimentary free delivery",
    )

    estimated_days_min: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
        comment="Minimum business days for doorstep delivery",
    )

    estimated_days_max: Mapped[int] = mapped_column(
        Integer,
        default=4,
        nullable=False,
        comment="Maximum business days for doorstep delivery",
    )

    is_cod_supported: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether Cash on Delivery is accepted for this delivery method",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active delivery method toggle",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display ordering on storefront checkout",
    )

    # Relationships
    zone: Mapped[Optional["ShippingZone"]] = relationship(
        "ShippingZone",
        back_populates="methods",
    )
