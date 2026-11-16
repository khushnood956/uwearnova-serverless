"""
Identity & Authentication Database Models
Follows MySQL 8.0 schema specifications in docs/backend/02-database-design.md.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.customer.models import Address, CustomerProfile
    from app.modules.staff.models import StaffProfile


class User(Base, IDMixin, TimestampMixin):
    """Core user account record representing customers, staff, and store administrators."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Normalized unique email address",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Argon2id password hash",
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Optional mobile or WhatsApp contact number",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
        index=True,
        comment="Account state: active, pending_verification, disabled, locked",
    )

    user_type: Mapped[str] = mapped_column(
        String(32),
        default="customer",
        nullable=False,
        index=True,
        comment="Primary user type: customer, staff, admin",
    )

    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp when email was confirmed",
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp of most recent successful login",
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Counter for rate limiting and temporary account lockout",
    )

    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp until which account is temporarily locked",
    )

    # Relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    password_resets: Mapped[List["PasswordReset"]] = relationship(
        "PasswordReset",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        lazy="selectin",
    )

    customer_profile: Mapped[Optional["CustomerProfile"]] = relationship(
        "CustomerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    addresses: Mapped[List["Address"]] = relationship(
        "Address",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    staff_profile: Mapped[Optional["StaffProfile"]] = relationship(
        "StaffProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class RefreshToken(Base, IDMixin, TimestampMixin):
    """Persisted refresh token metadata for session rotation and revocation."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="User account owning this session",
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="SHA-256 hash of raw refresh token string",
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="True if session was logged out or rotated",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="UTC expiration deadline for this refresh token",
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class PasswordReset(Base, IDMixin, TimestampMixin):
    """Password reset token record for self-service recovery."""

    __tablename__ = "password_resets"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="User account requesting password reset",
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="SHA-256 hash of one-time reset token",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="UTC expiration deadline (typically 1 hour)",
    )

    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True once token has been redeemed",
    )

    user: Mapped["User"] = relationship("User", back_populates="password_resets")
