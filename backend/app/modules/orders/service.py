"""
Order and Checkout Service Layer (M12)
Orchestrates cart validation, authoritative price recalculation, delivery validation,
inventory reservation, transactional order creation, idempotency, and lifecycle state machines.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import secrets
from typing import Dict, List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import AppException
from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.cart.models import Cart
from app.modules.cart.service import (
    build_cart_response,
    clear_cart,
    get_or_create_cart,
)
from app.modules.inventory.schemas import StockReleaseRequest, StockReservationRequest
from app.modules.inventory.service import release_stock, reserve_stock
from app.modules.orders.models import (
    CheckoutIdempotency,
    Order,
    OrderItem,
    OrderStatusHistory,
)
from app.modules.orders.schemas import (
    AddressSnapshot,
    AdminOrderDetailResponse,
    AdminOrderStatusHistoryResponse,
    CheckoutRequest,
    OrderCODReconciliationRequest,
    OrderItemResponse,
    OrderPaymentSummary,
    OrderResponse,
    OrderReturnSummary,
    OrderShipmentSummary,
    OrderStatusHistoryResponse,
)
from app.modules.shipping.schemas import (
    DeliveryAddressValidationRequest,
    ShippingQuoteRequest,
)
from app.modules.shipping.service import (
    calculate_shipping_quote,
    validate_delivery_address,
)

# Explicit Order Lifecycle State Machine
ALLOWED_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
    "pending_confirmation": {"confirmed", "cancelled"},
    "confirmed": {"processing", "cancelled"},
    "processing": {"packed", "cancelled"},
    "packed": {"shipped", "cancelled"},
    "shipped": {"delivered", "return_requested"},
    "delivered": {"return_requested"},
    "return_requested": {"returned", "delivered"},
    "returned": {"refunded"},
    "cancelled": set(),
    "refunded": set(),
}


def generate_order_number() -> str:
    """Generate a clean, professional order reference code (e.g. UNV-20261110-847291)."""
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    random_part = secrets.randbelow(900000) + 100000
    return f"UNV-{date_part}-{random_part}"


def compute_request_fingerprint(req: CheckoutRequest) -> str:
    """Compute SHA-256 fingerprint of the checkout payload excluding volatile client tokens."""
    payload_dict = req.model_dump(exclude={"idempotency_key"}, mode="json")
    serialized = json.dumps(payload_dict, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_order_response(
    order: Order,
    items: Optional[List[OrderItem]] = None,
    history: Optional[List[OrderStatusHistory]] = None,
) -> OrderResponse:
    """Transform Order database entity into strongly typed OrderResponse."""
    addr_data = json.loads(order.shipping_address_snapshot)
    address = AddressSnapshot(**addr_data)

    items_source = items if items is not None else order.items
    history_source = history if history is not None else order.status_history

    items_list = [
        OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=item.product_name_snapshot,
            product_slug=item.product_slug_snapshot,
            sku=item.sku_snapshot,
            size=item.size_snapshot,
            color=item.color_snapshot,
            unit_price=item.unit_price,
            quantity=item.quantity,
            line_discount=item.line_discount,
            line_total=item.line_total,
            image_url=item.image_url_snapshot,
        )
        for item in items_source
    ]

    history_list = [
        OrderStatusHistoryResponse(
            id=h.id,
            from_status=h.from_status,
            to_status=h.to_status,
            note=h.note,
            created_at=h.created_at,
        )
        for h in history_source
    ]

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        fulfillment_status=order.fulfillment_status,
        payment_method=order.payment_method,
        currency_code=order.currency_code,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        customer_phone=order.customer_phone,
        subtotal=order.subtotal,
        discount_total=order.discount_total,
        shipping_total=order.shipping_total,
        tax_total=order.tax_total,
        grand_total=order.grand_total,
        shipping_method_code=order.shipping_method_code,
        shipping_method_name=order.shipping_method_name,
        shipping_address=address,
        customer_note=order.customer_note,
        items=items_list,
        status_history=history_list,
        placed_at=order.placed_at,
        created_at=order.created_at,
    )


def build_admin_order_detail_response(order: Order) -> AdminOrderDetailResponse:
    """Transform Order database entity into comprehensive AdminOrderDetailResponse."""
    base_res = build_order_response(order)

    payments_list = [
        OrderPaymentSummary(
            id=p.id,
            payment_method=p.payment_method,
            status=p.status,
            amount=p.amount,
            currency_code=getattr(p, "currency_code", "PKR"),
            amount_collected=p.amount_collected,
            amount_outstanding=p.amount_outstanding,
            settlement_reference=p.settlement_reference,
            provider_reference=p.provider_reference,
            reconciled_at=p.reconciled_at,
            notes=p.notes,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in (order.payments or [])
    ]

    shipments_list = [
        OrderShipmentSummary(
            id=s.id,
            shipment_number=s.shipment_number,
            tracking_number=s.tracking_number,
            courier_code=s.courier_code,
            courier_name=s.courier_name,
            status=s.status,
            dispatched_at=s.dispatched_at,
            delivered_at=s.delivered_at,
            created_at=s.created_at,
        )
        for s in (order.shipments or [])
    ]

    returns_list = [
        OrderReturnSummary(
            id=r.id,
            request_number=r.request_number,
            request_type=r.request_type,
            status=r.status,
            reason_category=r.reason_category,
            refund_status=r.refund_status,
            refund_amount=r.refund_amount,
            created_at=r.created_at,
        )
        for r in (order.returns or [])
    ]

    admin_history = [
        AdminOrderStatusHistoryResponse(
            id=h.id,
            from_status=h.from_status,
            to_status=h.to_status,
            note=h.note,
            changed_by_user_id=h.changed_by_user_id,
            changed_by_user_email=h.changed_by_user.email if getattr(h, "changed_by_user", None) else None,
            created_at=h.created_at,
        )
        for h in (order.status_history or [])
    ]

    return AdminOrderDetailResponse(
        **base_res.model_dump(),
        user_id=order.user_id,
        payments=payments_list,
        shipments=shipments_list,
        returns=returns_list,
        admin_history=admin_history,
    )


async def create_order_from_checkout(
    db: AsyncSession,
    req: CheckoutRequest,
    current_user: Optional[User] = None,
    anonymous_token: Optional[str] = None,
) -> OrderResponse:
    """
    Execute transactional checkout and order creation.
    1. Checks idempotency to prevent duplicate orders or double-charges.
    2. Validates cart items, authoritative catalogue prices, and active availability.
    3. Validates shipping address and resolves official shipping quote.
    4. Reserves physical inventory units safely via M09 stock reservation foundation.
    5. Calculates final financial totals (subtotal, shipping, discounts, grand_total).
    6. Creates immutable Order and OrderItem snapshots.
    7. Empties active cart and records audit log.
    """
    # -----------------------------------------------------------------------
    # 1. Idempotency Check
    # -----------------------------------------------------------------------
    fingerprint = compute_request_fingerprint(req)
    if req.idempotency_key:
        idempotency_stmt = select(CheckoutIdempotency).where(
            CheckoutIdempotency.idempotency_key == req.idempotency_key
        )
        res = await db.execute(idempotency_stmt)
        cached_idempotency = res.scalar_one_or_none()

        if cached_idempotency:
            if cached_idempotency.request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="IDEMPOTENCY_CONFLICT: Idempotency key previously used with different order details",
                )
            if cached_idempotency.response_payload:
                cached_dict = json.loads(cached_idempotency.response_payload)
                return OrderResponse(**cached_dict)

    # -----------------------------------------------------------------------
    # 2. Cart Retrieval & Item Validation
    # -----------------------------------------------------------------------
    cart, _ = await get_or_create_cart(
        db,
        user=current_user,
        anonymous_token=anonymous_token,
    )
    cart_res = await build_cart_response(db, cart)

    if cart_res.total_items == 0 or len(cart_res.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CART_EMPTY: Cannot proceed to checkout with an empty shopping cart",
        )

    # Verify every line item is active and available
    for item in cart_res.items:
        if not item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CHECKOUT_ITEMS_UNAVAILABLE: '{item.product_name}' ({item.size}) is not available: {item.availability_message}",
            )

    # -----------------------------------------------------------------------
    # 3. Delivery Address & Shipping Fee Validation
    # -----------------------------------------------------------------------
    addr_req = DeliveryAddressValidationRequest(
        full_name=req.shipping_address.full_name,
        phone=req.shipping_address.phone,
        address_line_1=req.shipping_address.address_line_1,
        address_line_2=req.shipping_address.address_line_2,
        city=req.shipping_address.city,
        postal_code=req.shipping_address.postal_code,
        country_code=req.shipping_address.country_code,
    )
    addr_validation = await validate_delivery_address(db, addr_req)
    if not addr_validation.is_serviceable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DESTINATION_UNSERVICEABLE: Delivery is not serviceable to '{req.shipping_address.city}'",
        )

    # Calculate authoritative shipping quote
    is_cod = req.payment_method.lower() == "cod"
    quote_req = ShippingQuoteRequest(
        city=req.shipping_address.city,
        postal_code=req.shipping_address.postal_code,
        country_code=req.shipping_address.country_code,
        subtotal=cart_res.subtotal,
        is_cod=is_cod,
    )
    quote_res = await calculate_shipping_quote(db, quote_req)

    # Match requested shipping method
    matched_method = next(
        (m for m in quote_res.available_methods if m.code == req.shipping_method_code),
        None,
    )
    if not matched_method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"INVALID_SHIPPING_METHOD: Delivery option '{req.shipping_method_code}' is not available for this address or payment method",
        )

    shipping_fee = matched_method.final_fee
    shipping_name = matched_method.name

    # -----------------------------------------------------------------------
    # 4. Generate Order Reference
    # -----------------------------------------------------------------------
    order_number = generate_order_number()

    # -----------------------------------------------------------------------
    # 5. Inventory Reservation (Transaction Safe)
    # -----------------------------------------------------------------------
    reserved_items: List[Tuple[int, int]] = []
    try:
        for item in cart_res.items:
            res_req = StockReservationRequest(
                variant_id=item.variant_id,
                quantity=item.quantity,
                reference_type="checkout_hold",
                reference_id=order_number,
                notes=f"Order reservation for {order_number}",
            )
            await reserve_stock(db, res_req, actor_user=current_user)
            reserved_items.append((item.variant_id, item.quantity))
    except Exception as exc:
        # Stock reservation failed (e.g. concurrent checkout) -> rollback handled by caller session
        raise exc

    # -----------------------------------------------------------------------
    # 6. Financial Calculations & Server-Side Promotion Validation
    # -----------------------------------------------------------------------
    subtotal = cart_res.subtotal
    discount_total = Decimal("0.00")
    applied_coupon = None

    if req.coupon_code:
        from app.modules.promotions.service import evaluate_coupon
        is_valid, coupon, calc_discount, msg = await evaluate_coupon(
            db=db,
            code=req.coupon_code,
            subtotal=subtotal,
            customer_email=req.customer_email,
            user_id=current_user.id if current_user else None,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid coupon code: {msg}",
            )
        discount_total = calc_discount
        applied_coupon = coupon

    shipping_total = shipping_fee
    tax_total = Decimal("0.00")
    grand_total = max(Decimal("0.00"), subtotal - discount_total) + shipping_total + tax_total

    # -----------------------------------------------------------------------
    # 7. Create Order Header & Immutable Item Snapshots
    # -----------------------------------------------------------------------
    order = Order(
        order_number=order_number,
        user_id=current_user.id if current_user else None,
        customer_email=req.customer_email,
        customer_phone=req.customer_phone,
        customer_name=req.customer_name,
        status="pending_confirmation",
        payment_status="unpaid",  # Never marked as paid upon order creation!
        fulfillment_status="unfulfilled",
        payment_method=req.payment_method,
        currency_code="PKR",
        subtotal=subtotal,
        discount_total=discount_total,
        shipping_total=shipping_total,
        tax_total=tax_total,
        grand_total=grand_total,
        shipping_method_code=matched_method.code,
        shipping_method_name=shipping_name,
        shipping_address_snapshot=json.dumps(req.shipping_address.model_dump(), default=str),
        customer_note=req.customer_note,
        placed_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()

    if applied_coupon:
        from app.modules.promotions.service import record_redemption
        await record_redemption(
            db=db,
            coupon=applied_coupon,
            order_id=order.id,
            user_id=current_user.id if current_user else None,
            customer_email=req.customer_email,
            discount_amount=discount_total,
        )

    # Create immutable OrderItems
    created_items: List[OrderItem] = []
    for item in cart_res.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name_snapshot=item.product_name,
            product_slug_snapshot=item.product_slug,
            sku_snapshot=item.variant_sku,
            size_snapshot=item.size,
            color_snapshot=item.color_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            line_discount=Decimal("0.00"),
            line_total=item.line_total,
            image_url_snapshot=item.image_url,
        )
        db.add(order_item)
        created_items.append(order_item)

    # Create initial status history entry
    status_entry = OrderStatusHistory(
        order_id=order.id,
        from_status="none",
        to_status="pending_confirmation",
        note="Order placed via checkout",
        changed_by_user_id=current_user.id if current_user else None,
    )
    db.add(status_entry)
    await db.flush()

    # -----------------------------------------------------------------------
    # 8. Initialize Payment Ledger Entry (M13 COD Workflow)
    # -----------------------------------------------------------------------
    from app.modules.payments.service import create_initial_payment_for_order
    await create_initial_payment_for_order(db, order=order, actor_user=current_user)

    # -----------------------------------------------------------------------
    # 9. Empty Cart & Record Idempotency
    # -----------------------------------------------------------------------
    await clear_cart(db, cart)

    response_obj = build_order_response(order, items=created_items, history=[status_entry])

    if req.idempotency_key:
        now = datetime.now(timezone.utc)
        idempotency_record = CheckoutIdempotency(
            idempotency_key=req.idempotency_key,
            user_id=current_user.id if current_user else None,
            request_fingerprint=fingerprint,
            order_id=order.id,
            order_number=order.order_number,
            response_payload=json.dumps(response_obj.model_dump(mode="json")),
            expires_at=now + timedelta(days=1),
        )
        db.add(idempotency_record)
        await db.flush()

    # Audit logging
    await log_audit_event(
        db=db,
        action="order.created",
        entity_type="order",
        entity_id=str(order.id),
        user_id=current_user.id if current_user else None,
        actor_email=current_user.email if current_user else req.customer_email,
        details={
            "order_number": order.order_number,
            "grand_total": str(order.grand_total),
            "payment_method": order.payment_method,
            "items_count": len(created_items),
        },
    )

    return response_obj


async def update_order_status(
    db: AsyncSession,
    order_id: int,
    to_status: str,
    note: Optional[str] = None,
    actor_user: Optional[User] = None,
) -> OrderResponse:
    """
    Execute order lifecycle transition according to strict state machine rules.
    If order is cancelled, automatically releases all reserved stock back to the active pool.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
        )
        .where(Order.id == order_id)
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    current_status = order.status
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())

    if to_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"INVALID_STATUS_TRANSITION: Cannot transition order from '{current_status}' to '{to_status}'",
        )

    # If cancelling, release reserved inventory units
    if to_status == "cancelled":
        for item in order.items:
            if item.variant_id:
                try:
                    rel_req = StockReleaseRequest(
                        variant_id=item.variant_id,
                        quantity=item.quantity,
                        reference_type="order_cancelled",
                        reference_id=order.order_number,
                        notes=f"Released reservation from cancelled order {order.order_number}",
                    )
                    await release_stock(db, rel_req, actor_user=actor_user)
                except Exception:
                    # Continue releasing all items even if one was already released
                    pass

    order.status = to_status
    await db.flush()

    # Record transition history
    history_entry = OrderStatusHistory(
        order_id=order.id,
        from_status=current_status,
        to_status=to_status,
        note=note or f"Status changed from {current_status} to {to_status}",
        changed_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(history_entry)
    await db.flush()

    await log_audit_event(
        db=db,
        action="order.status_updated",
        entity_type="order",
        entity_id=str(order.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "order_number": order.order_number,
            "from_status": current_status,
            "to_status": to_status,
            "note": note,
        },
    )

    # Re-query order with relationships loaded
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
        )
        .where(Order.id == order_id)
        .execution_options(populate_existing=True)
    )
    res = await db.execute(stmt)
    refreshed_order = res.scalar_one()
    return build_order_response(refreshed_order)


async def get_order_by_number(
    db: AsyncSession,
    order_number: str,
    current_user: Optional[User] = None,
) -> OrderResponse:
    """
    Retrieve order details by human-readable reference number.
    Enforces customer ownership isolation (customer can only view their own orders).
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
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

    # Ownership check: If authenticated customer (not staff), must match user_id
    if current_user and current_user.user_type == "customer":
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

    return build_order_response(order)


async def list_orders(
    db: AsyncSession,
    current_user: Optional[User] = None,
    status_filter: Optional[str] = None,
    payment_status: Optional[str] = None,
    payment_method: Optional[str] = None,
    fulfillment_status: Optional[str] = None,
    customer_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[OrderResponse], int]:
    """Retrieve orders with rich administrative pagination and faceted filtering."""
    query = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
        )
    )

    if current_user and current_user.user_type == "customer":
        query = query.where(Order.user_id == current_user.id)

    if status_filter:
        query = query.where(Order.status == status_filter)

    if payment_status:
        query = query.where(Order.payment_status == payment_status)

    if payment_method:
        query = query.where(Order.payment_method == payment_method)

    if fulfillment_status:
        query = query.where(Order.fulfillment_status == fulfillment_status)

    if customer_id:
        query = query.where(Order.user_id == customer_id)

    if date_from:
        query = query.where(Order.created_at >= date_from)

    if date_to:
        query = query.where(Order.created_at <= date_to)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            Order.order_number.ilike(search_term)
            | Order.customer_email.ilike(search_term)
            | Order.customer_phone.ilike(search_term)
            | Order.customer_name.ilike(search_term)
        )

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    orders = res.scalars().all()

    return [build_order_response(o) for o in orders], total


async def get_admin_order(
    db: AsyncSession,
    order_ref: str,
) -> AdminOrderDetailResponse:
    """
    Retrieve comprehensive order details for administrative inspection including
    payments, shipments, returns, and operator timeline notes.
    """
    query = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history).selectinload(OrderStatusHistory.changed_by_user),
            selectinload(Order.payments),
            selectinload(Order.shipments),
            selectinload(Order.returns),
        )
    )

    if order_ref.isdigit():
        query = query.where(Order.id == int(order_ref))
    else:
        query = query.where(Order.order_number == order_ref)

    res = await db.execute(query)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return build_admin_order_detail_response(order)


async def confirm_order_admin(
    db: AsyncSession,
    order_id: int,
    note: Optional[str] = None,
    actor_user: Optional[User] = None,
) -> OrderResponse:
    """
    Confirm an order awaiting confirmation.
    Transitions pending_confirmation -> confirmed with audit logging.
    """
    stmt = select(Order).where(Order.id == order_id)
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != "pending_confirmation":
        raise AppException(
            message=f"Cannot confirm order: Expected status 'pending_confirmation', current status is '{order.status}'",
            code="INVALID_STATUS_TRANSITION",
            status_code=400,
        )

    return await update_order_status(
        db,
        order_id=order_id,
        to_status="confirmed",
        note=note or "Order confirmed by staff",
        actor_user=actor_user,
    )


async def cancel_order_admin(
    db: AsyncSession,
    order_id: int,
    reason: str,
    actor_user: Optional[User] = None,
) -> OrderResponse:
    """
    Cancel an unfulfilled order within authorized policy.
    Validates cancellability, releases reserved stock, voids unpaid COD payments, and creates audit log.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.status_history),
        )
        .where(Order.id == order_id)
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status == "cancelled":
        raise AppException(
            message="Order is already cancelled",
            code="ALREADY_CANCELLED",
            status_code=400,
        )

    if order.status in ("shipped", "delivered"):
        raise AppException(
            message=f"Cannot cancel order in '{order.status}' status. Initiated shipments must be processed via the returns workflow.",
            code="ORDER_ALREADY_DISPATCHED",
            status_code=400,
        )

    if order.status not in ("pending_confirmation", "confirmed", "processing", "packed"):
        raise AppException(
            message=f"Cannot cancel order with current status '{order.status}'.",
            code="INVALID_STATUS_TRANSITION",
            status_code=400,
        )

    # Cancel associated unpaid COD payments
    for payment in order.payments:
        if payment.payment_method == "cod" and payment.status in ("unpaid", "pending"):
            payment.status = "cancelled"

    return await update_order_status(
        db,
        order_id=order_id,
        to_status="cancelled",
        note=f"Cancelled by staff: {reason}",
        actor_user=actor_user,
    )


async def add_order_note(
    db: AsyncSession,
    order_id: int,
    note: str,
    actor_user: Optional[User] = None,
) -> AdminOrderStatusHistoryResponse:
    """Add internal operational staff note to an order without altering lifecycle status."""
    stmt = select(Order).where(Order.id == order_id)
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    history_entry = OrderStatusHistory(
        order_id=order.id,
        from_status=order.status,
        to_status=order.status,
        note=note,
        changed_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(history_entry)
    await db.flush()
    await db.refresh(history_entry)

    await log_audit_event(
        db=db,
        action="order.note_added",
        entity_type="order",
        entity_id=str(order.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={"order_number": order.order_number, "note": note},
    )
    await db.flush()

    return AdminOrderStatusHistoryResponse(
        id=history_entry.id,
        from_status=history_entry.from_status,
        to_status=history_entry.to_status,
        note=history_entry.note,
        changed_by_user_id=history_entry.changed_by_user_id,
        changed_by_user_email=actor_user.email if actor_user else None,
        created_at=history_entry.created_at,
    )


async def list_order_notes(
    db: AsyncSession,
    order_id: int,
) -> List[AdminOrderStatusHistoryResponse]:
    """Retrieve operational timeline notes for an order."""
    stmt = (
        select(OrderStatusHistory)
        .options(selectinload(OrderStatusHistory.changed_by_user))
        .where(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.created_at.asc())
    )
    res = await db.execute(stmt)
    history = res.scalars().all()

    return [
        AdminOrderStatusHistoryResponse(
            id=h.id,
            from_status=h.from_status,
            to_status=h.to_status,
            note=h.note,
            changed_by_user_id=h.changed_by_user_id,
            changed_by_user_email=h.changed_by_user.email if h.changed_by_user else None,
            created_at=h.created_at,
        )
        for h in history
    ]


async def reconcile_order_cod(
    db: AsyncSession,
    order_id: int,
    req: OrderCODReconciliationRequest,
    actor_user: Optional[User] = None,
) -> OrderResponse:
    """
    Reconcile courier remittance for Cash on Delivery orders.
    Verifies collected cash against order payable total and syncs order payment status.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.status_history),
        )
        .where(Order.id == order_id)
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    cod_payment = next((p for p in order.payments if p.payment_method == "cod"), None)
    if not cod_payment:
        raise AppException(
            message="No Cash on Delivery payment record found for this order",
            code="NO_COD_PAYMENT",
            status_code=400,
        )

    cod_payment.amount_collected = req.amount_collected
    cod_payment.amount_outstanding = max(Decimal("0.00"), cod_payment.amount - req.amount_collected)
    cod_payment.settlement_reference = req.remittance_reference
    cod_payment.reconciled_at = datetime.now(timezone.utc)
    cod_payment.reconciled_by_user_id = actor_user.id if actor_user else None
    if req.notes:
        cod_payment.notes = req.notes

    if cod_payment.amount_collected >= cod_payment.amount:
        cod_payment.status = "reconciled"
        order.payment_status = "paid"
    else:
        cod_payment.status = "partially_collected"
        order.payment_status = "partially_paid"

    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.cod_reconciled",
        entity_type="payment",
        entity_id=str(cod_payment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "order_number": order.order_number,
            "remittance_reference": req.remittance_reference,
            "amount_collected": str(req.amount_collected),
            "payment_status": cod_payment.status,
            "notes": req.notes,
        },
    )
    await db.flush()

    return build_order_response(order)
