"""
Order and Checkout Schemas (M12)
Pydantic schemas for checkout requests, address snapshots, immutable order items,
lifecycle status transitions, and administrative order management.
"""

from datetime import datetime
from decimal import Decimal
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AddressSnapshot(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=128)
    phone: str = Field(..., min_length=10, max_length=20)
    address_line_1: str = Field(..., min_length=5, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=2, max_length=128)
    postal_code: Optional[str] = Field(None, max_length=16)
    country_code: str = Field(default="PK", min_length=2, max_length=2)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+?92|0)?3[0-9]{9}$", cleaned):
            raise ValueError("Invalid Pakistani mobile number format. Expected: 03XXXXXXXXX or +923XXXXXXXXX")
        return cleaned


class CheckoutRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=128)
    customer_email: EmailStr = Field(..., description="Order confirmation email")
    customer_phone: str = Field(..., min_length=10, max_length=20)
    shipping_address: AddressSnapshot
    shipping_method_code: str = Field(default="standard_delivery", description="Selected delivery method code")
    payment_method: str = Field(default="cod", description="Payment option: cod, card")
    customer_note: Optional[str] = Field(None, max_length=500)
    coupon_code: Optional[str] = Field(None, max_length=64)
    idempotency_key: Optional[str] = Field(None, max_length=128)

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+?92|0)?3[0-9]{9}$", cleaned):
            raise ValueError("Invalid Pakistani mobile number format")
        return cleaned


class OrderItemResponse(BaseModel):
    id: int
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    product_name: str
    product_slug: str
    sku: str
    size: str
    color: str
    unit_price: Decimal
    quantity: int
    line_discount: Decimal
    line_total: Decimal
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderStatusHistoryResponse(BaseModel):
    id: int
    from_status: str
    to_status: str
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    order_number: str
    status: str
    payment_status: str
    fulfillment_status: str
    payment_method: str
    currency_code: str
    customer_name: str
    customer_email: str
    customer_phone: str
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    shipping_method_code: str
    shipping_method_name: str
    shipping_address: AddressSnapshot
    customer_note: Optional[str] = None
    items: List[OrderItemResponse]
    status_history: List[OrderStatusHistoryResponse]
    placed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int


class OrderStatusUpdateRequest(BaseModel):
    to_status: str = Field(..., description="Target order lifecycle state")
    note: Optional[str] = Field(None, max_length=255)


class OrderPaymentSummary(BaseModel):
    id: int
    payment_method: str
    status: str
    amount: Decimal
    currency_code: str = "PKR"
    amount_collected: Decimal
    amount_outstanding: Decimal
    settlement_reference: Optional[str] = None
    provider_reference: Optional[str] = None
    reconciled_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OrderShipmentSummary(BaseModel):
    id: int
    shipment_number: str
    tracking_number: Optional[str] = None
    courier_code: Optional[str] = None
    courier_name: Optional[str] = None
    status: str
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OrderReturnSummary(BaseModel):
    id: int
    request_number: str
    request_type: str
    status: str
    reason_category: str
    refund_status: Optional[str] = None
    refund_amount: Optional[Decimal] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminOrderStatusHistoryResponse(BaseModel):
    id: int
    from_status: str
    to_status: str
    note: Optional[str] = None
    changed_by_user_id: Optional[int] = None
    changed_by_user_email: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminOrderDetailResponse(OrderResponse):
    user_id: Optional[int] = None
    payments: List[OrderPaymentSummary] = Field(default_factory=list)
    shipments: List[OrderShipmentSummary] = Field(default_factory=list)
    returns: List[OrderReturnSummary] = Field(default_factory=list)
    admin_history: List[AdminOrderStatusHistoryResponse] = Field(default_factory=list)


class OrderCancellationRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=255, description="Mandatory cancellation reason")


class OrderConfirmationRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=255, description="Optional confirmation note")


class OrderNoteCreateRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=500, description="Internal operational note")


class OrderCODReconciliationRequest(BaseModel):
    remittance_reference: str = Field(..., min_length=3, max_length=128, description="Courier remittance slip / settlement reference")
    amount_collected: Decimal = Field(..., gt=Decimal(0), description="Total cash collected by courier in PKR")
    notes: Optional[str] = Field(None, max_length=255, description="Reconciliation notes")
