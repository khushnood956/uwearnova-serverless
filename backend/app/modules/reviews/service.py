"""
Product Reviews Service Layer (Module M21)
Implements review submission, verified purchaser detection,
rating re-aggregation, and administrative moderation workflows.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.catalog.models import Product
from app.modules.orders.models import Order, OrderItem
from app.modules.reviews.models import ProductReview
from app.modules.reviews.schemas import (
    AdminReviewItem,
    AdminReviewListResponse,
    PublicReviewItem,
    PublicReviewListResponse,
    ReviewModerateRequest,
    ReviewSubmitRequest,
)


async def _resolve_product(db: AsyncSession, product_id_or_slug: str) -> Product:
    """Resolve product instance by integer ID or unique URL slug."""
    query = select(Product)
    if product_id_or_slug.isdigit():
        query = query.where(Product.id == int(product_id_or_slug))
    else:
        query = query.where(Product.slug == product_id_or_slug)

    res = await db.execute(query)
    prod = res.scalar_one_or_none()
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id_or_slug}' not found",
        )
    return prod


async def _check_verified_buyer(
    db: AsyncSession,
    product_id: int,
    customer_email: str,
    user_id: Optional[int] = None,
) -> bool:
    """Check if the customer has placed an order containing this product."""
    c_filters = [Order.customer_email == customer_email.lower()]
    if user_id:
        c_filters.append(Order.user_id == user_id)

    query = (
        select(OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            OrderItem.product_id == product_id,
            or_(*c_filters),
            Order.status.in_(["confirmed", "processing", "packed", "shipped", "delivered"]),
        )
        .limit(1)
    )
    res = await db.execute(query)
    return res.scalar_one_or_none() is not None


async def _recalculate_product_ratings(db: AsyncSession, product_id: int) -> None:
    """Recalculate average rating and review count from approved reviews and update product."""
    stats_query = (
        select(
            func.count(ProductReview.id),
            func.avg(ProductReview.rating),
        )
        .where(
            ProductReview.product_id == product_id,
            ProductReview.status == "approved",
        )
    )
    res = await db.execute(stats_query)
    count, avg_score = res.one()

    p_res = await db.execute(select(Product).where(Product.id == product_id))
    product = p_res.scalar_one_or_none()
    if product:
        product.review_count = count or 0
        product.rating = Decimal(str(round(avg_score, 2))) if avg_score is not None else Decimal("5.00")
        await db.flush()


async def submit_product_review(
    db: AsyncSession,
    product_id_or_slug: str,
    req: ReviewSubmitRequest,
    current_user: Optional[User] = None,
) -> PublicReviewItem:
    """Submit a customer review for moderation."""
    product = await _resolve_product(db, product_id_or_slug)

    is_verified = await _check_verified_buyer(
        db=db,
        product_id=product.id,
        customer_email=req.customer_email,
        user_id=current_user.id if current_user else None,
    )

    review = ProductReview(
        product_id=product.id,
        user_id=current_user.id if current_user else None,
        customer_name=req.customer_name,
        customer_email=req.customer_email.lower(),
        rating=req.rating,
        title=req.title,
        comment=req.comment,
        status="pending",  # Requires administrative moderation
        is_verified_buyer=is_verified,
    )
    db.add(review)
    await db.flush()

    await log_audit_event(
        db=db,
        action="reviews.submitted",
        entity_type="product_review",
        entity_id=str(review.id),
        user_id=current_user.id if current_user else None,
        actor_email=req.customer_email,
        details={
            "product_id": product.id,
            "product_slug": product.slug,
            "rating": req.rating,
            "is_verified_buyer": is_verified,
        },
    )

    return PublicReviewItem.model_validate(review)


async def list_approved_reviews(
    db: AsyncSession,
    product_id_or_slug: str,
    page: int = 1,
    page_size: int = 20,
) -> PublicReviewListResponse:
    """List approved reviews and aggregated ratings for a product on storefront."""
    product = await _resolve_product(db, product_id_or_slug)

    base_query = select(ProductReview).where(
        ProductReview.product_id == product.id,
        ProductReview.status == "approved",
    )

    count_res = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_res.scalar() or 0

    query = base_query.order_by(ProductReview.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    reviews = result.scalars().all()

    # Rating distribution
    dist_query = (
        select(ProductReview.rating, func.count(ProductReview.id))
        .where(
            ProductReview.product_id == product.id,
            ProductReview.status == "approved",
        )
        .group_by(ProductReview.rating)
    )
    dist_res = await db.execute(dist_query)
    dist_map = {row[0]: row[1] for row in dist_res.all()}
    distribution = {str(i): dist_map.get(i, 0) for i in range(1, 6)}

    items = [PublicReviewItem.model_validate(r) for r in reviews]
    return PublicReviewListResponse(
        items=items,
        total=total,
        average_rating=product.rating,
        rating_distribution=distribution,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------
# Administrative Moderation
# ---------------------------------------------------------

async def list_reviews_admin(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    product_id: Optional[int] = None,
    rating: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> AdminReviewListResponse:
    """Administrative review queue with filters."""
    query = select(ProductReview).options(selectinload(ProductReview.product))

    if status_filter:
        query = query.where(ProductReview.status == status_filter)
    if product_id:
        query = query.where(ProductReview.product_id == product_id)
    if rating:
        query = query.where(ProductReview.rating == rating)

    count_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_res.scalar() or 0

    query = query.order_by(ProductReview.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    reviews = result.scalars().all()

    items = [
        AdminReviewItem(
            id=r.id,
            product_id=r.product_id,
            product_name=r.product.name if r.product else "Unknown Product",
            product_slug=r.product.slug if r.product else "",
            user_id=r.user_id,
            customer_name=r.customer_name,
            customer_email=r.customer_email,
            rating=r.rating,
            title=r.title,
            comment=r.comment,
            status=r.status,
            is_verified_buyer=r.is_verified_buyer,
            admin_notes=r.admin_notes,
            moderated_by_user_id=r.moderated_by_user_id,
            moderated_at=r.moderated_at,
            created_at=r.created_at,
        )
        for r in reviews
    ]

    return AdminReviewListResponse(items=items, total=total, page=page, page_size=page_size)


async def moderate_review(
    db: AsyncSession,
    review_id: int,
    req: ReviewModerateRequest,
    actor_user: User,
) -> AdminReviewItem:
    """Approve, reject, or hide customer review and update product rating aggregates."""
    query = select(ProductReview).options(selectinload(ProductReview.product)).where(ProductReview.id == review_id)
    res = await db.execute(query)
    review = res.scalar_one_or_none()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product review ID {review_id} not found",
        )

    action_map = {"approve": "approved", "reject": "rejected", "hide": "hidden"}
    target_status = action_map[req.action]

    review.status = target_status
    review.admin_notes = req.admin_notes
    review.moderated_by_user_id = actor_user.id
    review.moderated_at = datetime.now(timezone.utc)
    await db.flush()

    # Recalculate parent product ratings
    await _recalculate_product_ratings(db=db, product_id=review.product_id)

    await log_audit_event(
        db=db,
        action="reviews.moderated",
        entity_type="product_review",
        entity_id=str(review.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "product_id": review.product_id,
            "decision": req.action,
            "new_status": target_status,
            "admin_notes": req.admin_notes,
        },
    )

    return AdminReviewItem(
        id=review.id,
        product_id=review.product_id,
        product_name=review.product.name if review.product else "Unknown Product",
        product_slug=review.product.slug if review.product else "",
        user_id=review.user_id,
        customer_name=review.customer_name,
        customer_email=review.customer_email,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        status=review.status,
        is_verified_buyer=review.is_verified_buyer,
        admin_notes=review.admin_notes,
        moderated_by_user_id=review.moderated_by_user_id,
        moderated_at=review.moderated_at,
        created_at=review.created_at,
    )
