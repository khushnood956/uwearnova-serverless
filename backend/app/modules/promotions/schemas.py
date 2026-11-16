"""
Promotions and Coupons Pydantic Schemas (Module M21)
Defines validation and administrative management request/response models.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------
# Customer / Storefront Validation Schemas
# ---------------------------------------------------------

class CouponValidationRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    subtotal: Decimal = Field(..., ge=0)
    customer_email: EmailStr


class CouponValidationResponse(BaseModel):
    is_valid: bool
    code: str
    discount_type: str
    discount_amount: Decimal
    new_subtotal: Decimal
    message: Optional[str] = None


# ---------------------------------------------------------
# Administrative CRUD Schemas
# ---------------------------------------------------------

class CouponCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = Field(None, max_length=255)
    discount_type: str = Field(default="percentage", pattern="^(percentage|fixed_amount|free_shipping)$")
    discount_value: Decimal = Field(..., gt=0)
    max_discount_amount: Optional[Decimal] = Field(None, gt=0)
    min_order_amount: Optional[Decimal] = Field(None, ge=0)
    usage_limit_total: Optional[int] = Field(None, gt=0)
    usage_limit_per_customer: Optional[int] = Field(default=1, gt=0)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True


class CouponUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=255)
    discount_type: Optional[str] = Field(None, pattern="^(percentage|fixed_amount|free_shipping)$")
    discount_value: Optional[Decimal] = Field(None, gt=0)
    max_discount_amount: Optional[Decimal] = Field(None, gt=0)
    min_order_amount: Optional[Decimal] = Field(None, ge=0)
    usage_limit_total: Optional[int] = Field(None, gt=0)
    usage_limit_per_customer: Optional[int] = Field(None, gt=0)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: Decimal
    max_discount_amount: Optional[Decimal] = None
    min_order_amount: Optional[Decimal] = None
    usage_limit_total: Optional[int] = None
    usage_limit_per_customer: Optional[int] = None
    times_redeemed: int
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CouponListResponse(BaseModel):
    items: List[CouponResponse]
    total: int
    page: int
    page_size: int


class CouponRedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coupon_id: int
    order_id: Optional[int] = None
    user_id: Optional[int] = None
    customer_email: str
    discount_amount: Decimal
    redeemed_at: datetime


class CouponRedemptionListResponse(BaseModel):
    items: List[CouponRedemptionResponse]
    total: int
    page: int
    page_size: int
