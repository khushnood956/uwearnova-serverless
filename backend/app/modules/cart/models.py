"""
Cart and Wishlist Database Models (M10)
Defines server-side carts, cart items, customer wishlists, and wishlist items.
Supports both authenticated customer carts and guest anonymous carts with merging.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
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
    from app.modules.catalog.models import Product, ProductVariant


class Cart(Base, IDMixin, TimestampMixin):
    """
    Shopping cart record.
    Supports authenticated customers (via user_id) and guest shoppers (via anonymous_token).
    """

    __tablename__ = "carts"

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Associated customer account ID if authenticated",
    )

    anonymous_token: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Guest visitor unique session token",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
        index=True,
        comment="Cart status: active, merged, converted_to_order, abandoned",
    )

    # Relationships
    items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CartItem.created_at.desc()",
    )

    user: Mapped[Optional["User"]] = relationship("User")


class CartItem(Base, IDMixin, TimestampMixin):
    """
    Line item inside a shopping cart.
    Links to a specific SKU ProductVariant with quantity.
    """

    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id", name="uq_cart_items_cart_variant"),
    )

    cart_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent cart",
    )

    variant_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to product SKU variant",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Requested item purchase quantity",
    )

    # Relationships
    cart: Mapped["Cart"] = relationship(
        "Cart",
        back_populates="items",
    )

    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant",
        lazy="selectin",
    )


class Wishlist(Base, IDMixin, TimestampMixin):
    """
    Customer saved items wishlist.
    Strictly isolated to authenticated customer accounts.
    """

    __tablename__ = "wishlists"

    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Foreign key to customer user account",
    )

    # Relationships
    items: Mapped[List["WishlistItem"]] = relationship(
        "WishlistItem",
        back_populates="wishlist",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="WishlistItem.created_at.desc()",
    )

    user: Mapped["User"] = relationship("User")


class WishlistItem(Base, IDMixin):
    """
    Product bookmark inside a customer wishlist.
    """

    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint("wishlist_id", "product_id", name="uq_wishlist_items_wishlist_product"),
    )

    wishlist_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("wishlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent wishlist",
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to saved product",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        comment="Timestamp when product was added to wishlist",
    )

    # Relationships
    wishlist: Mapped["Wishlist"] = relationship(
        "Wishlist",
        back_populates="items",
    )

    product: Mapped["Product"] = relationship(
        "Product",
        lazy="selectin",
    )
