"""
Cart and Wishlist Schemas (M10)
Pydantic models for server-calculated shopping carts, line items, and wishlists.
Prices and line subtotals are authoritative and recalculate from current catalog data.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# Cart Schemas
# ===========================================================================

class AddToCartRequest(BaseModel):
    variant_id: int = Field(..., gt=0, description="Product SKU variant ID")
    quantity: int = Field(default=1, ge=1, le=99, description="Quantity to add (1-99)")


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=0, le=99, description="Updated item quantity (0 removes item)")


class MergeCartRequest(BaseModel):
    anonymous_token: str = Field(
        ...,
        min_length=10,
        max_length=64,
        description="Guest visitor anonymous token to merge into customer cart",
    )


class CartItemResponse(BaseModel):
    id: int
    variant_id: int
    product_id: int
    product_name: str
    product_slug: str
    variant_sku: str
    size: str
    color_name: str
    color_hex: Optional[str] = None
    image_url: Optional[str] = None
    unit_price: Decimal
    original_price: Optional[Decimal] = None
    quantity: int
    line_total: Decimal
    available_stock: int
    is_available: bool
    availability_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    anonymous_token: Optional[str] = None
    status: str
    items: List[CartItemResponse]
    total_items: int
    subtotal: Decimal
    free_shipping_threshold: Decimal
    amount_needed_for_free_shipping: Decimal
    is_free_shipping: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# Wishlist Schemas
# ===========================================================================

class AddToWishlistRequest(BaseModel):
    product_id: int = Field(..., gt=0, description="Product ID to bookmark")


class WishlistItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_slug: str
    price: Decimal
    original_price: Optional[Decimal] = None
    image_url: Optional[str] = None
    is_available: bool
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WishlistResponse(BaseModel):
    id: int
    user_id: int
    items: List[WishlistItemResponse]
    total_items: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
