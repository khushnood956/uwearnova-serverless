"""
Pydantic Schemas for Categories and Collections
Defines input validation, serialization, and tree responses for catalog navigation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Category Schemas
# ---------------------------------------------------------------------------

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Display name for the category")
    slug: str = Field(
        ...,
        min_length=2,
        max_length=128,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-friendly kebab-case slug",
    )
    description: Optional[str] = Field(None, max_length=2000, description="Editorial description")
    image_url: Optional[str] = Field(None, max_length=1024, description="Hero or thumbnail image URL")
    sort_order: int = Field(0, ge=0, description="Sorting priority (lower numbers appear first)")
    is_active: bool = Field(True, description="Whether category is publicly visible")
    is_coming_soon: bool = Field(False, description="Whether category is marked as Coming Soon")
    parent_id: Optional[int] = Field(None, description="Optional parent category ID for nested subcategories")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    slug: Optional[str] = Field(None, min_length=2, max_length=128, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: Optional[str] = Field(None, max_length=2000)
    image_url: Optional[str] = Field(None, max_length=1024)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_coming_soon: Optional[bool] = None
    parent_id: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    is_coming_soon: bool = False
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    children: List["CategoryTreeResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=False)


# ---------------------------------------------------------------------------
# Collection Schemas
# ---------------------------------------------------------------------------

class CollectionBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Display name for the collection")
    slug: str = Field(
        ...,
        min_length=2,
        max_length=128,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-friendly kebab-case slug",
    )
    description: Optional[str] = Field(None, max_length=2000, description="Collection editorial description")
    image_url: Optional[str] = Field(None, max_length=1024, description="Promotional banner image URL")
    sort_order: int = Field(0, ge=0, description="Display order in navigation")
    is_active: bool = Field(True, description="Whether collection is publicly visible")


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    slug: Optional[str] = Field(None, min_length=2, max_length=128, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: Optional[str] = Field(None, max_length=2000)
    image_url: Optional[str] = Field(None, max_length=1024)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CollectionResponse(CollectionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Product Variant & Image Schemas
# ---------------------------------------------------------------------------

class ProductImageBase(BaseModel):
    image_url: str = Field(..., max_length=1024, description="Public image URL")
    storage_key: Optional[str] = Field(None, max_length=255, description="Storage key / asset path")
    alt_text: Optional[str] = Field(None, max_length=255, description="Image alt text")
    sort_order: int = Field(0, ge=0, description="Display order in gallery")
    is_primary: bool = Field(False, description="Primary thumbnail indicator")
    file_size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")
    mime_type: Optional[str] = Field(None, max_length=64, description="MIME content type")
    width: Optional[int] = Field(None, ge=0, description="Image pixel width")
    height: Optional[int] = Field(None, ge=0, description="Image pixel height")


class ProductImageCreate(ProductImageBase):
    pass


class AddImageUrlRequest(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=1024, description="Direct URL of image")
    alt_text: Optional[str] = Field(None, max_length=255, description="Image alt text")
    is_primary: bool = Field(False, description="Primary hero image toggle")


class ProductImageResponse(ProductImageBase):
    id: int
    product_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PresignedUploadRequest(BaseModel):
    file_name: str = Field(..., min_length=3, max_length=255, description="Original filename (e.g. garment-front.webp)")
    mime_type: str = Field(..., description="MIME type e.g. image/webp, image/jpeg, image/png")
    file_size_bytes: int = Field(..., gt=0, description="Payload size in bytes")


class PresignedUploadResponse(BaseModel):
    upload_url: str
    storage_key: str
    public_url: str
    expires_in_seconds: int
    http_method: str = "PUT"
    required_headers: dict = Field(default_factory=dict)


class ConfirmUploadRequest(BaseModel):
    storage_key: str = Field(..., min_length=5, max_length=255)
    alt_text: Optional[str] = Field(None, max_length=255)
    is_primary: bool = Field(False)
    file_size_bytes: Optional[int] = Field(None, ge=0)
    mime_type: Optional[str] = Field(None, max_length=64)
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)


class ReorderImagesRequest(BaseModel):
    image_ids: List[int] = Field(..., min_length=1, description="Ordered list of image IDs")


class ProductVariantBase(BaseModel):
    sku: str = Field(..., min_length=2, max_length=64, description="Unique SKU code")
    size: str = Field(..., min_length=1, max_length=32, description="Size descriptor")
    color_name: str = Field(..., min_length=1, max_length=64, description="Color name")
    color_hex: Optional[str] = Field(None, max_length=16, description="Color swatch hex")
    price: Optional[Decimal] = Field(None, gt=Decimal(0), description="Optional variant price override in PKR")
    compare_at_price: Optional[Decimal] = Field(None, gt=Decimal(0), description="Optional compare-at price in PKR")
    inventory_count: int = Field(0, ge=0, description="Stock on hand")
    in_stock: bool = Field(True, description="Available flag")
    weight_grams: Optional[int] = Field(None, ge=0, description="Weight in grams")
    is_active: bool = Field(True, description="Active status")


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=2, max_length=64)
    size: Optional[str] = Field(None, min_length=1, max_length=32)
    color_name: Optional[str] = Field(None, min_length=1, max_length=64)
    color_hex: Optional[str] = Field(None, max_length=16)
    price: Optional[Decimal] = Field(None, gt=Decimal(0))
    compare_at_price: Optional[Decimal] = Field(None, gt=Decimal(0))
    inventory_count: Optional[int] = Field(None, ge=0)
    in_stock: Optional[bool] = None
    weight_grams: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductVariantResponse(ProductVariantBase):
    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Product Schemas
# ---------------------------------------------------------------------------

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Product title")
    slug: str = Field(
        ...,
        min_length=2,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-friendly kebab-case slug",
    )
    subtitle: Optional[str] = Field(None, max_length=255, description="Material or design subtitle")
    description: Optional[str] = Field(None, description="Detailed product description")
    category_id: int = Field(..., description="Associated category ID")
    brand_label: str = Field("UniNova", max_length=128, description="Brand label")
    status: str = Field("active", pattern=r"^(draft|active|archived)$", description="Lifecycle status")
    price: Decimal = Field(..., gt=Decimal(0), description="Base price in PKR")
    original_price: Optional[Decimal] = Field(None, gt=Decimal(0), description="Compare-at price in PKR")
    is_new_arrival: bool = Field(False, description="New arrivals flag")
    is_trending: bool = Field(False, description="Trending pieces flag")
    is_featured: bool = Field(False, description="Featured flag")
    fabric_care: Optional[List[str]] = Field(None, description="Care instructions and composition")
    delivery_notes: Optional[str] = Field(None, max_length=500, description="Delivery or shipping terms")


class ProductCreate(ProductBase):
    collection_ids: List[int] = Field(default_factory=list, description="Associated collection IDs")
    images: List[ProductImageCreate] = Field(default_factory=list, description="Product imagery")
    variants: List[ProductVariantCreate] = Field(default_factory=list, description="Product variants")


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    subtitle: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand_label: Optional[str] = Field(None, max_length=128)
    status: Optional[str] = Field(None, pattern=r"^(draft|active|archived)$")
    price: Optional[Decimal] = Field(None, gt=Decimal(0))
    original_price: Optional[Decimal] = Field(None, gt=Decimal(0))
    is_new_arrival: Optional[bool] = None
    is_trending: Optional[bool] = None
    is_featured: Optional[bool] = None
    fabric_care: Optional[List[str]] = None
    delivery_notes: Optional[str] = Field(None, max_length=500)
    collection_ids: Optional[List[int]] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    category_id: int
    category: Optional[CategoryResponse] = None
    collections: List[CollectionResponse] = Field(default_factory=list)
    brand_label: str
    status: str
    price: Decimal
    original_price: Optional[Decimal] = None
    is_new_arrival: bool
    is_trending: bool
    is_featured: bool
    fabric_care: Optional[List[str]] = None
    delivery_notes: Optional[str] = None
    rating: Decimal
    review_count: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    images: List[ProductImageResponse] = Field(default_factory=list)
    variants: List[ProductVariantResponse] = Field(default_factory=list)

    @field_validator("fabric_care", mode="before")
    @classmethod
    def parse_fabric_care(cls, v: Any) -> Optional[List[str]]:
        import json
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [v]
        return None

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    limit: int
    offset: int


class ProductVariantUpdate(BaseModel):
    """Payload to update an existing variant SKU."""
    sku: Optional[str] = Field(None, min_length=2, max_length=64, description="Stock Keeping Unit")
    size: Optional[str] = Field(None, max_length=32, description="Garment or footwear size")
    color_name: Optional[str] = Field(None, max_length=64, description="Color swatch name")
    color_hex: Optional[str] = Field(None, max_length=16, description="Color hex code")
    price: Optional[Decimal] = Field(None, gt=Decimal(0), description="Price override in PKR")
    compare_at_price: Optional[Decimal] = Field(None, gt=Decimal(0), description="Compare-at price in PKR")
    inventory_count: Optional[int] = Field(None, ge=0, description="Available physical inventory")
    in_stock: Optional[bool] = Field(None, description="Availability flag")
    weight_grams: Optional[int] = Field(None, ge=0, description="Weight in grams")
    is_active: Optional[bool] = Field(None, description="Active status")


class ProductBulkStatusRequest(BaseModel):
    """Payload for administrative bulk status updates."""
    product_ids: List[int] = Field(..., min_length=1, max_length=100, description="List of target product IDs")
    status: str = Field(..., pattern=r"^(draft|active|archived)$", description="New status to apply")


class ProductBulkStatusResponse(BaseModel):
    """Response summarizing bulk status updates."""
    updated_count: int
    status: str
    product_ids: List[int]


class CollectionProductAssignRequest(BaseModel):
    """Payload for assigning products to a curated collection."""
    product_ids: List[int] = Field(..., min_length=1, description="List of product IDs to associate")

