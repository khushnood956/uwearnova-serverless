"""
Promotions and Coupons API Routers (Module M21)
Provides public storefront coupon validation and protected administrative coupon CRUD.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.promotions.schemas import (
    CouponCreateRequest,
    CouponListResponse,
    CouponRedemptionListResponse,
    CouponResponse,
    CouponUpdateRequest,
    CouponValidationRequest,
    CouponValidationResponse,
)
from app.modules.promotions.service import (
    create_coupon,
    delete_coupon,
    get_coupon,
    list_coupon_redemptions,
    list_coupons,
    update_coupon,
    validate_coupon_endpoint,
)
from app.modules.rbac.dependencies import require_permission

public_promotions_router = APIRouter(prefix="/promotions", tags=["Promotions & Coupons"])
admin_promotions_router = APIRouter(prefix="/admin/coupons", tags=["Admin Promotions"])


# ---------------------------------------------------------
# Public Storefront Coupon Validation
# ---------------------------------------------------------

@public_promotions_router.post(
    "/validate",
    response_model=CouponValidationResponse,
    summary="Validate coupon code and preview server-calculated discount",
)
async def validate_coupon(
    req: CouponValidationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate promotional coupon against cart subtotal and customer identity.
    Calculates exact discount on the server without trusting client input.
    """
    return await validate_coupon_endpoint(
        db=db,
        code=req.code,
        subtotal=req.subtotal,
        customer_email=req.customer_email,
    )


# ---------------------------------------------------------
# Administrative Coupon Management
# ---------------------------------------------------------

@admin_promotions_router.post(
    "",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create promotional coupon",
    dependencies=[Depends(require_permission("promotions.manage"))],
)
async def admin_create_coupon(
    req: CouponCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new promotional coupon rule."""
    return await create_coupon(db=db, req=req, actor_user=current_user)


@admin_promotions_router.get(
    "",
    response_model=CouponListResponse,
    summary="List promotional coupons",
    dependencies=[Depends(require_permission("promotions.manage"))],
)
async def admin_list_coupons(
    is_active: Optional[bool] = Query(None, description="Filter active/inactive"),
    search: Optional[str] = Query(None, description="Search by code"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List coupons with pagination and search."""
    return await list_coupons(db=db, is_active=is_active, search=search, page=page, page_size=page_size)


@admin_promotions_router.get(
    "/{coupon_id}",
    response_model=CouponResponse,
    summary="Get coupon details",
    dependencies=[Depends(require_permission("promotions.manage"))],
)
async def admin_get_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get coupon by ID."""
    return await get_coupon(db=db, coupon_id=coupon_id)


@admin_promotions_router.put(
    "/{coupon_id}",
    response_model=CouponResponse,
    summary="Update promotional coupon",
    dependencies=[Depends(require_permission("promotions.manage"))],
)
async def admin_update_coupon(
    coupon_id: int,
    req: CouponUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update promotional coupon rules and limits."""
    return await update_coupon(db=db, coupon_id=coupon_id, req=req, actor_user=current_user)


@admin_promotions_router.delete(
    "/{coupon_id}",
    summary="Deactivate promotional coupon",
    dependencies=[Depends(require_permission("promotions.manage"))],
)
async def admin_delete_coupon(
    coupon_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate coupon."""
    return await delete_coupon(db=db, coupon_id=coupon_id, actor_user=current_user)


@admin_promotions_router.get(
    "/{coupon_id}/redemptions",
    response_model=CouponRedemptionListResponse,
    summary="List redemptions for a coupon",
    dependencies=[Depends(require_permission("promotions.manage"))],
)
async def admin_list_redemptions(
    coupon_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List redemption history for a specific coupon."""
    return await list_coupon_redemptions(db=db, coupon_id=coupon_id, page=page, page_size=page_size)
