"""
Catalog Database Models
Categories, Collections, Products, Variants, and Images.
Follows MySQL 8.0 schema specifications in docs/backend/02-database-design.md.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.inventory.models import InventoryItem

# Association table between products and collections
product_collections = Table(
    "product_collections",
    Base.metadata,
    Column(
        "product_id",
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "collection_id",
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


class Category(Base, IDMixin, TimestampMixin):
    """
    Product Category model supporting hierarchical classification
    (e.g., Women -> Ready-to-Wear, Men -> Tailoring, Footwear, Accessories).
    """

    __tablename__ = "categories"

    parent_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Optional parent category ID for nested taxonomy",
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable category name",
    )

    slug: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="SEO-friendly URL identifier",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Editorial category description",
    )

    image_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="Hero or thumbnail image URL / S3 asset key",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
        comment="Display priority order (lower comes first)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Storefront visibility toggle",
    )

    is_coming_soon: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether category/department is marked as Coming Soon",
    )

    # Hierarchical self-referencing relationship
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )

    children: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all",
        lazy="selectin",
        order_by="Category.sort_order",
    )

    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="category",
    )


class Collection(Base, IDMixin, TimestampMixin):
    """
    Curated Collection model for marketing and seasonal groupings
    (e.g., New Arrivals, Essentials, Signature Collection, Summer Sale).
    """

    __tablename__ = "collections"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable collection name",
    )

    slug: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="SEO-friendly collection slug for storefront routes",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Marketing description and editorial context",
    )

    image_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="Promotional banner image URL / asset key",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
        comment="Display priority in storefront navigation",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether collection is publicly accessible",
    )

    products: Mapped[List["Product"]] = relationship(
        "Product",
        secondary=product_collections,
        back_populates="collections",
        lazy="selectin",
    )


class Product(Base, IDMixin, TimestampMixin):
    """
    Core Product Catalogue record containing editorial, pricing, category,
    and publication status information.
    """

    __tablename__ = "products"

    category_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to primary category",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Product title",
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="SEO-friendly unique product URL slug",
    )

    subtitle: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Subtitle or material summary (e.g. Heavyweight Virgin Wool Blend)",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comprehensive editorial description",
    )

    brand_label: Mapped[str] = mapped_column(
        String(128),
        default="UWEARNOVA",
        nullable=False,
        comment="Brand label name",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
        index=True,
        comment="Lifecycle status: draft, active, archived",
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        index=True,
        comment="Storefront base selling price in PKR",
    )

    original_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Compare-at price before discount in PKR",
    )

    is_new_arrival: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Highlights product in New Arrivals section",
    )

    is_trending: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Highlights product in Trending Pieces section",
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Featured on homepage curations",
    )

    fabric_care: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialized array of fabric composition and care guidelines",
    )

    delivery_notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Special delivery terms, lead times, or return notice",
    )

    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("5.0"),
        nullable=False,
        comment="Average review score (1.0 to 5.0)",
    )

    review_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total verified customer reviews",
    )

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp when product was published live",
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="products",
        lazy="selectin",
    )

    collections: Mapped[List["Collection"]] = relationship(
        "Collection",
        secondary=product_collections,
        back_populates="products",
        lazy="selectin",
    )

    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProductVariant.id",
    )

    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProductImage.sort_order",
    )


class ProductVariant(Base, IDMixin, TimestampMixin):
    """
    Product SKU Variant representing a specific size/color combination with
    inventory stock and individual pricing.
    """

    __tablename__ = "product_variants"

    product_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent product",
    )

    sku: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Stock Keeping Unit (unique identifier)",
    )

    size: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Garment or footwear size (e.g. S, M, L, 40R, 42, One Size)",
    )

    color_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Color description (e.g. Obsidian Black, Sand Ivory, Warm Taupe)",
    )

    color_hex: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="Hexadecimal color swatch code (e.g. #111111, #C5AA82)",
    )

    price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Variant price override in PKR (null inherits product base price)",
    )

    compare_at_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Variant compare-at price in PKR",
    )

    inventory_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Available physical stock quantity",
    )

    in_stock: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Storefront availability flag",
    )

    weight_grams: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Shipping parcel weight in grams",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active variant status toggle",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="variants",
    )

    inventory_items: Mapped[List["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="variant",
        cascade="all, delete-orphan",
    )


class ProductImage(Base, IDMixin):
    """Product gallery imagery supporting multi-angle views and primary thumbnails."""

    __tablename__ = "product_images"

    product_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to product",
    )

    image_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Public image URL / asset path",
    )

    storage_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="S3 object key or partitioned storage path",
    )

    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        nullable=True,
        comment="Binary payload size in bytes",
    )

    mime_type: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="MIME content type (e.g. image/webp, image/jpeg)",
    )

    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Pixel width",
    )

    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Pixel height",
    )

    alt_text: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Accessibility alt text",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display sequence in gallery",
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Primary hero image for catalogue card thumbnail",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        comment="UTC creation timestamp",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="images",
    )
