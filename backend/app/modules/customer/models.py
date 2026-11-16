"""
Customer Account Domain Models (Module M17)
Profiles, address book, preferences, and account metadata.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User


class CustomerProfile(Base, IDMixin, TimestampMixin):
    """
    Customer profile storing personal details and communication preferences.
    One-to-one relationship with the core User entity.
    """

    __tablename__ = "customer_profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Foreign key to owning User",
    )

    first_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Customer given name",
    )

    last_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Customer family name",
    )

    date_of_birth: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Customer birth date for anniversary and birthday perks",
    )

    gender: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="Gender identity (male, female, other, prefer_not_to_say)",
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Profile avatar or thumbnail URL",
    )

    marketing_email_opt_in: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Consent to receive marketing and promotional newsletters via email",
    )

    marketing_sms_opt_in: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Consent to receive promotional SMS notifications",
    )

    marketing_whatsapp_opt_in: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Consent to receive WhatsApp dispatch and order updates (standard for PK ecommerce)",
    )

    preferred_currency: Mapped[str] = mapped_column(
        String(3),
        default="PKR",
        nullable=False,
        comment="Display currency code (default PKR)",
    )

    preferred_language: Mapped[str] = mapped_column(
        String(8),
        default="en",
        nullable=False,
        comment="Interface language preference (default English, 'ur' for Urdu)",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="customer_profile",
    )


class Address(Base, IDMixin, TimestampMixin):
    """
    Customer address book entries for delivery and billing.
    Enforces customer ownership and single default address guarantee.
    """

    __tablename__ = "addresses"

    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning customer foreign key",
    )

    recipient_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Full recipient name for courier delivery parcel",
    )

    phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Direct contact number for courier rider (03XXXXXXXXX format)",
    )

    address_line_1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Street, house/building number, apartment/suite",
    )

    address_line_2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Landmark, floor, sector, or additional directions",
    )

    city: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Destination city (Karachi, Lahore, Islamabad, etc.)",
    )

    area: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Neighborhood, sector, or delivery zone (e.g. DHA Phase 6, Gulberg III)",
    )

    postal_code: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Postal or ZIP code",
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        default="PK",
        nullable=False,
        comment="Two-letter ISO country code (default PK)",
    )

    label: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Friendly address tag (e.g. Home, Office, Studio)",
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the primary default shipping address",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="addresses",
    )
