"""
Customer Account Service Layer (Module M17)
Handles profile retrieval & mutation, address book operations with default enforcement,
preferences management, customer-safe order detail & timeline projection,
return history queries, and security/session management.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import AppException
from app.modules.audit.service import log_audit_event
from app.modules.auth.models import RefreshToken, User
from app.core.security import hash_password, verify_password
from app.modules.auth.service import change_password
from app.modules.customer.models import Address, CustomerProfile
from app.modules.customer.schemas import (
    AddressCreateRequest,
    AddressListResponse,
    AddressResponse,
    AddressUpdateRequest,
    AdminCustomerDetailResponse,
    AdminCustomerListItem,
    AdminCustomerListResponse,
    CustomerOrderDetailResponse,
    CustomerOrderItemResponse,
    CustomerOrderTimelineEntry,
    CustomerPreferencesResponse,
    CustomerPreferencesUpdateRequest,
    CustomerProfileResponse,
    CustomerProfileUpdateRequest,
    CustomerReturnItemResponse,
    CustomerReturnListResponse,
    CustomerReturnResponse,
    CustomerSecurityOverviewResponse,
    CustomerSessionResponse,
    CustomerShipmentSummary,
)
from app.modules.fulfillment.models import Shipment
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory
from app.modules.returns.models import ReturnItem, ReturnRequest


# ==============================================================================
# 1. Profile Management
# ==============================================================================

async def get_or_create_customer_profile(
    db: AsyncSession,
    user: User,
) -> CustomerProfileResponse:
    """
    Retrieve customer profile, creating one on-the-fly with sensible defaults if missing.
    """
    stmt = select(CustomerProfile).where(CustomerProfile.user_id == user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = CustomerProfile(
            user_id=user.id,
            marketing_email_opt_in=False,
            marketing_sms_opt_in=False,
            marketing_whatsapp_opt_in=True,
            preferred_currency="PKR",
            preferred_language="en",
        )
        db.add(profile)
        await db.flush()

    full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
    if not full_name:
        full_name = user.email.split("@")[0].replace(".", " ").title()

    return CustomerProfileResponse(
        id=profile.id,
        user_id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=profile.first_name,
        last_name=profile.last_name,
        full_name=full_name,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        avatar_url=profile.avatar_url,
        marketing_email_opt_in=profile.marketing_email_opt_in,
        marketing_sms_opt_in=profile.marketing_sms_opt_in,
        marketing_whatsapp_opt_in=profile.marketing_whatsapp_opt_in,
        preferred_currency=profile.preferred_currency,
        preferred_language=profile.preferred_language,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


async def update_customer_profile(
    db: AsyncSession,
    user: User,
    req: CustomerProfileUpdateRequest,
) -> CustomerProfileResponse:
    """
    Update customer personal profile attributes and sync phone number to core user record.
    """
    stmt = select(CustomerProfile).where(CustomerProfile.user_id == user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = CustomerProfile(user_id=user.id)
        db.add(profile)
        await db.flush()

    if req.first_name is not None:
        profile.first_name = req.first_name.strip() or None
    if req.last_name is not None:
        profile.last_name = req.last_name.strip() or None
    if req.date_of_birth is not None:
        profile.date_of_birth = req.date_of_birth
    if req.gender is not None:
        profile.gender = req.gender.strip() or None
    if req.avatar_url is not None:
        profile.avatar_url = req.avatar_url.strip() or None

    # Sync phone with user record if updated
    if req.phone is not None:
        user.phone = req.phone

    await db.flush()

    await log_audit_event(
        db=db,
        action="customer.profile_updated",
        entity_type="customer_profile",
        entity_id=str(user.id),
        user_id=user.id,
        actor_email=user.email,
        details={
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "phone": user.phone,
        },
    )

    return await get_or_create_customer_profile(db, user)


# ==============================================================================
# 2. Preferences Management
# ==============================================================================

async def get_customer_preferences(
    db: AsyncSession,
    user: User,
) -> CustomerPreferencesResponse:
    """Retrieve customer marketing and localization preferences."""
    profile_resp = await get_or_create_customer_profile(db, user)
    return CustomerPreferencesResponse(
        marketing_email_opt_in=profile_resp.marketing_email_opt_in,
        marketing_sms_opt_in=profile_resp.marketing_sms_opt_in,
        marketing_whatsapp_opt_in=profile_resp.marketing_whatsapp_opt_in,
        preferred_currency=profile_resp.preferred_currency,
        preferred_language=profile_resp.preferred_language,
    )


async def update_customer_preferences(
    db: AsyncSession,
    user: User,
    req: CustomerPreferencesUpdateRequest,
) -> CustomerPreferencesResponse:
    """Update communication channels and language preferences."""
    stmt = select(CustomerProfile).where(CustomerProfile.user_id == user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = CustomerProfile(user_id=user.id)
        db.add(profile)
        await db.flush()

    if req.marketing_email_opt_in is not None:
        profile.marketing_email_opt_in = req.marketing_email_opt_in
    if req.marketing_sms_opt_in is not None:
        profile.marketing_sms_opt_in = req.marketing_sms_opt_in
    if req.marketing_whatsapp_opt_in is not None:
        profile.marketing_whatsapp_opt_in = req.marketing_whatsapp_opt_in
    if req.preferred_currency is not None:
        profile.preferred_currency = req.preferred_currency.upper().strip()
    if req.preferred_language is not None:
        profile.preferred_language = req.preferred_language.lower().strip()

    await db.flush()

    await log_audit_event(
        db=db,
        action="customer.preferences_updated",
        entity_type="customer_preferences",
        entity_id=str(user.id),
        user_id=user.id,
        actor_email=user.email,
        details={
            "marketing_email": profile.marketing_email_opt_in,
            "marketing_sms": profile.marketing_sms_opt_in,
            "marketing_whatsapp": profile.marketing_whatsapp_opt_in,
            "currency": profile.preferred_currency,
            "language": profile.preferred_language,
        },
    )

    return CustomerPreferencesResponse(
        marketing_email_opt_in=profile.marketing_email_opt_in,
        marketing_sms_opt_in=profile.marketing_sms_opt_in,
        marketing_whatsapp_opt_in=profile.marketing_whatsapp_opt_in,
        preferred_currency=profile.preferred_currency,
        preferred_language=profile.preferred_language,
    )


# ==============================================================================
# 3. Address Book Operations
# ==============================================================================

async def list_customer_addresses(
    db: AsyncSession,
    user_id: int,
) -> AddressListResponse:
    """Retrieve all saved addresses for customer, default address first."""
    stmt = (
        select(Address)
        .where(Address.user_id == user_id)
        .order_by(Address.is_default.desc(), Address.created_at.desc())
    )
    res = await db.execute(stmt)
    addresses = res.scalars().all()
    return AddressListResponse(
        addresses=[AddressResponse.model_validate(a) for a in addresses],
        total=len(addresses),
    )


async def create_customer_address(
    db: AsyncSession,
    user: User,
    req: AddressCreateRequest,
) -> AddressResponse:
    """
    Add address to customer address book.
    If requested as default (or if it's the customer's first address),
    unsets default flag on previous entries.
    """
    # Count existing addresses
    count_stmt = select(func.count(Address.id)).where(Address.user_id == user.id)
    count_res = await db.execute(count_stmt)
    existing_count = count_res.scalar_one()

    # Determine default state: if first address or requested default
    make_default = req.is_default or (existing_count == 0)

    if make_default:
        await db.execute(
            update(Address)
            .where(Address.user_id == user.id)
            .values(is_default=False)
        )

    new_address = Address(
        user_id=user.id,
        recipient_name=req.recipient_name.strip(),
        phone=req.phone.strip(),
        address_line_1=req.address_line_1.strip(),
        address_line_2=req.address_line_2.strip() if req.address_line_2 else None,
        city=req.city.strip(),
        area=req.area.strip() if req.area else None,
        postal_code=req.postal_code.strip() if req.postal_code else None,
        country_code=req.country_code.upper().strip(),
        label=req.label.strip() if req.label else None,
        is_default=make_default,
    )
    db.add(new_address)
    await db.flush()

    await log_audit_event(
        db=db,
        action="customer.address_created",
        entity_type="address",
        entity_id=str(new_address.id),
        user_id=user.id,
        actor_email=user.email,
        details={"city": new_address.city, "is_default": new_address.is_default},
    )

    return AddressResponse.model_validate(new_address)


async def get_customer_address(
    db: AsyncSession,
    user_id: int,
    address_id: int,
) -> AddressResponse:
    """Retrieve single address enforcing strict ownership."""
    stmt = select(Address).where(Address.id == address_id, Address.user_id == user_id)
    res = await db.execute(stmt)
    address = res.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found in customer address book",
        )

    return AddressResponse.model_validate(address)


async def update_customer_address(
    db: AsyncSession,
    user: User,
    address_id: int,
    req: AddressUpdateRequest,
) -> AddressResponse:
    """Update address fields, enforcing ownership and default address logic."""
    stmt = select(Address).where(Address.id == address_id, Address.user_id == user.id)
    res = await db.execute(stmt)
    address = res.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found in customer address book",
        )

    if req.is_default is True and not address.is_default:
        await db.execute(
            update(Address)
            .where(Address.user_id == user.id)
            .values(is_default=False)
        )
        address.is_default = True
    elif req.is_default is False and address.is_default:
        address.is_default = False

    if req.recipient_name is not None:
        address.recipient_name = req.recipient_name.strip()
    if req.phone is not None:
        address.phone = req.phone.strip()
    if req.address_line_1 is not None:
        address.address_line_1 = req.address_line_1.strip()
    if req.address_line_2 is not None:
        address.address_line_2 = req.address_line_2.strip() or None
    if req.city is not None:
        address.city = req.city.strip()
    if req.area is not None:
        address.area = req.area.strip() or None
    if req.postal_code is not None:
        address.postal_code = req.postal_code.strip() or None
    if req.country_code is not None:
        address.country_code = req.country_code.upper().strip()
    if req.label is not None:
        address.label = req.label.strip() or None

    await db.flush()

    await log_audit_event(
        db=db,
        action="customer.address_updated",
        entity_type="address",
        entity_id=str(address.id),
        user_id=user.id,
        actor_email=user.email,
        details={"address_id": address.id, "city": address.city, "is_default": address.is_default},
    )

    return AddressResponse.model_validate(address)


async def delete_customer_address(
    db: AsyncSession,
    user: User,
    address_id: int,
) -> None:
    """Delete address with automatic fallback default promotion."""
    stmt = select(Address).where(Address.id == address_id, Address.user_id == user.id)
    res = await db.execute(stmt)
    address = res.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found in customer address book",
        )

    was_default = address.is_default
    await db.delete(address)
    await db.flush()

    # If deleted address was default, promote another address to default
    if was_default:
        next_addr_stmt = (
            select(Address)
            .where(Address.user_id == user.id)
            .order_by(Address.created_at.desc())
            .limit(1)
        )
        next_res = await db.execute(next_addr_stmt)
        next_addr = next_res.scalar_one_or_none()
        if next_addr:
            next_addr.is_default = True
            await db.flush()

    await log_audit_event(
        db=db,
        action="customer.address_deleted",
        entity_type="address",
        entity_id=str(address_id),
        user_id=user.id,
        actor_email=user.email,
        details={"deleted_address_id": address_id},
    )


async def set_default_address(
    db: AsyncSession,
    user: User,
    address_id: int,
) -> AddressResponse:
    """Explicitly set an address as primary default."""
    stmt = select(Address).where(Address.id == address_id, Address.user_id == user.id)
    res = await db.execute(stmt)
    address = res.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found in customer address book",
        )

    await db.execute(
        update(Address)
        .where(Address.user_id == user.id)
        .values(is_default=False)
    )
    address.is_default = True
    await db.flush()

    await log_audit_event(
        db=db,
        action="customer.address_set_default",
        entity_type="address",
        entity_id=str(address.id),
        user_id=user.id,
        actor_email=user.email,
        details={"address_id": address.id},
    )

    return AddressResponse.model_validate(address)


# ==============================================================================
# 4. Customer-Safe Order Details & Timeline Projection
# ==============================================================================

_STATUS_CUSTOMER_DESCRIPTIONS: Dict[str, str] = {
    "pending_confirmation": "Your order was placed successfully and is awaiting order confirmation.",
    "confirmed": "Your order is confirmed and scheduled for warehouse packing.",
    "processing": "Our atelier is carefully packing your pieces.",
    "shipped": "Your parcel was handed over to our courier partner for dispatch.",
    "dispatched": "Your parcel is en route with the courier delivery network.",
    "delivered": "Parcel has been successfully delivered to your destination address.",
    "completed": "Order fulfilled and completed.",
    "cancelled": "Order was cancelled.",
    "return_requested": "A return or exchange request was filed for this order.",
    "returned": "Order items were returned to our warehouse.",
}


async def get_customer_order_detail(
    db: AsyncSession,
    user: User,
    order_number: str,
) -> CustomerOrderDetailResponse:
    """
    Project full order details with timeline and shipment tracking.
    Enforces customer ownership and completely omits internal staff notes.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
            selectinload(Order.shipments),
        )
        .where(Order.order_number == order_number)
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Ownership check: Customer can only view their own orders
    if order.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    try:
        shipping_addr = json.loads(order.shipping_address_snapshot)
    except Exception:
        shipping_addr = {}

    # Map Items
    items = [
        CustomerOrderItemResponse(
            id=i.id,
            product_id=i.product_id,
            variant_id=i.variant_id,
            product_name=i.product_name_snapshot,
            product_slug=i.product_slug_snapshot,
            sku=i.sku_snapshot,
            size=i.size_snapshot,
            color=i.color_snapshot,
            unit_price=i.unit_price,
            quantity=i.quantity,
            line_total=i.line_total,
            image_url=i.image_url_snapshot,
        )
        for i in order.items
    ]

    # Map Timeline (Customer Safe: No staff notes!)
    timeline = []
    for h in sorted(order.status_history, key=lambda x: x.created_at):
        desc = _STATUS_CUSTOMER_DESCRIPTIONS.get(
            h.to_status,
            f"Order moved to {h.to_status.replace('_', ' ').capitalize()}.",
        )
        timeline.append(
            CustomerOrderTimelineEntry(
                status=h.to_status,
                description=desc,
                occurred_at=h.created_at,
            )
        )

    # Map Shipments
    shipments = [
        CustomerShipmentSummary(
            id=s.id,
            shipment_number=s.shipment_number,
            courier_name=s.courier_name,
            tracking_number=s.tracking_number,
            tracking_url=s.tracking_url,
            status=s.status,
            total_weight_grams=s.total_weight_grams,
            allocated_at=s.allocated_at,
            dispatched_at=s.dispatched_at,
            delivered_at=s.delivered_at,
        )
        for s in (order.shipments or [])
    ]

    return CustomerOrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        fulfillment_status=order.fulfillment_status,
        currency_code=order.currency_code,
        subtotal=order.subtotal,
        discount_total=order.discount_total,
        shipping_total=order.shipping_total,
        grand_total=order.grand_total,
        shipping_address=shipping_addr,
        shipping_method_code=order.shipping_method_code,
        customer_notes=order.customer_note,
        items=items,
        timeline=timeline,
        shipments=shipments,
        placed_at=order.placed_at,
    )


# ==============================================================================
# 5. Customer Return & Exchange Overview
# ==============================================================================

async def list_customer_returns(
    db: AsyncSession,
    user: User,
    page: int = 1,
    page_size: int = 20,
) -> CustomerReturnListResponse:
    """
    List all return and exchange requests for the authenticated customer.
    Filters out internal staff notes and inspector remarks.
    """
    offset = (page - 1) * page_size
    count_stmt = (
        select(func.count(ReturnRequest.id))
        .where(ReturnRequest.user_id == user.id)
    )
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one()

    stmt = (
        select(ReturnRequest)
        .options(
            selectinload(ReturnRequest.order),
            selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
            selectinload(ReturnRequest.items).selectinload(ReturnItem.exchange_variant),
        )
        .where(ReturnRequest.user_id == user.id)
        .order_by(ReturnRequest.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    returns = res.scalars().all()

    items_out = []
    for r in returns:
        r_items = []
        for it in r.items:
            p_name = it.order_item.product_name_snapshot if it.order_item else "Item"
            sku = it.order_item.sku_snapshot if it.order_item else "SKU"
            ex_size = it.exchange_variant.size if it.exchange_variant else None
            r_items.append(
                CustomerReturnItemResponse(
                    id=it.id,
                    order_item_id=it.order_item_id,
                    product_name=p_name,
                    sku=sku,
                    quantity=it.quantity,
                    reason=it.reason,
                    exchange_size=ex_size,
                    inspection_status=it.inspection_status,
                    refund_amount=it.refund_amount,
                )
            )

        items_out.append(
            CustomerReturnResponse(
                id=r.id,
                request_number=r.request_number,
                order_number=r.order.order_number if r.order else "",
                status=r.status,
                request_type=r.request_type,
                resolution_type=r.resolution_type,
                total_refund_amount=r.total_refund_amount,
                customer_notes=r.customer_notes,
                items=r_items,
                created_at=r.created_at,
                resolved_at=r.resolved_at,
            )
        )

    return CustomerReturnListResponse(
        returns=items_out,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_customer_return_detail(
    db: AsyncSession,
    user: User,
    return_id: int,
) -> CustomerReturnResponse:
    """Retrieve single return request with customer ownership check."""
    stmt = (
        select(ReturnRequest)
        .options(
            selectinload(ReturnRequest.order),
            selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
            selectinload(ReturnRequest.items).selectinload(ReturnItem.exchange_variant),
        )
        .where(ReturnRequest.id == return_id, ReturnRequest.user_id == user.id)
    )
    res = await db.execute(stmt)
    r = res.scalar_one_or_none()

    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    r_items = []
    for it in r.items:
        p_name = it.order_item.product_name_snapshot if it.order_item else "Item"
        sku = it.order_item.sku_snapshot if it.order_item else "SKU"
        ex_size = it.exchange_variant.size if it.exchange_variant else None
        r_items.append(
            CustomerReturnItemResponse(
                id=it.id,
                order_item_id=it.order_item_id,
                product_name=p_name,
                sku=sku,
                quantity=it.quantity,
                reason=it.reason,
                exchange_size=ex_size,
                inspection_status=it.inspection_status,
                refund_amount=it.refund_amount,
            )
        )

    return CustomerReturnResponse(
        id=r.id,
        request_number=r.request_number,
        order_number=r.order.order_number if r.order else "",
        status=r.status,
        request_type=r.request_type,
        resolution_type=r.resolution_type,
        total_refund_amount=r.total_refund_amount,
        customer_notes=r.customer_notes,
        items=r_items,
        created_at=r.created_at,
        resolved_at=r.resolved_at,
    )


# ==============================================================================
# 6. Security & Session Overview
# ==============================================================================

async def get_customer_security_overview(
    db: AsyncSession,
    user: User,
) -> CustomerSecurityOverviewResponse:
    """Retrieve active session counts, email verification state, and login history."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,
        )
        .order_by(RefreshToken.created_at.desc())
    )
    res = await db.execute(stmt)
    tokens = res.scalars().all()

    sessions = [
        CustomerSessionResponse(
            id=t.id,
            created_at=t.created_at,
            expires_at=t.expires_at,
            is_current=False,
        )
        for t in tokens
    ]

    return CustomerSecurityOverviewResponse(
        email=user.email,
        phone=user.phone,
        email_verified=user.email_verified_at is not None,
        last_login_at=user.last_login_at,
        active_sessions_count=len(sessions),
        sessions=sessions,
    )


async def change_customer_password_workflow(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Change customer password with current password verification and session revocation."""
    await change_password(
        db=db,
        user=user,
        current_password=current_password,
        new_password=new_password,
    )
    await log_audit_event(
        db=db,
        action="customer.password_changed",
        entity_type="user",
        entity_id=str(user.id),
        user_id=user.id,
        actor_email=user.email,
        details={"status": "password_changed_sessions_revoked"},
    )


async def revoke_other_sessions(
    db: AsyncSession,
    user: User,
) -> int:
    """Revoke all active refresh token sessions for customer."""
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)
        .values(revoked=True)
    )
    res = await db.execute(stmt)
    revoked_count = res.rowcount
    await db.flush()

    await log_audit_event(
        db=db,
        action="customer.sessions_revoked",
        entity_type="user",
        entity_id=str(user.id),
        user_id=user.id,
        actor_email=user.email,
        details={"revoked_count": revoked_count},
    )

    return revoked_count


# ==============================================================================
# 7. Administrative Customer Management (Module M19)
# ==============================================================================

async def list_customers_admin(
    db: AsyncSession,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[AdminCustomerListItem], int]:
    """Retrieve paginated customer accounts with profile and spend aggregates."""
    query = (
        select(User)
        .options(
            selectinload(User.customer_profile),
        )
        .where(User.user_type == "customer")
    )

    if status_filter:
        query = query.where(User.status == status_filter)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.outerjoin(CustomerProfile, User.id == CustomerProfile.user_id).where(
            User.email.ilike(search_term)
            | User.phone.ilike(search_term)
            | CustomerProfile.first_name.ilike(search_term)
            | CustomerProfile.last_name.ilike(search_term)
        )

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    users = res.scalars().all()

    # Pre-calculate order stats for these users
    user_ids = [u.id for u in users]
    orders_map: Dict[int, Tuple[int, Decimal]] = {}
    if user_ids:
        order_stats_query = (
            select(
                Order.user_id,
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.grand_total), Decimal("0.00")).label("spend"),
            )
            .where(Order.user_id.in_(user_ids), Order.status != "cancelled")
            .group_by(Order.user_id)
        )
        stats_res = await db.execute(order_stats_query)
        for row in stats_res.all():
            orders_map[row.user_id] = (row.order_count, row.spend)

    items: List[AdminCustomerListItem] = []
    for u in users:
        p = u.customer_profile
        full_name = f"{p.first_name or ''} {p.last_name or ''}".strip() if p else ""
        if not full_name:
            full_name = u.email.split("@")[0]
        order_count, spend = orders_map.get(u.id, (0, Decimal("0.00")))
        items.append(
            AdminCustomerListItem(
                id=u.id,
                email=u.email,
                full_name=full_name,
                phone=u.phone,
                status=u.status,
                user_type=u.user_type,
                total_orders=order_count,
                lifetime_spend=spend,
                created_at=u.created_at,
            )
        )

    return items, total


async def get_customer_detail_admin(
    db: AsyncSession,
    customer_id: int,
) -> AdminCustomerDetailResponse:
    """Retrieve comprehensive customer dossier including profile, addresses, spend, and orders."""
    stmt = (
        select(User)
        .options(
            selectinload(User.customer_profile),
            selectinload(User.addresses),
        )
        .where(User.id == customer_id)
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Order stats and recent orders
    orders_stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
        )
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    orders_res = await db.execute(orders_stmt)
    orders = orders_res.scalars().all()

    total_orders = len([o for o in orders if o.status != "cancelled"])
    lifetime_spend = sum((o.grand_total for o in orders if o.status != "cancelled"), Decimal("0.00"))

    # Return count
    returns_stmt = select(func.count(ReturnRequest.id)).where(ReturnRequest.user_id == user.id)
    returns_count_res = await db.execute(returns_stmt)
    returns_count = returns_count_res.scalar_one() or 0

    from app.modules.orders.service import build_order_response

    recent_orders_responses = [build_order_response(o) for o in orders[:10]]

    profile_res = None
    if user.customer_profile:
        p = user.customer_profile
        full_name = f"{p.first_name or ''} {p.last_name or ''}".strip() or user.email.split("@")[0]
        profile_res = CustomerProfileResponse(
            id=p.id,
            user_id=user.id,
            email=user.email,
            phone=user.phone,
            first_name=p.first_name,
            last_name=p.last_name,
            full_name=full_name,
            date_of_birth=p.date_of_birth,
            gender=p.gender,
            avatar_url=p.avatar_url,
            marketing_email_opt_in=p.marketing_email_opt_in,
            marketing_sms_opt_in=p.marketing_sms_opt_in,
            marketing_whatsapp_opt_in=p.marketing_whatsapp_opt_in,
            preferred_currency=p.preferred_currency,
            preferred_language=p.preferred_language,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )

    addresses_res = [AddressResponse.model_validate(a) for a in (user.addresses or [])]

    return AdminCustomerDetailResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        status=user.status,
        user_type=user.user_type,
        email_verified=user.email_verified_at is not None,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        profile=profile_res,
        addresses=addresses_res,
        total_orders=total_orders,
        lifetime_spend=lifetime_spend,
        returns_count=returns_count,
        recent_orders=recent_orders_responses,
    )


async def update_customer_status_admin(
    db: AsyncSession,
    customer_id: int,
    new_status: str,
    reason: str,
    actor_user: Optional[User] = None,
) -> AdminCustomerDetailResponse:
    """Modify customer account status (active, suspended, disabled) with audit logging."""
    stmt = (
        select(User)
        .options(
            selectinload(User.customer_profile),
            selectinload(User.addresses),
        )
        .where(User.id == customer_id)
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    if user.user_type != "customer":
        raise AppException(
            message="Only customer accounts can be modified through this endpoint",
            code="INVALID_USER_TYPE",
            status_code=400,
        )

    old_status = user.status
    user.status = new_status

    # If suspending or disabling, revoke active sessions
    if new_status in ("suspended", "disabled"):
        rev_stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)
            .values(revoked=True)
        )
        await db.execute(rev_stmt)

    await db.flush()

    await log_audit_event(
        db=db,
        action="customer.status_updated",
        entity_type="user",
        entity_id=str(user.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "customer_email": user.email,
            "from_status": old_status,
            "to_status": new_status,
            "reason": reason,
        },
    )
    await db.flush()

    return await get_customer_detail_admin(db, customer_id=user.id)
