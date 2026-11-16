"""
Inventory Schemas (M09)
Pydantic schemas for warehouse locations, inventory levels, stock adjustments,
reservations, releases, and movement history.
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# Location Schemas
class InventoryLocationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    code: str = Field(..., min_length=2, max_length=64)
    address_line_1: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=128)
    postal_code: Optional[str] = Field(None, max_length=32)
    country_code: str = Field(default="PK", min_length=2, max_length=2)
    is_active: bool = True


class InventoryLocationCreate(InventoryLocationBase):
    pass


class InventoryLocationResponse(InventoryLocationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Inventory Item Schemas
class InventoryItemResponse(BaseModel):
    id: int
    variant_id: int
    location_id: int
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    reorder_threshold: int
    is_low_stock: bool
    variant_sku: Optional[str] = None
    variant_size: Optional[str] = None
    variant_color: Optional[str] = None
    product_name: Optional[str] = None
    location_name: Optional[str] = None
    location_code: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryItemListResponse(BaseModel):
    items: List[InventoryItemResponse]
    total: int
    page: int
    page_size: int


class StockThresholdUpdateRequest(BaseModel):
    reorder_threshold: int = Field(..., ge=0, description="Replenishment alert threshold")


# Stock Operations Schemas
MovementType = Literal[
    "receipt",
    "sale",
    "reservation",
    "release",
    "return",
    "adjustment",
    "cycle_count",
    "damaged",
]


class StockAdjustmentRequest(BaseModel):
    variant_id: int = Field(..., gt=0, description="Product variant SKU ID")
    location_id: Optional[int] = Field(None, gt=0, description="Target warehouse location (defaults to primary)")
    quantity_delta: int = Field(..., description="Quantity delta (positive for intake, negative for decrement)")
    reason: MovementType = Field(default="adjustment", description="Movement reason classification")
    notes: Optional[str] = Field(None, max_length=255, description="Auditable operator explanation")
    reference_type: Optional[str] = Field(None, max_length=64, description="Originating document type")
    reference_id: Optional[str] = Field(None, max_length=64, description="Originating document identifier")


class StockReservationRequest(BaseModel):
    variant_id: int = Field(..., gt=0, description="Product variant SKU ID")
    location_id: Optional[int] = Field(None, gt=0, description="Target warehouse location (defaults to primary)")
    quantity: int = Field(..., gt=0, description="Number of units to reserve from available stock")
    reference_type: str = Field(default="checkout_hold", max_length=64)
    reference_id: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=255)


class StockReleaseRequest(BaseModel):
    variant_id: int = Field(..., gt=0, description="Product variant SKU ID")
    location_id: Optional[int] = Field(None, gt=0, description="Target warehouse location (defaults to primary)")
    quantity: int = Field(..., gt=0, description="Number of units to release back to available stock")
    reference_type: str = Field(default="checkout_release", max_length=64)
    reference_id: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=255)


# Movement History Schemas
class InventoryMovementResponse(BaseModel):
    id: int
    variant_id: int
    location_id: int
    movement_type: str
    quantity_delta: int
    quantity_on_hand_before: int
    quantity_on_hand_after: int
    quantity_reserved_before: int
    quantity_reserved_after: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    reason_notes: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    variant_sku: Optional[str] = None
    location_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryMovementListResponse(BaseModel):
    movements: List[InventoryMovementResponse]
    total: int
    page: int
    page_size: int


# Bulk and Low-Stock Operations
class BulkStockAdjustmentItem(BaseModel):
    variant_id: int = Field(..., gt=0, description="Product variant SKU ID")
    location_id: Optional[int] = Field(None, gt=0, description="Warehouse location (defaults to primary)")
    quantity_delta: int = Field(..., description="Quantity delta (positive for intake, negative for decrement)")
    reason: MovementType = Field(default="receipt", description="Movement reason classification")
    notes: Optional[str] = Field(None, max_length=255, description="Audit note")


class BulkStockAdjustmentRequest(BaseModel):
    adjustments: List[BulkStockAdjustmentItem] = Field(
        ..., min_length=1, max_length=100, description="List of stock intake or adjustment items"
    )


class BulkStockAdjustmentResponse(BaseModel):
    adjusted_count: int
    total_delta: int
    timestamp: datetime


class LowStockItemResponse(BaseModel):
    item_id: int
    variant_id: int
    variant_sku: str
    product_name: str
    variant_size: Optional[str] = None
    variant_color: Optional[str] = None
    location_id: int
    location_name: str
    location_code: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    reorder_threshold: int
    deficit: int
    updated_at: datetime


class LowStockReportResponse(BaseModel):
    items: List[LowStockItemResponse]
    total_low_stock_items: int
    generated_at: datetime

