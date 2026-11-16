"""
Store Content API Routers (Module M21)
Provides public storefront content access and protected administrative content management.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
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
from app.modules.content.service import (
    create_announcement_bar,
    create_content_page,
    create_homepage_campaign,
    delete_announcement_bar,
    delete_content_page,
    delete_homepage_campaign,
    get_active_announcements,
    get_active_homepage_campaigns,
    get_content_page_admin,
    get_published_content_page,
    list_announcements_admin,
    list_content_pages_admin,
    list_homepage_campaigns_admin,
    update_announcement_bar,
    update_content_page,
    update_homepage_campaign,
)
from app.modules.rbac.dependencies import require_permission

public_content_router = APIRouter(prefix="/content", tags=["Store Content"])
admin_content_router = APIRouter(prefix="/admin/content", tags=["Admin Content"])


# ---------------------------------------------------------
# Public Storefront Content Access
# ---------------------------------------------------------

@public_content_router.get(
    "/announcements",
    response_model=List[AnnouncementBarResponse],
    summary="Get active announcement bars",
)
async def get_announcements(db: AsyncSession = Depends(get_db)):
    """Retrieve active announcement bars for storefront header display."""
    return await get_active_announcements(db=db)


@public_content_router.get(
    "/homepage-campaigns",
    response_model=List[HomepageCampaignResponse],
    summary="Get active homepage campaigns",
)
async def get_homepage_campaigns(db: AsyncSession = Depends(get_db)):
    """Retrieve active homepage hero banners in display sequence order."""
    return await get_active_homepage_campaigns(db=db)


@public_content_router.get(
    "/pages/{slug}",
    response_model=ContentPageResponse,
    summary="Get published content page by slug",
)
async def get_page(slug: str, db: AsyncSession = Depends(get_db)):
    """Retrieve published content page by URL slug (e.g. about, faqs, shipping-delivery)."""
    return await get_published_content_page(db=db, slug=slug)


# ---------------------------------------------------------
# Administrative Announcement Bars Management
# ---------------------------------------------------------

@admin_content_router.post(
    "/announcements",
    response_model=AnnouncementBarResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create announcement bar",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_create_announcement(
    req: AnnouncementBarCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new announcement bar banner."""
    return await create_announcement_bar(db=db, req=req, actor_user=current_user)


@admin_content_router.get(
    "/announcements",
    response_model=List[AnnouncementBarResponse],
    summary="List all announcement bars",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_list_announcements(db: AsyncSession = Depends(get_db)):
    """List all announcement bars."""
    return await list_announcements_admin(db=db)


@admin_content_router.put(
    "/announcements/{bar_id}",
    response_model=AnnouncementBarResponse,
    summary="Update announcement bar",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_update_announcement(
    bar_id: int,
    req: AnnouncementBarUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update announcement bar message, style, or schedule."""
    return await update_announcement_bar(db=db, bar_id=bar_id, req=req, actor_user=current_user)


@admin_content_router.delete(
    "/announcements/{bar_id}",
    summary="Delete announcement bar",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_delete_announcement(
    bar_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete announcement bar."""
    return await delete_announcement_bar(db=db, bar_id=bar_id, actor_user=current_user)


# ---------------------------------------------------------
# Administrative Homepage Campaigns Management
# ---------------------------------------------------------

@admin_content_router.post(
    "/homepage-campaigns",
    response_model=HomepageCampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create homepage campaign",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_create_campaign(
    req: HomepageCampaignCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a homepage hero banner or campaign."""
    return await create_homepage_campaign(db=db, req=req, actor_user=current_user)


@admin_content_router.get(
    "/homepage-campaigns",
    response_model=List[HomepageCampaignResponse],
    summary="List all homepage campaigns",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_list_campaigns(db: AsyncSession = Depends(get_db)):
    """List all homepage campaigns."""
    return await list_homepage_campaigns_admin(db=db)


@admin_content_router.put(
    "/homepage-campaigns/{campaign_id}",
    response_model=HomepageCampaignResponse,
    summary="Update homepage campaign",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_update_campaign(
    campaign_id: int,
    req: HomepageCampaignUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update homepage campaign details, image, or order."""
    return await update_homepage_campaign(db=db, campaign_id=campaign_id, req=req, actor_user=current_user)


@admin_content_router.delete(
    "/homepage-campaigns/{campaign_id}",
    summary="Delete homepage campaign",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete homepage campaign."""
    return await delete_homepage_campaign(db=db, campaign_id=campaign_id, actor_user=current_user)


# ---------------------------------------------------------
# Administrative Content Pages Management
# ---------------------------------------------------------

@admin_content_router.post(
    "/pages",
    response_model=ContentPageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create content page",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_create_page(
    req: ContentPageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new policy or content page."""
    return await create_content_page(db=db, req=req, actor_user=current_user)


@admin_content_router.get(
    "/pages",
    response_model=List[ContentPageResponse],
    summary="List all content pages",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_list_pages(db: AsyncSession = Depends(get_db)):
    """List all content pages."""
    return await list_content_pages_admin(db=db)


@admin_content_router.get(
    "/pages/{page_id}",
    response_model=ContentPageResponse,
    summary="Get content page by ID",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_get_page(page_id: int, db: AsyncSession = Depends(get_db)):
    """Get content page details by ID."""
    return await get_content_page_admin(db=db, page_id=page_id)


@admin_content_router.put(
    "/pages/{page_id}",
    response_model=ContentPageResponse,
    summary="Update content page",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_update_page(
    page_id: int,
    req: ContentPageUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update content page body, title, or metadata."""
    return await update_content_page(db=db, page_id=page_id, req=req, actor_user=current_user)


@admin_content_router.delete(
    "/pages/{page_id}",
    summary="Delete content page",
    dependencies=[Depends(require_permission("content.manage"))],
)
async def admin_delete_page(
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete content page."""
    return await delete_content_page(db=db, page_id=page_id, actor_user=current_user)
