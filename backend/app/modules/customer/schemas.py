"""
Customer Account Schemas (Module M17)
Pydantic schemas for customer profile, address book, preferences,
customer-safe order details/timeline, returns overview, and security settings.
"""

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==============================================================================
# 1. Profile Schemas
# ==============================================================================

class CustomerProfileResponse(BaseModel):
    """Authoritative customer profile view with personal info and preferences."""
    id: Optional[int] = None
    user_id: int
    email: str
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    marketing_email_opt_in: bool = False
    marketing_sms_opt_in: bool = False
    marketing_whatsapp_opt_in: bool = True
    preferred_currency: str = "PKR"
    preferred_language: str = "en"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerProfileUpdateRequest(BaseModel):
    """Payload to update customer profile fields."""
    first_name: Optional[str] = Field(None, max_length=64)
    last_name: Optional[str] = Field(None, max_length=64)
    phone: Optional[str] = Field(None, max_length=32)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=16)
    avatar_url: Optional[str] = Field(None, max_length=512)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+?92|0)?3[0-9]{9}$", cleaned):
            raise ValueError(
                "Invalid Pakistani mobile number format. Expected format: 03XXXXXXXXX or +923XXXXXXXXX"
            )
        return cleaned


# ==============================================================================
# 2. Preferences Schemas
# ==============================================================================

class CustomerPreferencesResponse(BaseModel):
    """Communication and localization preferences."""
    marketing_email_opt_in: bool
    marketing_sms_opt_in: bool
    marketing_whatsapp_opt_in: bool
    preferred_currency: str
    preferred_language: str

    model_config = ConfigDict(from_attributes=True)


class CustomerPreferencesUpdateRequest(BaseModel):
    """Payload to update notification and language preferences."""
    marketing_email_opt_in: Optional[bool] = None
    marketing_sms_opt_in: Optional[bool] = None
    marketing_whatsapp_opt_in: Optional[bool] = None
    preferred_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    preferred_language: Optional[str] = Field(None, min_length=2, max_length=8)


# ==============================================================================
# 3. Address Book Schemas
# ==============================================================================

class AddressBase(BaseModel):
    """Common attributes for address book records."""
    recipient_name: str = Field(..., min_length=2, max_length=128)
    phone: str = Field(..., min_length=7, max_length=32)
    address_line_1: str = Field(..., min_length=5, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=2, max_length=128)
    area: Optional[str] = Field(None, max_length=128)
    postal_code: Optional[str] = Field(None, max_length=32)
    country_code: str = Field(default="PK", min_length=2, max_length=2)
    label: Optional[str] = Field(None, max_length=64)
    is_default: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+?92|0)?3[0-9]{9}$", cleaned):
            raise ValueError(
                "Invalid Pakistani mobile number format. Expected format: 03XXXXXXXXX or +923XXXXXXXXX"
            )
        return cleaned


class AddressCreateRequest(AddressBase):
    pass


class AddressUpdateRequest(BaseModel):
    recipient_name: Optional[str] = Field(None, min_length=2, max_length=128)
    phone: Optional[str] = Field(None, min_length=7, max_length=32)
    address_line_1: Optional[str] = Field(None, min_length=5, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=128)
    area: Optional[str] = Field(None, max_length=128)
    postal_code: Optional[str] = Field(None, max_length=32)
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    label: Optional[str] = Field(None, max_length=64)
    is_default: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+?92|0)?3[0-9]{9}$", cleaned):
            raise ValueError(
                "Invalid Pakistani mobile number format. Expected format: 03XXXXXXXXX or +923XXXXXXXXX"
            )
        return cleaned


class AddressResponse(AddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddressListResponse(BaseModel):
    addresses: List[AddressResponse]
    total: int


# ==============================================================================
# 4. Customer-Safe Order Details & Timeline Schemas
# ==============================================================================

class CustomerOrderItemResponse(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    product_slug: str
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    unit_price: Decimal
    quantity: int
    line_total: Decimal
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerOrderTimelineEntry(BaseModel):
    status: str
    description: str
    occurred_at: datetime


class CustomerShipmentSummary(BaseModel):
    id: int
    shipment_number: str
    courier_name: str
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    status: str
    total_weight_grams: int
    allocated_at: datetime
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerOrderDetailResponse(BaseModel):
    """
    Customer-facing order details.
    Guarantees internal staff notes, provider secrets, and operational remarks are omitted.
    """
    id: int
    order_number: str
    status: str
    payment_method: str
    payment_status: str
    fulfillment_status: str
    currency_code: str
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    shipping_address: Dict[str, Any]
    shipping_method_code: str
    customer_notes: Optional[str] = None
    items: List[CustomerOrderItemResponse]
    timeline: List[CustomerOrderTimelineEntry]
    shipments: List[CustomerShipmentSummary]
    placed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 5. Customer Return & Exchange Overview Schemas
# ==============================================================================

class CustomerReturnItemResponse(BaseModel):
    id: int
    order_item_id: int
    product_name: str
    sku: str
    quantity: int
    reason: str
    exchange_size: Optional[str] = None
    inspection_status: str
    refund_amount: Optional[Decimal] = None


class CustomerReturnResponse(BaseModel):
    """Customer-facing return overview (omits internal staff/inspector notes)."""
    id: int
    request_number: str
    order_number: str
    status: str
    request_type: str
    resolution_type: str
    total_refund_amount: Optional[Decimal] = None
    customer_notes: Optional[str] = None
    items: List[CustomerReturnItemResponse]
    created_at: datetime
    resolved_at: Optional[datetime] = None


class CustomerReturnListResponse(BaseModel):
    returns: List[CustomerReturnResponse]
    total: int
    page: int
    page_size: int


# ==============================================================================
# 6. Security & Session Schemas
# ==============================================================================

class CustomerPasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Existing account password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New account password (minimum 8 characters)",
    )


class CustomerSessionResponse(BaseModel):
    id: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_current: bool = False


class CustomerSecurityOverviewResponse(BaseModel):
    email: str
    phone: Optional[str] = None
    email_verified: bool
    last_login_at: Optional[datetime] = None
    active_sessions_count: int
    sessions: List[CustomerSessionResponse] = []


# ==============================================================================
# 7. Administrative Customer Management Schemas (Module M19)
# ==============================================================================

class AdminCustomerListItem(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str] = None
    status: str
    user_type: str = "customer"
    total_orders: int = 0
    lifetime_spend: Decimal = Decimal("0.00")
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminCustomerListResponse(BaseModel):
    customers: List[AdminCustomerListItem]
    total: int
    page: int
    page_size: int


class AdminCustomerDetailResponse(BaseModel):
    id: int
    email: str
    phone: Optional[str] = None
    status: str
    user_type: str
    email_verified: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime
    profile: Optional[CustomerProfileResponse] = None
    addresses: List[AddressResponse] = Field(default_factory=list)
    total_orders: int = 0
    lifetime_spend: Decimal = Decimal("0.00")
    returns_count: int = 0
    recent_orders: List[Any] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class CustomerStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern=r"^(active|suspended|disabled)$", description="New account status")
    reason: str = Field(..., min_length=3, max_length=255, description="Mandatory reason for status update")
