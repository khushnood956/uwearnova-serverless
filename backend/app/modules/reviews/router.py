"""
Product Reviews API Routers (Module M21)
Provides public review submission/listing and protected administrative review moderation.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.models import User
from app.modules.rbac.dependencies import require_permission
from app.modules.reviews.schemas import (
    AdminReviewListResponse,
    AdminReviewItem,
    PublicReviewItem,
    PublicReviewListResponse,
    ReviewModerateRequest,
    ReviewSubmitRequest,
)
from app.modules.reviews.service import (
    list_approved_reviews,
    list_reviews_admin,
    moderate_review,
    submit_product_review,
)

public_reviews_router = APIRouter(prefix="/products", tags=["Product Reviews"])
admin_reviews_router = APIRouter(prefix="/admin/reviews", tags=["Admin Reviews"])


# ---------------------------------------------------------
# Public Product Reviews
# ---------------------------------------------------------

@public_reviews_router.get(
    "/{product_id_or_slug}/reviews",
    response_model=PublicReviewListResponse,
    summary="List approved customer reviews for a product",
)
async def get_product_reviews(
    product_id_or_slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List approved reviews and aggregated score distribution on storefront."""
    return await list_approved_reviews(db=db, product_id_or_slug=product_id_or_slug, page=page, page_size=page_size)


@public_reviews_router.post(
    "/{product_id_or_slug}/reviews",
    response_model=PublicReviewItem,
    status_code=status.HTTP_201_CREATED,
    summary="Submit product review for moderation",
)
async def post_product_review(
    product_id_or_slug: str,
    req: ReviewSubmitRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit product review.
    Detects verified purchaser status if caller has ordered this product.
    Reviews enter pending status until administratively approved.
    """
    return await submit_product_review(
        db=db,
        product_id_or_slug=product_id_or_slug,
        req=req,
        current_user=current_user,
    )


# ---------------------------------------------------------
# Administrative Review Moderation
# ---------------------------------------------------------

@admin_reviews_router.get(
    "",
    response_model=AdminReviewListResponse,
    summary="List reviews across all products for moderation",
    dependencies=[Depends(require_permission("reviews.moderate"))],
)
async def admin_list_reviews(
    status: Optional[str] = Query(None, description="Filter: pending, approved, rejected, hidden"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    rating: Optional[int] = Query(None, description="Filter by star rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List customer reviews with moderation filters."""
    return await list_reviews_admin(
        db=db,
        status_filter=status,
        product_id=product_id,
        rating=rating,
        page=page,
        page_size=page_size,
    )


@admin_reviews_router.post(
    "/{review_id}/moderate",
    response_model=AdminReviewItem,
    summary="Approve, reject, or hide customer review",
    dependencies=[Depends(require_permission("reviews.moderate"))],
)
async def admin_moderate_review(
    review_id: int,
    req: ReviewModerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Moderate review decision (approve/reject/hide) and update parent product rating aggregates."""
    return await moderate_review(
        db=db,
        review_id=review_id,
        req=req,
        actor_user=current_user,
    )
