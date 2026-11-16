"""
Store Content Pydantic Schemas (Module M21)
Defines contracts for announcement bars, homepage campaigns, and content pages.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------
# Announcement Bar Schemas
# ---------------------------------------------------------

class AnnouncementBarCreateRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=255)
    link_url: Optional[str] = Field(None, max_length=500)
    bg_color: str = Field(default="#000000", max_length=32)
    text_color: str = Field(default="#FFFFFF", max_length=32)
    is_active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class AnnouncementBarUpdateRequest(BaseModel):
    message: Optional[str] = Field(None, min_length=3, max_length=255)
    link_url: Optional[str] = Field(None, max_length=500)
    bg_color: Optional[str] = Field(None, max_length=32)
    text_color: Optional[str] = Field(None, max_length=32)
    is_active: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class AnnouncementBarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    link_url: Optional[str] = None
    bg_color: str
    text_color: str
    is_active: bool
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------
# Homepage Campaign Schemas
# ---------------------------------------------------------

class HomepageCampaignCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=255)
    cta_text: Optional[str] = Field(default="Explore Collection", max_length=64)
    cta_link: Optional[str] = Field(default="/collections/women", max_length=255)
    banner_image_url: Optional[str] = Field(None, max_length=500)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class HomepageCampaignUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=255)
    cta_text: Optional[str] = Field(None, max_length=64)
    cta_link: Optional[str] = Field(None, max_length=255)
    banner_image_url: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class HomepageCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subtitle: Optional[str] = None
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    banner_image_url: Optional[str] = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------
# Content Page Schemas
# ---------------------------------------------------------

class ContentPageCreateRequest(BaseModel):
    slug: str = Field(..., min_length=2, max_length=128, pattern="^[a-z0-9-]+$")
    title: str = Field(..., min_length=2, max_length=255)
    body: str = Field(..., min_length=5)
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)
    is_published: bool = True


class ContentPageUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    body: Optional[str] = Field(None, min_length=5)
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)
    is_published: Optional[bool] = None


class ContentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    body: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    is_published: bool
    created_at: datetime
    updated_at: datetime
