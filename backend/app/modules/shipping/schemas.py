"""
Shipping Schemas (M11)
Pydantic schemas for shipping zones, configurable delivery methods,
address validation, and shipping quotes.
"""

from datetime import datetime
from decimal import Decimal
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ===========================================================================
# Delivery Address Schemas
# ===========================================================================

class DeliveryAddressValidationRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=128)
    phone: str = Field(..., min_length=10, max_length=20, description="Customer phone number (e.g. 03001234567)")
    address_line_1: str = Field(..., min_length=5, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=2, max_length=128)
    postal_code: Optional[str] = Field(None, max_length=16)
    country_code: str = Field(default="PK", min_length=2, max_length=2)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        # Check standard Pakistan phone patterns (03... or +923... or 923...)
        if not re.match(r"^(\+?92|0)?3[0-9]{9}$", cleaned):
            raise ValueError("Invalid Pakistani mobile number format. Expected format: 03XXXXXXXXX or +923XXXXXXXXX")
        return cleaned


class DeliveryAddressValidationResponse(BaseModel):
    is_valid: bool
    city: str
    is_serviceable: bool
    zone_code: Optional[str] = None
    normalized_phone: str
    message: Optional[str] = None


# ===========================================================================
# Shipping Zone Schemas
# ===========================================================================

class ShippingZoneBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    code: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = Field(None, max_length=255)
    cities: List[str] = Field(default_factory=list)
    is_active: bool = True


class ShippingZoneCreate(ShippingZoneBase):
    pass


class ShippingZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    description: Optional[str] = None
    cities: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ShippingZoneResponse(ShippingZoneBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# Shipping Method Schemas
# ===========================================================================

class ShippingMethodBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    code: str = Field(..., min_length=2, max_length=64)
    zone_id: Optional[int] = Field(None, description="Target zone constraint or null for nationwide")
    description: Optional[str] = Field(None, max_length=255)
    base_fee: Decimal = Field(default=Decimal("350.00"), ge=0)
    free_shipping_threshold: Optional[Decimal] = Field(default=Decimal("15000.00"), ge=0)
    estimated_days_min: int = Field(default=2, ge=0)
    estimated_days_max: int = Field(default=4, ge=1)
    is_cod_supported: bool = True
    is_active: bool = True
    sort_order: int = 0


class ShippingMethodCreate(ShippingMethodBase):
    pass


class ShippingMethodUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    description: Optional[str] = None
    zone_id: Optional[int] = None
    base_fee: Optional[Decimal] = Field(None, ge=0)
    free_shipping_threshold: Optional[Decimal] = Field(None, ge=0)
    estimated_days_min: Optional[int] = Field(None, ge=0)
    estimated_days_max: Optional[int] = Field(None, ge=1)
    is_cod_supported: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ShippingMethodResponse(ShippingMethodBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# Shipping Quote Schemas
# ===========================================================================

class ShippingQuoteRequest(BaseModel):
    city: str = Field(..., min_length=2, max_length=128)
    postal_code: Optional[str] = Field(None, max_length=16)
    country_code: str = Field(default="PK", min_length=2, max_length=2)
    subtotal: Optional[Decimal] = Field(None, ge=0, description="Order subtotal; if omitted, resolved from active cart")
    is_cod: bool = Field(default=False, description="Whether Cash on Delivery is requested")


class ShippingMethodQuoteItem(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    estimated_days_min: int
    estimated_days_max: int
    is_cod_supported: bool
    base_fee: Decimal
    discount: Decimal
    final_fee: Decimal
    is_free: bool
    free_shipping_threshold: Optional[Decimal] = None
    amount_needed_for_free_shipping: Optional[Decimal] = None


class ShippingQuoteResponse(BaseModel):
    destination_city: str
    is_serviceable: bool
    zone_code: Optional[str] = None
    subtotal: Decimal
    available_methods: List[ShippingMethodQuoteItem]
    recommended_method_code: str
