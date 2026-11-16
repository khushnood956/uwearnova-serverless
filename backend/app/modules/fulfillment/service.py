"""
Fulfillment and Shipment Service Layer (Module M15)
Business logic for parcel creation, courier assignment, fulfillment status progression,
manual tracking checkpoints, order history preservation, and staff authorization.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import secrets
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.fulfillment.models import Shipment, ShipmentEvent, ShipmentItem
from app.modules.fulfillment.provider import get_courier_provider
from app.modules.fulfillment.schemas import (
    OrderTrackingTimelineResponse,
    ShipmentCreateRequest,
    ShipmentEventCreateRequest,
    ShipmentEventResponse,
    ShipmentItemResponse,
    ShipmentResponse,
    ShipmentStatusUpdateRequest,
    ShipmentTrackingUpdateRequest,
)
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory


def generate_shipment_number() -> str:
    """Generate unique human-readable shipment number: SHP-YYYYMMDD-XXXXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_hex = secrets.token_hex(3).upper()
    return f"SHP-{date_str}-{random_hex}"


def build_shipment_response(shipment: Shipment) -> ShipmentResponse:
    """Safely build ShipmentResponse from model instance without async lazy load errors."""
    items = [
        ShipmentItemResponse(
            id=item.id,
            order_item_id=item.order_item_id,
            quantity=item.quantity,
            product_name_snapshot=item.product_name_snapshot,
            sku_snapshot=item.sku_snapshot,
            size_snapshot=item.size_snapshot,
            color_snapshot=item.color_snapshot,
        )
        for item in (shipment.items if "items" in shipment.__dict__ else [])
    ]

    events = [
        ShipmentEventResponse(
            id=ev.id,
            status=ev.status,
            location=ev.location,
            description=ev.description,
            source=ev.source,
            recorded_by_user_id=ev.recorded_by_user_id,
            occurred_at=ev.occurred_at,
            notes=ev.notes,
        )
        for ev in (shipment.events if "events" in shipment.__dict__ else [])
    ]

    return ShipmentResponse(
        id=shipment.id,
        shipment_number=shipment.shipment_number,
        order_id=shipment.order_id,
        courier_code=shipment.courier_code,
        courier_name=shipment.courier_name,
        tracking_number=shipment.tracking_number,
        tracking_url=shipment.tracking_url,
        status=shipment.status,
        shipping_method_code=shipment.shipping_method_code,
        destination_city=shipment.destination_city,
        total_weight_grams=shipment.total_weight_grams,
        package_count=shipment.package_count,
        cod_amount_to_collect=shipment.cod_amount_to_collect,
        dispatch_notes=shipment.dispatch_notes,
        allocated_at=shipment.allocated_at,
        packed_at=shipment.packed_at,
        dispatched_at=shipment.dispatched_at,
        estimated_delivery_at=shipment.estimated_delivery_at,
        delivered_at=shipment.delivered_at,
        items=items,
        events=events,
        created_at=shipment.created_at,
    )


async def create_shipment_for_order(
    db: AsyncSession,
    order_id: int,
    req: ShipmentCreateRequest,
    actor_user: Optional[User] = None,
) -> ShipmentResponse:
    """
    Create a shipment parcel for an order.
    Requires permission: 'shipments.manage'.
    Allocates line items, assigns carrier, formats consignment tracking, and records audit history.
    """
    # 1. Fetch Order with Items and Existing Shipments
    order_stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.shipments).selectinload(Shipment.items),
        )
        .where(Order.id == order_id)
    )
    res = await db.execute(order_stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status in ("cancelled", "returned", "refunded"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot fulfill order with status '{order.status}'",
        )

    # 2. Parse Shipping Address Snapshot
    try:
        addr = json.loads(order.shipping_address_snapshot)
    except Exception:
        addr = {}

    destination_city = addr.get("city") or "Pakistan"

    # 3. Determine Items Allocation and Validate Quantities
    order_items_map = {item.id: item for item in order.items}

    # Count already fulfilled quantities across active (non-cancelled) shipments
    already_fulfilled: Dict[int, int] = {item.id: 0 for item in order.items}
    for existing_shipment in order.shipments:
        if existing_shipment.status != "cancelled":
            for s_item in existing_shipment.items:
                already_fulfilled[s_item.order_item_id] = (
                    already_fulfilled.get(s_item.order_item_id, 0) + s_item.quantity
                )

    allocations: List[Tuple[OrderItem, int]] = []
    if req.items:
        for it_req in req.items:
            if it_req.order_item_id not in order_items_map:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {it_req.order_item_id} does not belong to order {order.order_number}",
                )
            target_item = order_items_map[it_req.order_item_id]
            remaining = target_item.quantity - already_fulfilled.get(target_item.id, 0)
            if it_req.quantity > remaining:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Requested quantity ({it_req.quantity}) exceeds remaining unfulfilled "
                        f"quantity ({remaining}) for SKU {target_item.sku_snapshot}"
                    ),
                )
            allocations.append((target_item, it_req.quantity))
    else:
        # Default: allocate all remaining unfulfilled items
        for item in order.items:
            remaining = item.quantity - already_fulfilled.get(item.id, 0)
            if remaining > 0:
                allocations.append((item, remaining))

    if not allocations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All items in this order have already been allocated to existing shipments",
        )

    # 4. Resolve COD Collection Amount
    cod_amount = Decimal("0.00")
    if order.payment_method == "cod" and order.payment_status != "paid":
        if req.cod_amount_to_collect is not None:
            cod_amount = req.cod_amount_to_collect
        else:
            # Entire outstanding order amount
            cod_amount = order.grand_total

    # 5. Book Consignment / Carrier Reference
    shipment_number = generate_shipment_number()
    provider = get_courier_provider(req.courier_code)

    consignment = await provider.book_consignment(
        shipment_number=shipment_number,
        destination_city=destination_city,
        destination_address=addr,
        cod_amount=cod_amount,
        weight_grams=req.total_weight_grams,
        order_number=order.order_number,
        customer_phone=order.customer_phone,
        customer_name=order.customer_name,
        manual_tracking_number=req.tracking_number,
    )

    courier_name = req.courier_name or consignment.courier_name
    tracking_num = req.tracking_number or consignment.tracking_number
    tracking_url = req.tracking_url or consignment.tracking_url

    # 6. Create Shipment Record
    shipment = Shipment(
        shipment_number=shipment_number,
        order_id=order.id,
        courier_code=consignment.courier_code,
        courier_name=courier_name,
        tracking_number=tracking_num,
        tracking_url=tracking_url,
        status="allocated",
        shipping_method_code=order.shipping_method_code,
        shipping_address_snapshot=order.shipping_address_snapshot,
        destination_city=destination_city,
        total_weight_grams=req.total_weight_grams,
        package_count=req.package_count,
        cod_amount_to_collect=cod_amount,
        dispatch_notes=req.dispatch_notes,
        allocated_at=datetime.now(timezone.utc),
        created_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(shipment)
    await db.flush()

    # 7. Create Shipment Items
    for target_item, qty in allocations:
        s_item = ShipmentItem(
            shipment_id=shipment.id,
            order_item_id=target_item.id,
            quantity=qty,
            product_name_snapshot=target_item.product_name_snapshot,
            sku_snapshot=target_item.sku_snapshot,
            size_snapshot=target_item.size_snapshot,
            color_snapshot=target_item.color_snapshot,
        )
        db.add(s_item)

    # 8. Record Initial Tracking Event
    init_event = ShipmentEvent(
        shipment_id=shipment.id,
        status="allocated",
        location="Warehouse Fulfillment Center",
        description=f"Shipment allocated to carrier '{courier_name}'. Consignment reference: {tracking_num or 'Pending'}",
        source="staff",
        recorded_by_user_id=actor_user.id if actor_user else None,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(init_event)

    # 9. Update Order Fulfillment Status
    # Calculate new total fulfilled
    total_ordered_units = sum(i.quantity for i in order.items)
    new_fulfilled_units = sum(already_fulfilled.values()) + sum(q for _, q in allocations)

    if new_fulfilled_units >= total_ordered_units:
        order.fulfillment_status = "fulfilled"
    else:
        order.fulfillment_status = "partially_fulfilled"

    # Order History Preservation
    history = OrderStatusHistory(
        order_id=order.id,
        from_status=order.status,
        to_status=order.status,
        note=f"Shipment {shipment_number} created with carrier '{courier_name}'"[:255],
        changed_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(history)
    await db.flush()

    # 10. Audit Logging
    await log_audit_event(
        db=db,
        action="shipment.created",
        entity_type="shipment",
        entity_id=str(shipment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "shipment_number": shipment_number,
            "order_number": order.order_number,
            "courier_code": consignment.courier_code,
            "tracking_number": tracking_num,
            "destination_city": destination_city,
            "items_count": len(allocations),
        },
    )

    # Re-fetch shipment with eager relations
    return await get_shipment_by_id(db, shipment.id)


async def update_shipment_status(
    db: AsyncSession,
    shipment_id: int,
    req: ShipmentStatusUpdateRequest,
    actor_user: Optional[User] = None,
) -> ShipmentResponse:
    """
    Advance shipment fulfillment state machine.
    Requires permission: 'shipments.manage'.
    Validates status transitions, updates timestamps, updates parent order states,
    and records an immutable tracking event checkpoint.
    """
    shipment_stmt = (
        select(Shipment)
        .options(
            selectinload(Shipment.order).selectinload(Order.shipments),
            selectinload(Shipment.items),
            selectinload(Shipment.events),
        )
        .where(Shipment.id == shipment_id)
    )
    res = await db.execute(shipment_stmt)
    shipment = res.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    current_status = shipment.status
    target_status = req.status.lower().strip()

    valid_statuses = {
        "allocated",
        "packing",
        "packed",
        "ready_for_pickup",
        "dispatched",
        "in_transit",
        "out_for_delivery",
        "delivered",
        "delivery_failed",
        "returned_to_origin",
        "cancelled",
    }
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid fulfillment status '{target_status}'. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    # Valid State Transition Matrix
    allowed_transitions: Dict[str, set] = {
        "allocated": {"packing", "packed", "ready_for_pickup", "dispatched", "cancelled"},
        "packing": {"packed", "ready_for_pickup", "dispatched", "cancelled"},
        "packed": {"ready_for_pickup", "dispatched", "cancelled"},
        "ready_for_pickup": {"dispatched", "cancelled"},
        "dispatched": {"in_transit", "out_for_delivery", "delivered", "delivery_failed", "returned_to_origin"},
        "in_transit": {"out_for_delivery", "delivered", "delivery_failed", "returned_to_origin"},
        "out_for_delivery": {"delivered", "delivery_failed", "returned_to_origin"},
        "delivery_failed": {"out_for_delivery", "delivered", "returned_to_origin"},
        "delivered": set(),  # Terminal state
        "returned_to_origin": set(),  # Terminal state
        "cancelled": set(),  # Terminal state
    }

    if target_status != current_status and target_status not in allowed_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition shipment from '{current_status}' to '{target_status}'",
        )

    now = datetime.now(timezone.utc)
    shipment.status = target_status

    # Update state-specific timestamps
    if target_status == "packed" and not shipment.packed_at:
        shipment.packed_at = now
    elif target_status in ("dispatched", "in_transit") and not shipment.dispatched_at:
        shipment.dispatched_at = now
    elif target_status == "delivered" and not shipment.delivered_at:
        shipment.delivered_at = now

    # Append Tracking Event
    desc = req.description or f"Shipment status transitioned to {target_status.replace('_', ' ').title()}"
    event = ShipmentEvent(
        shipment_id=shipment.id,
        status=target_status,
        location=req.location,
        description=desc,
        source="staff",
        recorded_by_user_id=actor_user.id if actor_user else None,
        occurred_at=now,
        notes=req.notes,
    )
    db.add(event)

    # Synchronize Parent Order
    order = shipment.order
    if order:
        prev_order_status = order.status
        if target_status == "packed":
            if order.status in ("pending_confirmation", "confirmed", "processing"):
                order.status = "packed"
        elif target_status in ("dispatched", "in_transit"):
            if order.status != "shipped" and order.status != "delivered":
                order.status = "shipped"
        elif target_status == "delivered":
            # Check if all shipments for this order are delivered
            all_delivered = all(s.status == "delivered" for s in order.shipments if s.id != shipment.id)
            if all_delivered:
                order.status = "delivered"
        elif target_status == "cancelled":
            # Recalculate fulfillment status
            non_cancelled = [s for s in order.shipments if s.id != shipment.id and s.status != "cancelled"]
            if not non_cancelled:
                order.fulfillment_status = "unfulfilled"
            else:
                order.fulfillment_status = "partially_fulfilled"

        # Record Order Status History
        history = OrderStatusHistory(
            order_id=order.id,
            from_status=prev_order_status,
            to_status=order.status,
            note=f"Shipment {shipment.shipment_number} updated to '{target_status}': {desc}"[:255],
            changed_by_user_id=actor_user.id if actor_user else None,
        )
        db.add(history)

    await db.flush()

    await log_audit_event(
        db=db,
        action="shipment.status_updated",
        entity_type="shipment",
        entity_id=str(shipment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "shipment_number": shipment.shipment_number,
            "previous_status": current_status,
            "new_status": target_status,
            "location": req.location,
            "description": desc,
        },
    )

    return await get_shipment_by_id(db, shipment.id)


async def update_shipment_tracking(
    db: AsyncSession,
    shipment_id: int,
    req: ShipmentTrackingUpdateRequest,
    actor_user: Optional[User] = None,
) -> ShipmentResponse:
    """
    Update carrier tracking reference or consignment link.
    Requires permission: 'shipments.manage'.
    """
    shipment_stmt = (
        select(Shipment)
        .options(selectinload(Shipment.order))
        .where(Shipment.id == shipment_id)
    )
    res = await db.execute(shipment_stmt)
    shipment = res.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    provider = get_courier_provider(req.courier_code or shipment.courier_code)

    previous_tracking = shipment.tracking_number
    shipment.tracking_number = req.tracking_number.strip()
    if req.courier_code:
        shipment.courier_code = req.courier_code
        shipment.courier_name = provider.display_name

    shipment.tracking_url = req.tracking_url or provider.generate_tracking_url(shipment.tracking_number)

    event = ShipmentEvent(
        shipment_id=shipment.id,
        status=shipment.status,
        description=f"Tracking reference updated from '{previous_tracking or 'None'}' to '{shipment.tracking_number}'",
        source="staff",
        recorded_by_user_id=actor_user.id if actor_user else None,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()

    await log_audit_event(
        db=db,
        action="shipment.tracking_updated",
        entity_type="shipment",
        entity_id=str(shipment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "shipment_number": shipment.shipment_number,
            "previous_tracking": previous_tracking,
            "new_tracking": shipment.tracking_number,
            "courier_code": shipment.courier_code,
        },
    )

    return await get_shipment_by_id(db, shipment.id)


async def record_shipment_event(
    db: AsyncSession,
    shipment_id: int,
    req: ShipmentEventCreateRequest,
    actor_user: Optional[User] = None,
) -> ShipmentEventResponse:
    """
    Record an intermediate manual tracking event (e.g. checkpoint arrival, scan, delay note)
    without advancing the state machine.
    Requires permission: 'shipments.manage'.
    """
    shipment_stmt = select(Shipment).where(Shipment.id == shipment_id)
    res = await db.execute(shipment_stmt)
    shipment = res.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    event = ShipmentEvent(
        shipment_id=shipment.id,
        status=req.status,
        location=req.location,
        description=req.description,
        source="staff",
        recorded_by_user_id=actor_user.id if actor_user else None,
        occurred_at=datetime.now(timezone.utc),
        notes=req.notes,
    )
    db.add(event)
    await db.flush()

    await log_audit_event(
        db=db,
        action="shipment.event_recorded",
        entity_type="shipment_event",
        entity_id=str(event.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "shipment_number": shipment.shipment_number,
            "status": req.status,
            "location": req.location,
            "description": req.description,
        },
    )

    return ShipmentEventResponse.model_validate(event)


async def get_shipment_by_id(db: AsyncSession, shipment_id: int) -> ShipmentResponse:
    """Retrieve full shipment record with items and tracking events."""
    stmt = (
        select(Shipment)
        .options(
            selectinload(Shipment.items),
            selectinload(Shipment.events),
        )
        .where(Shipment.id == shipment_id)
    )
    res = await db.execute(stmt)
    shipment = res.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    return build_shipment_response(shipment)


async def list_shipments(
    db: AsyncSession,
    order_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    courier_code: Optional[str] = None,
    destination_city: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ShipmentResponse], int]:
    """Search and filter shipments for administrative and staff work queues."""
    query = (
        select(Shipment)
        .options(
            selectinload(Shipment.items),
            selectinload(Shipment.events),
        )
        .order_by(Shipment.id.desc())
    )

    if order_id:
        query = query.where(Shipment.order_id == order_id)
    if status_filter:
        query = query.where(Shipment.status == status_filter)
    if courier_code:
        query = query.where(Shipment.courier_code == courier_code)
    if destination_city:
        query = query.where(Shipment.destination_city.ilike(f"%{destination_city}%"))
    if search:
        search_pat = f"%{search.strip()}%"
        query = query.where(
            (Shipment.shipment_number.ilike(search_pat))
            | (Shipment.tracking_number.ilike(search_pat))
            | (Shipment.courier_name.ilike(search_pat))
        )

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar_one()

    paginated = query.limit(limit).offset(offset)
    res = await db.execute(paginated)
    shipments = res.scalars().all()

    return [build_shipment_response(s) for s in shipments], total


async def get_order_tracking_timeline(
    db: AsyncSession,
    order_number: str,
    current_user: Optional[User] = None,
    customer_phone: Optional[str] = None,
) -> OrderTrackingTimelineResponse:
    """
    Public / customer-facing tracking view.
    Enforces customer ownership or guest phone matching.
    """
    order_stmt = (
        select(Order)
        .options(
            selectinload(Order.shipments).selectinload(Shipment.items),
            selectinload(Order.shipments).selectinload(Shipment.events),
        )
        .where(Order.order_number == order_number)
    )
    res = await db.execute(order_stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Ownership check
    if current_user and current_user.user_type == "customer":
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
    elif not current_user:
        # Guest tracking requires phone verification
        if not customer_phone or customer_phone.strip() != order.customer_phone.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer phone number verification required for guest order tracking",
            )

    try:
        addr = json.loads(order.shipping_address_snapshot)
        dest_city = addr.get("city", "Pakistan")
    except Exception:
        dest_city = "Pakistan"

    shipment_responses = [build_shipment_response(s) for s in order.shipments]

    return OrderTrackingTimelineResponse(
        order_number=order.order_number,
        order_status=order.status,
        fulfillment_status=order.fulfillment_status,
        destination_city=dest_city,
        shipments=shipment_responses,
    )
