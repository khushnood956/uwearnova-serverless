"""
Fulfillment and Shipment API Schemas (Module M15)
Pydantic contracts for shipment creation, status transitions,
manual tracking checkpoints, and customer tracking views.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ShipmentItemAllocationRequest(BaseModel):
    """Specific line item and quantity allocated to a parcel."""
    order_item_id: int
    quantity: int = Field(default=1, gt=0)


class ShipmentCreateRequest(BaseModel):
    """Payload to create a shipment parcel for an order."""
    courier_code: str = Field(default="manual", description="Carrier code (e.g. tcs, leopards, trax, manual)")
    courier_name: Optional[str] = Field(default=None, description="Optional custom carrier name")
    tracking_number: Optional[str] = Field(default=None, description="Airway Bill (AWB) or CN number")
    tracking_url: Optional[str] = Field(default=None, description="Direct URL to courier tracking portal")
    total_weight_grams: int = Field(default=500, gt=0, description="Package weight in grams")
    package_count: int = Field(default=1, ge=1, description="Number of packages in this shipment")
    cod_amount_to_collect: Optional[Decimal] = Field(default=None, description="COD collection amount")
    dispatch_notes: Optional[str] = Field(default=None, max_length=1000)
    items: Optional[List[ShipmentItemAllocationRequest]] = Field(
        default=None,
        description="Line items to include; if omitted, all unfulfilled order items are included",
    )


class ShipmentStatusUpdateRequest(BaseModel):
    """Advance or transition shipment fulfillment state."""
    status: str = Field(
        ...,
        description=(
            "Valid states: packing, packed, ready_for_pickup, dispatched, in_transit, "
            "out_for_delivery, delivered, delivery_failed, returned_to_origin, cancelled"
        ),
    )
    location: Optional[str] = Field(default=None, max_length=128, description="Geographic checkpoint")
    description: Optional[str] = Field(default=None, max_length=500, description="Milestone note")
    notes: Optional[str] = Field(default=None, max_length=1000)


class ShipmentTrackingUpdateRequest(BaseModel):
    """Update carrier assignment or consignment tracking reference."""
    tracking_number: str = Field(..., min_length=1, max_length=128)
    courier_code: Optional[str] = Field(default=None)
    tracking_url: Optional[str] = Field(default=None, max_length=512)


class ShipmentEventCreateRequest(BaseModel):
    """Append a tracking checkpoint without necessarily advancing state."""
    status: str = Field(..., max_length=32)
    location: Optional[str] = Field(default=None, max_length=128)
    description: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=1000)


class ShipmentItemResponse(BaseModel):
    """Line item in shipment response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_item_id: int
    quantity: int
    product_name_snapshot: str
    sku_snapshot: str
    size_snapshot: str
    color_snapshot: str


class ShipmentEventResponse(BaseModel):
    """Tracking event checkpoint response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    location: Optional[str] = None
    description: str
    source: str
    recorded_by_user_id: Optional[int] = None
    occurred_at: datetime
    notes: Optional[str] = None


class ShipmentResponse(BaseModel):
    """Complete shipment parcel detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_number: str
    order_id: int
    courier_code: str
    courier_name: str
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    status: str
    shipping_method_code: str
    destination_city: str
    total_weight_grams: int
    package_count: int
    cod_amount_to_collect: Decimal
    dispatch_notes: Optional[str] = None
    allocated_at: datetime
    packed_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    estimated_delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    items: List[ShipmentItemResponse] = Field(default_factory=list)
    events: List[ShipmentEventResponse] = Field(default_factory=list)
    created_at: datetime


class ShipmentListResponse(BaseModel):
    """Paginated list of shipment parcels."""
    items: List[ShipmentResponse]
    total: int
    page: int
    page_size: int


class OrderTrackingTimelineResponse(BaseModel):
    """Customer-facing order delivery tracking timeline."""
    order_number: str
    order_status: str
    fulfillment_status: str
    destination_city: str
    shipments: List[ShipmentResponse]
