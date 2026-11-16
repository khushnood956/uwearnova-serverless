"""
Promotions and Coupon Models (Module M21)
Defines discount coupons, validation criteria, usage quotas, and redemption history.
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


class Coupon(Base, IDMixin, TimestampMixin):
    """
    Promotional coupon with configurable discount rules, expiration, and usage limits.
    """

    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Normalized uppercase coupon code (e.g. WELCOME10, EID2026)",
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable description or promotion notes",
    )

    discount_type: Mapped[str] = mapped_column(
        String(32),
        default="percentage",
        nullable=False,
        comment="Discount mechanism: percentage, fixed_amount, free_shipping",
    )

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Value of discount: percent off (e.g. 15.00 for 15%) or PKR fixed deduction",
    )

    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Maximum ceiling cap in PKR for percentage discounts",
    )

    min_order_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Minimum eligible order subtotal in PKR required to apply coupon",
    )

    usage_limit_total: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total system-wide redemption limit (null for unlimited)",
    )

    usage_limit_per_customer: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=1,
        nullable=True,
        comment="Maximum redemptions per customer (null for unlimited)",
    )

    times_redeemed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total counter of completed redemptions",
    )

    starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Coupon validity start timestamp",
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Coupon validity expiration timestamp",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Administrative active flag",
    )

    # Relationships
    redemptions: Mapped[List["CouponRedemption"]] = relationship(
        "CouponRedemption",
        back_populates="coupon",
        cascade="all, delete-orphan",
    )


class CouponRedemption(Base, IDMixin):
    """
    Immutable ledger of successful coupon redemptions attached to placed orders.
    """

    __tablename__ = "coupon_redemptions"

    coupon_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("coupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent coupon ID",
    )

    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Order where coupon was redeemed",
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated customer user ID (null for guest)",
    )

    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Customer email address used at checkout",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Actual discount amount in PKR granted by this redemption",
    )

    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Redemption timestamp",
    )

    # Relationships
    coupon: Mapped["Coupon"] = relationship("Coupon", back_populates="redemptions")
