"""
Product Reviews Domain Models (Module M21)
Defines customer garment reviews, star ratings, verified buyer flags, and moderation status.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.catalog.models import Product


class ProductReview(Base, IDMixin, TimestampMixin):
    """
    Customer review for an apparel product.
    Includes star rating (1-5), verified purchaser verification,
    and moderation lifecycle states (pending, approved, rejected, hidden).
    """

    __tablename__ = "product_reviews"

    product_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated product ID",
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Customer user ID if authenticated (null for guest)",
    )

    customer_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Author display name",
    )

    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Customer contact email",
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Numerical rating score (1 to 5 stars)",
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Review headline or summary",
    )

    comment: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full review commentary and garment feedback",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
        comment="Moderation state: pending, approved, rejected, hidden",
    )

    is_verified_buyer: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag indicating customer completed an order containing this product",
    )

    admin_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes recorded during moderation review",
    )

    moderated_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Staff user who moderated this review",
    )

    moderated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when moderation decision was recorded",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product")
