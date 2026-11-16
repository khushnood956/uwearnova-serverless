"""
Promotions and Coupons Service Layer (Module M21)
Implements server-side discount validation, usage quota enforcement,
coupon lifecycle management, and redemption recording.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.promotions.models import Coupon, CouponRedemption
from app.modules.promotions.schemas import (
    CouponCreateRequest,
    CouponListResponse,
    CouponRedemptionListResponse,
    CouponRedemptionResponse,
    CouponResponse,
    CouponUpdateRequest,
    CouponValidationResponse,
)


def _normalize_coupon_code(code: str) -> str:
    """Normalize coupon code to uppercase and strip whitespace."""
    return code.strip().upper()


async def evaluate_coupon(
    db: AsyncSession,
    code: str,
    subtotal: Decimal,
    customer_email: str,
    user_id: Optional[int] = None,
) -> Tuple[bool, Optional[Coupon], Decimal, str]:
    """
    Core backend promotion validation engine.
    Never trusts client-submitted discount amounts.
    Returns (is_valid, coupon, discount_amount, message).
    """
    norm_code = _normalize_coupon_code(code)
    stmt = select(Coupon).where(Coupon.code == norm_code)
    res = await db.execute(stmt)
    coupon = res.scalar_one_or_none()

    if not coupon:
        return False, None, Decimal("0.00"), f"Coupon code '{norm_code}' not found"

    if not coupon.is_active:
        return False, coupon, Decimal("0.00"), "Coupon is currently inactive"

    now = datetime.now(timezone.utc)
    if coupon.starts_at:
        starts = coupon.starts_at if coupon.starts_at.tzinfo else coupon.starts_at.replace(tzinfo=timezone.utc)
        if now < starts:
            return False, coupon, Decimal("0.00"), "Coupon promotion has not started yet"

    if coupon.expires_at:
        expires = coupon.expires_at if coupon.expires_at.tzinfo else coupon.expires_at.replace(tzinfo=timezone.utc)
        if now > expires:
            return False, coupon, Decimal("0.00"), "Coupon has expired"

    if coupon.min_order_amount and subtotal < coupon.min_order_amount:
        return (
            False,
            coupon,
            Decimal("0.00"),
            f"Minimum order subtotal of PKR {coupon.min_order_amount:,.2f} required to use this coupon",
        )

    if coupon.usage_limit_total and coupon.times_redeemed >= coupon.usage_limit_total:
        return False, coupon, Decimal("0.00"), "Coupon usage limit has been reached"

    # Per-customer usage limit
    if coupon.usage_limit_per_customer:
        c_filter = [CouponRedemption.customer_email == customer_email.lower()]
        if user_id:
            c_filter.append(CouponRedemption.user_id == user_id)

        redemptions_query = select(func.count(CouponRedemption.id)).where(
            CouponRedemption.coupon_id == coupon.id,
            or_(*c_filter),
        )
        r_res = await db.execute(redemptions_query)
        customer_redemptions = r_res.scalar() or 0

        if customer_redemptions >= coupon.usage_limit_per_customer:
            return False, coupon, Decimal("0.00"), "You have reached the maximum redemptions for this coupon"

    # Calculate discount
    discount_amount = Decimal("0.00")
    if coupon.discount_type == "percentage":
        discount_amount = (subtotal * coupon.discount_value / Decimal("100.00")).quantize(Decimal("0.01"))
        if coupon.max_discount_amount and discount_amount > coupon.max_discount_amount:
            discount_amount = coupon.max_discount_amount
    elif coupon.discount_type == "fixed_amount":
        discount_amount = min(coupon.discount_value, subtotal)
    elif coupon.discount_type == "free_shipping":
        discount_amount = Decimal("0.00")  # Shipping fee waived in shipping quote

    return True, coupon, discount_amount, "Coupon applied successfully"


async def validate_coupon_endpoint(
    db: AsyncSession,
    code: str,
    subtotal: Decimal,
    customer_email: str,
) -> CouponValidationResponse:
    """Public storefront validation endpoint handler."""
    is_valid, coupon, discount, message = await evaluate_coupon(
        db=db,
        code=code,
        subtotal=subtotal,
        customer_email=customer_email,
    )

    new_subtotal = max(Decimal("0.00"), subtotal - discount)
    return CouponValidationResponse(
        is_valid=is_valid,
        code=_normalize_coupon_code(code),
        discount_type=coupon.discount_type if coupon else "percentage",
        discount_amount=discount,
        new_subtotal=new_subtotal,
        message=message,
    )


async def record_redemption(
    db: AsyncSession,
    coupon: Coupon,
    order_id: Optional[int],
    user_id: Optional[int],
    customer_email: str,
    discount_amount: Decimal,
) -> CouponRedemption:
    """Record an immutable coupon redemption entry and increment counter."""
    redemption = CouponRedemption(
        coupon_id=coupon.id,
        order_id=order_id,
        user_id=user_id,
        customer_email=customer_email.lower(),
        discount_amount=discount_amount,
    )
    db.add(redemption)
    coupon.times_redeemed += 1
    await db.flush()
    return redemption


# ---------------------------------------------------------
# Administrative CRUD Operations
# ---------------------------------------------------------

async def create_coupon(
    db: AsyncSession,
    req: CouponCreateRequest,
    actor_user: User,
) -> CouponResponse:
    """Create a new promotional coupon with audit logging."""
    norm_code = _normalize_coupon_code(req.code)

    # Check for existing code
    existing_stmt = select(Coupon).where(Coupon.code == norm_code)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Coupon code '{norm_code}' already exists",
        )

    coupon = Coupon(
        code=norm_code,
        description=req.description,
        discount_type=req.discount_type,
        discount_value=req.discount_value,
        max_discount_amount=req.max_discount_amount,
        min_order_amount=req.min_order_amount,
        usage_limit_total=req.usage_limit_total,
        usage_limit_per_customer=req.usage_limit_per_customer,
        starts_at=req.starts_at,
        expires_at=req.expires_at,
        is_active=req.is_active,
    )
    db.add(coupon)
    await db.flush()

    await log_audit_event(
        db=db,
        action="promotions.coupon_created",
        entity_type="coupon",
        entity_id=str(coupon.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": str(coupon.discount_value),
        },
    )

    return CouponResponse.model_validate(coupon)


async def list_coupons(
    db: AsyncSession,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> CouponListResponse:
    """List promotional coupons with search and filtering."""
    query = select(Coupon)

    if is_active is not None:
        query = query.where(Coupon.is_active == is_active)
    if search:
        query = query.where(Coupon.code.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(Coupon.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    coupons = result.scalars().all()

    items = [CouponResponse.model_validate(c) for c in coupons]
    return CouponListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_coupon(db: AsyncSession, coupon_id: int) -> CouponResponse:
    """Retrieve coupon details."""
    stmt = select(Coupon).where(Coupon.id == coupon_id)
    res = await db.execute(stmt)
    coupon = res.scalar_one_or_none()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon ID {coupon_id} not found",
        )
    return CouponResponse.model_validate(coupon)


async def update_coupon(
    db: AsyncSession,
    coupon_id: int,
    req: CouponUpdateRequest,
    actor_user: User,
) -> CouponResponse:
    """Update promotional coupon rules with audit logging."""
    stmt = select(Coupon).where(Coupon.id == coupon_id)
    res = await db.execute(stmt)
    coupon = res.scalar_one_or_none()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon ID {coupon_id} not found",
        )

    updates = req.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(coupon, field, value)

    await db.flush()

    await log_audit_event(
        db=db,
        action="promotions.coupon_updated",
        entity_type="coupon",
        entity_id=str(coupon.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"code": coupon.code, "updated_fields": list(updates.keys())},
    )

    return CouponResponse.model_validate(coupon)


async def delete_coupon(
    db: AsyncSession,
    coupon_id: int,
    actor_user: User,
) -> dict:
    """Deactivate promotional coupon."""
    stmt = select(Coupon).where(Coupon.id == coupon_id)
    res = await db.execute(stmt)
    coupon = res.scalar_one_or_none()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon ID {coupon_id} not found",
        )

    coupon.is_active = False
    await db.flush()

    await log_audit_event(
        db=db,
        action="promotions.coupon_deactivated",
        entity_type="coupon",
        entity_id=str(coupon.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"code": coupon.code},
    )

    return {"success": True, "message": f"Coupon '{coupon.code}' deactivated successfully"}


async def list_coupon_redemptions(
    db: AsyncSession,
    coupon_id: int,
    page: int = 1,
    page_size: int = 20,
) -> CouponRedemptionListResponse:
    """List redemptions for a specific coupon."""
    query = select(CouponRedemption).where(CouponRedemption.coupon_id == coupon_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(CouponRedemption.redeemed_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    redemptions = result.scalars().all()

    items = [CouponRedemptionResponse.model_validate(r) for r in redemptions]
    return CouponRedemptionListResponse(items=items, total=total, page=page, page_size=page_size)
