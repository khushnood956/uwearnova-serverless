"""
Store Content Service Layer (Module M21)
Implements business logic and administrative management for announcements,
homepage campaigns, and content pages.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.content.models import AnnouncementBar, ContentPage, HomepageCampaign
from app.modules.content.schemas import (
    AnnouncementBarCreateRequest,
    AnnouncementBarResponse,
    AnnouncementBarUpdateRequest,
    ContentPageCreateRequest,
    ContentPageResponse,
    ContentPageUpdateRequest,
    HomepageCampaignCreateRequest,
    HomepageCampaignResponse,
    HomepageCampaignUpdateRequest,
)


# ---------------------------------------------------------
# Announcement Bars
# ---------------------------------------------------------

async def get_active_announcements(db: AsyncSession) -> List[AnnouncementBarResponse]:
    """Retrieve active announcement bars for storefront banner display."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(AnnouncementBar)
        .where(AnnouncementBar.is_active.is_(True))
        .order_by(AnnouncementBar.id.desc())
    )
    res = await db.execute(stmt)
    bars = res.scalars().all()

    # Filter by schedule if start/end times specified
    valid_bars = []
    for b in bars:
        if b.starts_at:
            st = b.starts_at if b.starts_at.tzinfo else b.starts_at.replace(tzinfo=timezone.utc)
            if now < st:
                continue
        if b.ends_at:
            en = b.ends_at if b.ends_at.tzinfo else b.ends_at.replace(tzinfo=timezone.utc)
            if now > en:
                continue
        valid_bars.append(AnnouncementBarResponse.model_validate(b))

    return valid_bars


async def create_announcement_bar(
    db: AsyncSession,
    req: AnnouncementBarCreateRequest,
    actor_user: User,
) -> AnnouncementBarResponse:
    """Create announcement bar banner with audit logging."""
    bar = AnnouncementBar(
        message=req.message,
        link_url=req.link_url,
        bg_color=req.bg_color,
        text_color=req.text_color,
        is_active=req.is_active,
        starts_at=req.starts_at,
        ends_at=req.ends_at,
    )
    db.add(bar)
    await db.flush()

    await log_audit_event(
        db=db,
        action="content.announcement_created",
        entity_type="announcement_bar",
        entity_id=str(bar.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"message": bar.message},
    )

    return AnnouncementBarResponse.model_validate(bar)


async def list_announcements_admin(db: AsyncSession) -> List[AnnouncementBarResponse]:
    """List all announcement bars for administration."""
    stmt = select(AnnouncementBar).order_by(AnnouncementBar.id.desc())
    res = await db.execute(stmt)
    return [AnnouncementBarResponse.model_validate(b) for b in res.scalars().all()]


async def update_announcement_bar(
    db: AsyncSession,
    bar_id: int,
    req: AnnouncementBarUpdateRequest,
    actor_user: User,
) -> AnnouncementBarResponse:
    """Update announcement bar with audit logging."""
    stmt = select(AnnouncementBar).where(AnnouncementBar.id == bar_id)
    res = await db.execute(stmt)
    bar = res.scalar_one_or_none()
    if not bar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Announcement bar ID {bar_id} not found",
        )

    updates = req.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(bar, field, value)

    await db.flush()

    await log_audit_event(
        db=db,
        action="content.announcement_updated",
        entity_type="announcement_bar",
        entity_id=str(bar.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"updated_fields": list(updates.keys())},
    )

    return AnnouncementBarResponse.model_validate(bar)


async def delete_announcement_bar(
    db: AsyncSession,
    bar_id: int,
    actor_user: User,
) -> dict:
    """Delete announcement bar."""
    stmt = select(AnnouncementBar).where(AnnouncementBar.id == bar_id)
    res = await db.execute(stmt)
    bar = res.scalar_one_or_none()
    if not bar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Announcement bar ID {bar_id} not found",
        )

    await db.delete(bar)
    await db.flush()

    await log_audit_event(
        db=db,
        action="content.announcement_deleted",
        entity_type="announcement_bar",
        entity_id=str(bar_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
    )

    return {"success": True, "message": f"Announcement bar ID {bar_id} deleted"}


# ---------------------------------------------------------
# Homepage Campaigns
# ---------------------------------------------------------

async def get_active_homepage_campaigns(db: AsyncSession) -> List[HomepageCampaignResponse]:
    """Retrieve active homepage hero campaigns ordered by display sequence."""
    stmt = (
        select(HomepageCampaign)
        .where(HomepageCampaign.is_active.is_(True))
        .order_by(HomepageCampaign.sort_order.asc(), HomepageCampaign.id.desc())
    )
    res = await db.execute(stmt)
    return [HomepageCampaignResponse.model_validate(c) for c in res.scalars().all()]


async def create_homepage_campaign(
    db: AsyncSession,
    req: HomepageCampaignCreateRequest,
    actor_user: User,
) -> HomepageCampaignResponse:
    """Create homepage hero campaign with audit logging."""
    campaign = HomepageCampaign(
        title=req.title,
        subtitle=req.subtitle,
        cta_text=req.cta_text,
        cta_link=req.cta_link,
        banner_image_url=req.banner_image_url,
        sort_order=req.sort_order,
        is_active=req.is_active,
    )
    db.add(campaign)
    await db.flush()

    await log_audit_event(
        db=db,
        action="content.campaign_created",
        entity_type="homepage_campaign",
        entity_id=str(campaign.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"title": campaign.title},
    )

    return HomepageCampaignResponse.model_validate(campaign)


async def list_homepage_campaigns_admin(db: AsyncSession) -> List[HomepageCampaignResponse]:
    """List all homepage campaigns for administration."""
    stmt = select(HomepageCampaign).order_by(HomepageCampaign.sort_order.asc(), HomepageCampaign.id.desc())
    res = await db.execute(stmt)
    return [HomepageCampaignResponse.model_validate(c) for c in res.scalars().all()]


async def update_homepage_campaign(
    db: AsyncSession,
    campaign_id: int,
    req: HomepageCampaignUpdateRequest,
    actor_user: User,
) -> HomepageCampaignResponse:
    """Update homepage campaign with audit logging."""
    stmt = select(HomepageCampaign).where(HomepageCampaign.id == campaign_id)
    res = await db.execute(stmt)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Homepage campaign ID {campaign_id} not found",
        )

    updates = req.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(campaign, field, value)

    await db.flush()

    await log_audit_event(
        db=db,
        action="content.campaign_updated",
        entity_type="homepage_campaign",
        entity_id=str(campaign.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"title": campaign.title, "updated_fields": list(updates.keys())},
    )

    return HomepageCampaignResponse.model_validate(campaign)


async def delete_homepage_campaign(
    db: AsyncSession,
    campaign_id: int,
    actor_user: User,
) -> dict:
    """Delete homepage campaign."""
    stmt = select(HomepageCampaign).where(HomepageCampaign.id == campaign_id)
    res = await db.execute(stmt)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Homepage campaign ID {campaign_id} not found",
        )

    await db.delete(campaign)
    await db.flush()

    await log_audit_event(
        db=db,
        action="content.campaign_deleted",
        entity_type="homepage_campaign",
        entity_id=str(campaign_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
    )

    return {"success": True, "message": f"Homepage campaign ID {campaign_id} deleted"}


# ---------------------------------------------------------
# Content Pages
# ---------------------------------------------------------

async def get_published_content_page(db: AsyncSession, slug: str) -> ContentPageResponse:
    """Retrieve published content page for storefront viewing."""
    stmt = select(ContentPage).where(ContentPage.slug == slug.lower(), ContentPage.is_published.is_(True))
    res = await db.execute(stmt)
    page = res.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content page '{slug}' not found",
        )
    return ContentPageResponse.model_validate(page)


async def create_content_page(
    db: AsyncSession,
    req: ContentPageCreateRequest,
    actor_user: User,
) -> ContentPageResponse:
    """Create content page with unique slug validation and audit logging."""
    slug = req.slug.lower().strip()
    existing_stmt = select(ContentPage).where(ContentPage.slug == slug)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Content page with slug '{slug}' already exists",
        )

    page = ContentPage(
        slug=slug,
        title=req.title,
        body=req.body,
        meta_title=req.meta_title,
        meta_description=req.meta_description,
        is_published=req.is_published,
    )
    db.add(page)
    await db.flush()

    await log_audit_event(
        db=db,
        action="content.page_created",
        entity_type="content_page",
        entity_id=str(page.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"slug": page.slug, "title": page.title},
    )

    return ContentPageResponse.model_validate(page)


async def list_content_pages_admin(db: AsyncSession) -> List[ContentPageResponse]:
    """List all content pages for administration."""
    stmt = select(ContentPage).order_by(ContentPage.slug.asc())
    res = await db.execute(stmt)
    return [ContentPageResponse.model_validate(p) for p in res.scalars().all()]


async def get_content_page_admin(db: AsyncSession, page_id: int) -> ContentPageResponse:
    """Get content page by ID."""
    stmt = select(ContentPage).where(ContentPage.id == page_id)
    res = await db.execute(stmt)
    page = res.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content page ID {page_id} not found",
        )
    return ContentPageResponse.model_validate(page)


async def update_content_page(
    db: AsyncSession,
    page_id: int,
    req: ContentPageUpdateRequest,
    actor_user: User,
) -> ContentPageResponse:
    """Update content page with audit logging."""
    stmt = select(ContentPage).where(ContentPage.id == page_id)
    res = await db.execute(stmt)
    page = res.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content page ID {page_id} not found",
        )

    updates = req.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(page, field, value)

    await db.flush()

    await log_audit_event(
        db=db,
        action="content.page_updated",
        entity_type="content_page",
        entity_id=str(page.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"slug": page.slug, "updated_fields": list(updates.keys())},
    )

    return ContentPageResponse.model_validate(page)


async def delete_content_page(
    db: AsyncSession,
    page_id: int,
    actor_user: User,
) -> dict:
    """Delete content page."""
    stmt = select(ContentPage).where(ContentPage.id == page_id)
    res = await db.execute(stmt)
    page = res.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content page ID {page_id} not found",
        )

    slug = page.slug
    await db.delete(page)
    await db.flush()

    await log_audit_event(
        db=db,
        action="content.page_deleted",
        entity_type="content_page",
        entity_id=str(page_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"slug": slug},
    )

    return {"success": True, "message": f"Content page '{slug}' deleted"}
