"""
Product Reviews Pydantic Schemas (Module M21)
Defines customer review submission, product review queries, and moderation contracts.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------
# Customer Review Submission & Public Schemas
# ---------------------------------------------------------

class ReviewSubmitRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=128)
    customer_email: EmailStr
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: str = Field(..., min_length=5)


class PublicReviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    customer_name: str
    rating: int
    title: Optional[str] = None
    comment: str
    is_verified_buyer: bool
    created_at: datetime


class PublicReviewListResponse(BaseModel):
    items: List[PublicReviewItem]
    total: int
    average_rating: Decimal
    rating_distribution: dict
    page: int
    page_size: int


# ---------------------------------------------------------
# Administrative Moderation Schemas
# ---------------------------------------------------------

class ReviewModerateRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|hide)$")
    admin_notes: Optional[str] = None


class AdminReviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_slug: str
    user_id: Optional[int] = None
    customer_name: str
    customer_email: str
    rating: int
    title: Optional[str] = None
    comment: str
    status: str
    is_verified_buyer: bool
    admin_notes: Optional[str] = None
    moderated_by_user_id: Optional[int] = None
    moderated_at: Optional[datetime] = None
    created_at: datetime


class AdminReviewListResponse(BaseModel):
    items: List[AdminReviewItem]
    total: int
    page: int
    page_size: int
