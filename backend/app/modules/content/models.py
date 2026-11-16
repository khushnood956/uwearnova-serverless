"""
Store Content Domain Models (Module M21)
Defines announcement bars, configurable homepage campaign heroes, and static policy/content pages.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IDMixin, TimestampMixin


class AnnouncementBar(Base, IDMixin, TimestampMixin):
    """
    Top-of-page announcement bar banner for alerts, flash promos, and delivery notices.
    """

    __tablename__ = "announcement_bars"

    message: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Announcement message text (e.g. Free Delivery across Pakistan on orders over Rs. 5,000)",
    )

    link_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional destination link URL",
    )

    bg_color: Mapped[str] = mapped_column(
        String(32),
        default="#000000",
        nullable=False,
        comment="Hex or CSS background color",
    )

    text_color: Mapped[str] = mapped_column(
        String(32),
        default="#FFFFFF",
        nullable=False,
        comment="Hex or CSS text color",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active banner display flag",
    )

    starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Scheduled banner display start timestamp",
    )

    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Scheduled banner display end timestamp",
    )


class HomepageCampaign(Base, IDMixin, TimestampMixin):
    """
    Curated homepage hero carousel or promotional editorial feature.
    """

    __tablename__ = "homepage_campaigns"

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Campaign headline (e.g. The Winter 2026 Sartorial Edit)",
    )

    subtitle: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Campaign sub-headline or description",
    )

    cta_text: Mapped[Optional[str]] = mapped_column(
        String(64),
        default="Explore Collection",
        nullable=True,
        comment="Call to action button label",
    )

    cta_link: Mapped[Optional[str]] = mapped_column(
        String(255),
        default="/collections/women",
        nullable=True,
        comment="Call to action destination route",
    )

    banner_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Hero image URL or S3 asset path",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display sequence ordering",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Campaign visibility flag",
    )


class ContentPage(Base, IDMixin, TimestampMixin):
    """
    CMS page for brand storytelling, customer policies, shipping guidelines, FAQs, etc.
    """

    __tablename__ = "content_pages"

    slug: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique URL slug (e.g. about, shipping-delivery, returns-exchanges, faqs)",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Page headline title",
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Markdown or HTML content body",
    )

    meta_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="SEO title tag",
    )

    meta_description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="SEO meta description snippet",
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Published state toggle",
    )
