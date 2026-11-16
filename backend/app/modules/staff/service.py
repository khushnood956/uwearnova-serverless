"""
Staff Operations Service Layer (Module M20)
Provides role-filtered work queues, operational task assignment,
order processing, warehouse fulfillment (packing and dispatch),
stock intake and cycle counts, and customer support ticket handling.
"""

from datetime import datetime, timezone
from decimal import Decimal
import secrets
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.catalog.models import Product, ProductVariant
from app.modules.fulfillment.models import Shipment, ShipmentEvent
from app.modules.fulfillment.schemas import ShipmentStatusUpdateRequest, ShipmentTrackingUpdateRequest
from app.modules.fulfillment.service import update_shipment_status, update_shipment_tracking
from app.modules.inventory.models import InventoryItem, InventoryLocation, InventoryMovement
from app.modules.inventory.schemas import StockAdjustmentRequest
from app.modules.inventory.service import adjust_stock, get_or_create_inventory_item
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory
from app.modules.orders.service import add_order_note, confirm_order_admin
from app.modules.rbac.service import get_user_permissions
from app.modules.returns.models import ReturnItem, ReturnRequest
from app.modules.staff.models import StaffProfile, StaffTask, SupportTicket, SupportTicketMessage
from app.modules.staff.schemas import (
    StaffCycleCountRequest,
    StaffDashboardSummaryResponse,
    StaffFulfillmentDispatchRequest,
    StaffFulfillmentPackRequest,
    StaffFulfillmentQueueItem,
    StaffFulfillmentQueueResponse,
    StaffInventoryQueueItem,
    StaffInventoryQueueResponse,
    StaffOrderProcessRequest,
    StaffOrderQueueItem,
    StaffOrderQueueResponse,
    StaffReturnQueueItem,
    StaffReturnQueueResponse,
    StaffStockReceiveRequest,
    StaffTaskAssignRequest,
    StaffTaskCreateRequest,
    StaffTaskListResponse,
    StaffTaskResponse,
    StaffTaskStatusUpdateRequest,
    SupportTicketAssignRequest,
    SupportTicketCreateRequest,
    SupportTicketListResponse,
    SupportTicketMessageCreateRequest,
    SupportTicketMessageResponse,
    SupportTicketResponse,
    SupportTicketStatusUpdateRequest,
)


def generate_ticket_number() -> str:
    """Generate unique support ticket reference: TKT-YYYYMMDD-XXXXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_hex = secrets.token_hex(3).upper()
    return f"TKT-{date_str}-{random_hex}"


def generate_task_number() -> str:
    """Generate unique task reference: TSK-YYYYMMDD-XXXXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_hex = secrets.token_hex(3).upper()
    return f"TSK-{date_str}-{random_hex}"


# ---------------------------------------------------------
# Staff Dashboard Summary
# ---------------------------------------------------------

async def get_staff_dashboard_summary(
    db: AsyncSession,
    current_user: User,
) -> StaffDashboardSummaryResponse:
    """
    Generate customized operational dashboard summary based strictly on
    the authenticated staff member's granted permissions.
    """
    perms = await get_user_permissions(db, current_user.id)
    user_roles = [r.name for r in (current_user.roles or [])]

    # Tasks assigned to this user
    task_stmt = select(func.count(StaffTask.id)).where(
        StaffTask.assigned_staff_id == current_user.id,
        StaffTask.status.in_(["pending", "in_progress"]),
    )
    task_res = await db.execute(task_stmt)
    assigned_tasks_count = task_res.scalar() or 0

    orders_count: Optional[int] = None
    if "orders.read" in perms:
        o_stmt = select(func.count(Order.id)).where(
            Order.status.in_(["pending", "pending_confirmation", "confirmed", "processing"]),
        )
        o_res = await db.execute(o_stmt)
        orders_count = o_res.scalar() or 0

    fulfillment_count: Optional[int] = None
    if "shipments.manage" in perms:
        f_stmt = select(func.count(Shipment.id)).where(
            Shipment.status.in_(["created", "allocated", "packing", "packed", "ready_for_pickup"]),
        )
        f_res = await db.execute(f_stmt)
        fulfillment_count = f_res.scalar() or 0

    inventory_count: Optional[int] = None
    if "inventory.read" in perms:
        i_stmt = select(func.count(InventoryItem.id)).where(
            (InventoryItem.quantity_on_hand - InventoryItem.quantity_reserved) <= InventoryItem.reorder_threshold
        )
        i_res = await db.execute(i_stmt)
        inventory_count = i_res.scalar() or 0

    returns_count: Optional[int] = None
    if "returns.read" in perms:
        r_stmt = select(func.count(ReturnRequest.id)).where(
            ReturnRequest.status.in_(["requested", "approved", "received"]),
        )
        r_res = await db.execute(r_stmt)
        returns_count = r_res.scalar() or 0

    support_count: Optional[int] = None
    if "customers.read" in perms or "returns.read" in perms or "dashboard.read" in perms:
        s_stmt = select(func.count(SupportTicket.id)).where(
            SupportTicket.status.in_(["open", "in_progress"]),
        )
        s_res = await db.execute(s_stmt)
        support_count = s_res.scalar() or 0

    return StaffDashboardSummaryResponse(
        staff_user_id=current_user.id,
        email=current_user.email,
        roles=user_roles,
        permissions=sorted(list(perms)),
        assigned_tasks_count=assigned_tasks_count,
        orders_queue_count=orders_count,
        fulfillment_queue_count=fulfillment_count,
        inventory_low_stock_count=inventory_count,
        returns_queue_count=returns_count,
        support_tickets_queue_count=support_count,
    )


# ---------------------------------------------------------
# Role-Specific Work Queues
# ---------------------------------------------------------

async def get_orders_work_queue(
    db: AsyncSession,
    queue_type: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> StaffOrderQueueResponse:
    """Retrieve operational orders work queue."""
    query = select(Order).options(selectinload(Order.items))

    if queue_type == "pending_confirmation":
        query = query.where(Order.status.in_(["pending", "pending_confirmation"]))
    elif queue_type == "awaiting_fulfillment":
        query = query.where(
            Order.status == "confirmed",
            Order.fulfillment_status.in_(["unfulfilled", "partially_fulfilled"]),
        )
    else:
        query = query.where(Order.status.in_(["pending", "pending_confirmation", "confirmed", "processing"]))

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Paginate
    query = query.order_by(Order.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    items = []
    for o in orders:
        op_stage = "verify" if o.status in ("pending", "pending_confirmation") else "pack"
        city = ""
        if o.shipping_address_snapshot:
            if isinstance(o.shipping_address_snapshot, str):
                try:
                    import json
                    city = json.loads(o.shipping_address_snapshot).get("city", "")
                except Exception:
                    city = ""
            elif isinstance(o.shipping_address_snapshot, dict):
                city = o.shipping_address_snapshot.get("city", "")
        items.append(
            StaffOrderQueueItem(
                order_id=o.id,
                order_number=o.order_number,
                status=o.status,
                payment_status=o.payment_status,
                payment_method=o.payment_method,
                fulfillment_status=o.fulfillment_status,
                total_amount=o.grand_total,
                currency=o.currency_code,
                item_count=len(o.items or []),
                customer_email=o.customer_email,
                customer_name=o.customer_name or "",
                customer_city=city,
                created_at=o.created_at,
                operational_stage=op_stage,
            )
        )

    return StaffOrderQueueResponse(items=items, total=total, page=page, page_size=page_size)


async def get_fulfillment_work_queue(
    db: AsyncSession,
    stage: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> StaffFulfillmentQueueResponse:
    """Retrieve parcel packaging and courier dispatch work queue."""
    query = select(Shipment).options(
        selectinload(Shipment.items),
        selectinload(Shipment.order),
    )

    if stage == "packing":
        query = query.where(Shipment.status.in_(["created", "allocated", "packing"]))
    elif stage == "dispatch":
        query = query.where(Shipment.status.in_(["packed", "ready_for_pickup"]))
    else:
        query = query.where(Shipment.status.in_(["created", "allocated", "packing", "packed", "ready_for_pickup"]))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(Shipment.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    shipments = result.scalars().all()

    items = []
    for s in shipments:
        city = ""
        if s.shipping_address_snapshot:
            if isinstance(s.shipping_address_snapshot, str):
                try:
                    import json
                    city = json.loads(s.shipping_address_snapshot).get("city", "")
                except Exception:
                    city = ""
            elif isinstance(s.shipping_address_snapshot, dict):
                city = s.shipping_address_snapshot.get("city", "")
        order_num = s.order.order_number if s.order else f"ORD-{s.order_id}"
        items.append(
            StaffFulfillmentQueueItem(
                shipment_id=s.id,
                shipment_number=s.shipment_number,
                order_id=s.order_id,
                order_number=order_num,
                courier_code=s.courier_code,
                status=s.status,
                item_count=len(s.items or []),
                shipping_city=city,
                created_at=s.created_at,
                tracking_number=s.tracking_number,
            )
        )

    return StaffFulfillmentQueueResponse(items=items, total=total, page=page, page_size=page_size)


async def get_inventory_work_queue(
    db: AsyncSession,
    deficit_only: bool = True,
    location_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> StaffInventoryQueueResponse:
    """Retrieve stock replenishment and intake queue."""
    query = (
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.variant).selectinload(ProductVariant.product),
            selectinload(InventoryItem.location),
        )
    )

    if location_id is not None:
        query = query.where(InventoryItem.location_id == location_id)

    if deficit_only:
        query = query.where(
            (InventoryItem.quantity_on_hand - InventoryItem.quantity_reserved) <= InventoryItem.reorder_threshold
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(InventoryItem.id.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    inv_items = result.scalars().all()

    items = []
    for it in inv_items:
        v = it.variant
        p = v.product if v else None
        loc = it.location
        available = max(0, it.quantity_on_hand - it.quantity_reserved)
        deficit = max(0, it.reorder_threshold - available)
        items.append(
            StaffInventoryQueueItem(
                variant_id=it.variant_id,
                sku=v.sku if v else f"VAR-{it.variant_id}",
                product_id=p.id if p else 0,
                product_title=p.name if p else "Unknown Product",
                location_id=it.location_id,
                location_name=loc.name if loc else "Warehouse",
                quantity_on_hand=it.quantity_on_hand,
                quantity_reserved=it.quantity_reserved,
                quantity_available=available,
                reorder_threshold=it.reorder_threshold,
                deficit=deficit,
            )
        )

    return StaffInventoryQueueResponse(items=items, total=total, page=page, page_size=page_size)


async def get_returns_work_queue(
    db: AsyncSession,
    stage: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> StaffReturnQueueResponse:
    """Retrieve return request inspection and processing queue."""
    query = select(ReturnRequest).options(
        selectinload(ReturnRequest.items),
        selectinload(ReturnRequest.order),
    )

    if stage == "review":
        query = query.where(ReturnRequest.status == "requested")
    elif stage == "inspection":
        query = query.where(ReturnRequest.status.in_(["approved", "received"]))
    else:
        query = query.where(ReturnRequest.status.in_(["requested", "approved", "received"]))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(ReturnRequest.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    returns = result.scalars().all()

    items = []
    for r in returns:
        order_num = r.order.order_number if r.order else f"ORD-{r.order_id}"
        q_stage = "review" if r.status == "requested" else "inspection"
        items.append(
            StaffReturnQueueItem(
                request_id=r.id,
                request_number=r.request_number,
                order_id=r.order_id,
                order_number=order_num,
                status=r.status,
                request_type=r.request_type,
                item_count=len(r.items or []),
                created_at=r.created_at,
                stage=q_stage,
            )
        )

    return StaffReturnQueueResponse(items=items, total=total, page=page, page_size=page_size)


# ---------------------------------------------------------
# Support Tickets Service
# ---------------------------------------------------------

def _build_support_ticket_response(ticket: SupportTicket) -> SupportTicketResponse:
    """Construct full SupportTicketResponse with message thread."""
    messages = [
        SupportTicketMessageResponse(
            id=m.id,
            ticket_id=m.ticket_id,
            sender_user_id=m.sender_user_id,
            sender_type=m.sender_type,
            sender_name=m.sender_name,
            message=m.message,
            is_internal_note=m.is_internal_note,
            created_at=m.created_at,
        )
        for m in (ticket.messages or [])
    ]

    order_num = ticket.order.order_number if getattr(ticket, "order", None) else None
    staff_email = ticket.assigned_staff.email if getattr(ticket, "assigned_staff", None) else None

    return SupportTicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        customer_id=ticket.customer_id,
        customer_email=ticket.customer_email,
        customer_name=ticket.customer_name,
        order_id=ticket.order_id,
        order_number=order_num,
        subject=ticket.subject,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        assigned_staff_id=ticket.assigned_staff_id,
        assigned_staff_email=staff_email,
        assigned_at=ticket.assigned_at,
        resolved_at=ticket.resolved_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=messages,
    )


async def create_support_ticket(
    db: AsyncSession,
    req: SupportTicketCreateRequest,
    actor_user: User,
) -> SupportTicketResponse:
    """Create a new support ticket and record opening message."""
    # Find customer account by email if exists
    c_res = await db.execute(select(User).where(User.email == req.customer_email.lower()))
    customer = c_res.scalar_one_or_none()

    ticket = SupportTicket(
        ticket_number=generate_ticket_number(),
        customer_id=customer.id if customer else None,
        customer_email=req.customer_email.lower(),
        customer_name=req.customer_name,
        order_id=req.order_id,
        subject=req.subject,
        category=req.category,
        priority=req.priority,
        status="open",
        assigned_staff_id=None,
    )
    db.add(ticket)
    await db.flush()

    # Initial message
    init_msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_user_id=actor_user.id,
        sender_type="staff",
        sender_name=actor_user.email.split("@")[0].title(),
        message=req.message,
        is_internal_note=False,
    )
    db.add(init_msg)
    await db.flush()

    await log_audit_event(
        db=db,
        action="support.ticket_created",
        entity_type="support_ticket",
        entity_id=str(ticket.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "category": ticket.category,
            "customer_email": ticket.customer_email,
        },
    )

    return await get_support_ticket_detail(db, ticket.id)


async def list_support_tickets(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    assigned_staff_id: Optional[int] = None,
    unassigned_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> SupportTicketListResponse:
    """List customer support tickets with filters and pagination."""
    query = select(SupportTicket).options(
        selectinload(SupportTicket.messages),
        selectinload(SupportTicket.assigned_staff),
        selectinload(SupportTicket.order),
    )

    if status_filter:
        query = query.where(SupportTicket.status == status_filter)
    if category_filter:
        query = query.where(SupportTicket.category == category_filter)
    if priority_filter:
        query = query.where(SupportTicket.priority == priority_filter)
    if unassigned_only:
        query = query.where(SupportTicket.assigned_staff_id.is_(None))
    elif assigned_staff_id is not None:
        query = query.where(SupportTicket.assigned_staff_id == assigned_staff_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(SupportTicket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tickets = result.scalars().all()

    items = [_build_support_ticket_response(t) for t in tickets]
    return SupportTicketListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_support_ticket_detail(
    db: AsyncSession,
    ticket_id: int,
) -> SupportTicketResponse:
    """Retrieve support ticket detail and message thread."""
    query = (
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.messages),
            selectinload(SupportTicket.assigned_staff),
            selectinload(SupportTicket.order),
        )
        .where(SupportTicket.id == ticket_id)
    )
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support ticket ID {ticket_id} not found",
        )
    return _build_support_ticket_response(ticket)


async def assign_support_ticket(
    db: AsyncSession,
    ticket_id: int,
    staff_user_id: int,
    actor_user: User,
) -> SupportTicketResponse:
    """Assign ticket to a staff member."""
    # Verify staff exists
    s_res = await db.execute(select(User).where(User.id == staff_user_id))
    staff = s_res.scalar_one_or_none()
    if not staff or staff.user_type not in ("staff", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User ID {staff_user_id} is not an eligible staff member",
        )

    t_res = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = t_res.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support ticket ID {ticket_id} not found",
        )

    ticket.assigned_staff_id = staff_user_id
    ticket.assigned_at = datetime.now(timezone.utc)
    if ticket.status == "open":
        ticket.status = "in_progress"

    # Add system notification message
    sys_msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_user_id=actor_user.id,
        sender_type="system",
        sender_name="System",
        message=f"Ticket assigned to {staff.email} by {actor_user.email}",
        is_internal_note=True,
    )
    db.add(sys_msg)
    await db.flush()

    await log_audit_event(
        db=db,
        action="support.ticket_assigned",
        entity_type="support_ticket",
        entity_id=str(ticket.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "ticket_number": ticket.ticket_number,
            "assigned_staff_id": staff_user_id,
            "assigned_staff_email": staff.email,
        },
    )

    return await get_support_ticket_detail(db, ticket.id)


async def add_ticket_message(
    db: AsyncSession,
    ticket_id: int,
    req: SupportTicketMessageCreateRequest,
    actor_user: User,
) -> SupportTicketMessageResponse:
    """Append a response message or internal note to ticket."""
    t_res = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = t_res.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support ticket ID {ticket_id} not found",
        )

    msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_user_id=actor_user.id,
        sender_type="staff",
        sender_name=actor_user.email.split("@")[0].title(),
        message=req.message,
        is_internal_note=req.is_internal_note,
    )
    db.add(msg)

    if not req.is_internal_note and ticket.status == "in_progress":
        ticket.status = "waiting_customer"

    await db.flush()

    await log_audit_event(
        db=db,
        action="support.message_added",
        entity_type="support_ticket",
        entity_id=str(ticket.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "ticket_number": ticket.ticket_number,
            "is_internal_note": req.is_internal_note,
        },
    )

    return SupportTicketMessageResponse(
        id=msg.id,
        ticket_id=msg.ticket_id,
        sender_user_id=msg.sender_user_id,
        sender_type=msg.sender_type,
        sender_name=msg.sender_name,
        message=msg.message,
        is_internal_note=msg.is_internal_note,
        created_at=msg.created_at,
    )


async def update_support_ticket_status(
    db: AsyncSession,
    ticket_id: int,
    req: SupportTicketStatusUpdateRequest,
    actor_user: User,
) -> SupportTicketResponse:
    """Update support ticket status with optional resolution notes."""
    valid_statuses = {"open", "in_progress", "waiting_customer", "resolved", "closed"}
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ticket status '{req.status}'. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    t_res = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = t_res.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support ticket ID {ticket_id} not found",
        )

    prev_status = ticket.status
    ticket.status = req.status
    now = datetime.now(timezone.utc)

    if req.status in ("resolved", "closed"):
        ticket.resolved_at = now

    # System message
    note_suffix = f" - Notes: {req.resolution_notes}" if req.resolution_notes else ""
    sys_msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_user_id=actor_user.id,
        sender_type="system",
        sender_name="System",
        message=f"Status changed from {prev_status} to {req.status} by {actor_user.email}{note_suffix}",
        is_internal_note=True,
    )
    db.add(sys_msg)
    await db.flush()

    await log_audit_event(
        db=db,
        action="support.ticket_status_updated",
        entity_type="support_ticket",
        entity_id=str(ticket.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "ticket_number": ticket.ticket_number,
            "previous_status": prev_status,
            "new_status": req.status,
            "resolution_notes": req.resolution_notes,
        },
    )

    return await get_support_ticket_detail(db, ticket.id)


# ---------------------------------------------------------
# Staff Tasks Service
# ---------------------------------------------------------

def _build_staff_task_response(task: StaffTask) -> StaffTaskResponse:
    """Build StaffTaskResponse from model."""
    staff_email = task.assigned_staff.email if getattr(task, "assigned_staff", None) else None
    return StaffTaskResponse(
        id=task.id,
        task_number=task.task_number,
        task_type=task.task_type,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assigned_staff_id=task.assigned_staff_id,
        assigned_staff_email=staff_email,
        created_by_user_id=task.created_by_user_id,
        order_id=task.order_id,
        shipment_id=task.shipment_id,
        return_request_id=task.return_request_id,
        support_ticket_id=task.support_ticket_id,
        due_date=task.due_date,
        completed_at=task.completed_at,
        resolution_notes=task.resolution_notes,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def create_staff_task(
    db: AsyncSession,
    req: StaffTaskCreateRequest,
    creator_user: User,
) -> StaffTaskResponse:
    """Create an operational work task and optionally assign it."""
    task = StaffTask(
        task_number=generate_task_number(),
        task_type=req.task_type,
        title=req.title,
        description=req.description,
        priority=req.priority,
        status="pending",
        assigned_staff_id=req.assigned_staff_id,
        created_by_user_id=creator_user.id,
        order_id=req.order_id,
        shipment_id=req.shipment_id,
        return_request_id=req.return_request_id,
        support_ticket_id=req.support_ticket_id,
        due_date=req.due_date,
    )
    db.add(task)
    await db.flush()

    await log_audit_event(
        db=db,
        action="staff.task_created",
        entity_type="staff_task",
        entity_id=str(task.id),
        user_id=creator_user.id,
        actor_email=creator_user.email,
        details={
            "task_number": task.task_number,
            "task_type": task.task_type,
            "title": task.title,
            "assigned_staff_id": task.assigned_staff_id,
        },
    )

    return await get_staff_task_detail(db, task.id)


async def list_staff_tasks(
    db: AsyncSession,
    assigned_staff_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    task_type: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> StaffTaskListResponse:
    """List operational tasks with filters."""
    query = select(StaffTask).options(selectinload(StaffTask.assigned_staff))

    if assigned_staff_id is not None:
        query = query.where(StaffTask.assigned_staff_id == assigned_staff_id)
    if status_filter:
        query = query.where(StaffTask.status == status_filter)
    if task_type:
        query = query.where(StaffTask.task_type == task_type)
    if priority:
        query = query.where(StaffTask.priority == priority)

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(StaffTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    items = [_build_staff_task_response(t) for t in tasks]
    return StaffTaskListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_staff_task_detail(
    db: AsyncSession,
    task_id: int,
) -> StaffTaskResponse:
    """Get operational task detail."""
    query = select(StaffTask).options(selectinload(StaffTask.assigned_staff)).where(StaffTask.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff task ID {task_id} not found",
        )
    return _build_staff_task_response(task)


async def assign_staff_task(
    db: AsyncSession,
    task_id: int,
    staff_user_id: int,
    actor_user: User,
) -> StaffTaskResponse:
    """Assign or reassign task to staff member."""
    s_res = await db.execute(select(User).where(User.id == staff_user_id))
    staff = s_res.scalar_one_or_none()
    if not staff or staff.user_type not in ("staff", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User ID {staff_user_id} is not an eligible staff member",
        )

    t_res = await db.execute(select(StaffTask).where(StaffTask.id == task_id))
    task = t_res.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff task ID {task_id} not found",
        )

    task.assigned_staff_id = staff_user_id
    if task.status == "pending":
        task.status = "in_progress"

    await db.flush()

    await log_audit_event(
        db=db,
        action="staff.task_assigned",
        entity_type="staff_task",
        entity_id=str(task.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "task_number": task.task_number,
            "assigned_staff_id": staff_user_id,
            "assigned_staff_email": staff.email,
        },
    )

    return await get_staff_task_detail(db, task.id)


async def update_staff_task_status(
    db: AsyncSession,
    task_id: int,
    req: StaffTaskStatusUpdateRequest,
    actor_user: User,
) -> StaffTaskResponse:
    """Update task status (e.g. mark completed with notes)."""
    valid_statuses = {"pending", "in_progress", "completed", "cancelled"}
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task status '{req.status}'. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    t_res = await db.execute(select(StaffTask).where(StaffTask.id == task_id))
    task = t_res.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff task ID {task_id} not found",
        )

    prev_status = task.status
    task.status = req.status
    if req.resolution_notes:
        task.resolution_notes = req.resolution_notes

    if req.status in ("completed", "cancelled"):
        task.completed_at = datetime.now(timezone.utc)

    await db.flush()

    await log_audit_event(
        db=db,
        action="staff.task_status_updated",
        entity_type="staff_task",
        entity_id=str(task.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "task_number": task.task_number,
            "previous_status": prev_status,
            "new_status": req.status,
            "resolution_notes": req.resolution_notes,
        },
    )

    return await get_staff_task_detail(db, task.id)


# ---------------------------------------------------------
# Staff Operational Processing Workflows
# ---------------------------------------------------------

async def staff_process_order(
    db: AsyncSession,
    order_id: int,
    req: StaffOrderProcessRequest,
    actor_user: User,
) -> Dict[str, Any]:
    """
    Order Manager operational action: confirms order and logs verification notes.
    """
    o_res = await db.execute(select(Order).where(Order.id == order_id))
    order = o_res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order ID {order_id} not found",
        )

    if order.status in ("pending", "pending_confirmation"):
        await confirm_order_admin(
            db=db,
            order_id=order.id,
            note=req.notes or "Order verified and confirmed by Order Manager for fulfillment",
            actor_user=actor_user,
        )
    elif req.notes:
        await add_order_note(
            db=db,
            order_id=order.id,
            note=req.notes,
            actor_user=actor_user,
        )

    await log_audit_event(
        db=db,
        action="staff.order_processed",
        entity_type="order",
        entity_id=str(order.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"order_number": order.order_number, "notes": req.notes},
    )

    return {"success": True, "order_id": order.id, "order_number": order.order_number, "status": order.status}


async def staff_pack_shipment(
    db: AsyncSession,
    shipment_id: int,
    req: StaffFulfillmentPackRequest,
    actor_user: User,
) -> Dict[str, Any]:
    """
    Fulfillment Staff action: packs parcel and transitions shipment to 'packed'.
    """
    update_req = ShipmentStatusUpdateRequest(
        status="packed",
        description=req.notes or "Parcel packed and sealed in warehouse",
        notes=req.notes,
    )
    shipment = await update_shipment_status(
        db=db,
        shipment_id=shipment_id,
        req=update_req,
        actor_user=actor_user,
    )

    await log_audit_event(
        db=db,
        action="staff.fulfillment_packed",
        entity_type="shipment",
        entity_id=str(shipment.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "shipment_number": shipment.shipment_number,
            "weight_kg": str(req.package_weight_kg) if req.package_weight_kg else None,
            "dimensions": req.package_dimensions,
        },
    )

    return {
        "success": True,
        "shipment_id": shipment.id,
        "shipment_number": shipment.shipment_number,
        "status": shipment.status,
    }


async def staff_dispatch_shipment(
    db: AsyncSession,
    shipment_id: int,
    req: StaffFulfillmentDispatchRequest,
    actor_user: User,
) -> Dict[str, Any]:
    """
    Fulfillment Staff action: dispatches parcel with courier consignment number.
    """
    tracking_req = ShipmentTrackingUpdateRequest(
        tracking_number=req.tracking_number,
        courier_code=req.courier_code,
        notes=req.notes,
    )
    shipment = await update_shipment_tracking(
        db=db,
        shipment_id=shipment_id,
        req=tracking_req,
        actor_user=actor_user,
    )

    dispatch_req = ShipmentStatusUpdateRequest(
        status="dispatched",
        description=req.notes or f"Dispatched with tracking #{req.tracking_number}",
        notes=req.notes,
    )
    shipment = await update_shipment_status(
        db=db,
        shipment_id=shipment_id,
        req=dispatch_req,
        actor_user=actor_user,
    )

    await log_audit_event(
        db=db,
        action="staff.fulfillment_dispatched",
        entity_type="shipment",
        entity_id=str(shipment.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "shipment_number": shipment.shipment_number,
            "tracking_number": req.tracking_number,
            "courier_code": shipment.courier_code,
        },
    )

    return {
        "success": True,
        "shipment_id": shipment.id,
        "shipment_number": shipment.shipment_number,
        "status": shipment.status,
        "tracking_number": shipment.tracking_number,
    }


async def staff_receive_stock(
    db: AsyncSession,
    req: StaffStockReceiveRequest,
    actor_user: User,
) -> Dict[str, Any]:
    """
    Inventory Manager action: warehouse stock intake receipt.
    """
    adj_req = StockAdjustmentRequest(
        variant_id=req.variant_id,
        location_id=req.location_id,
        quantity_delta=req.quantity,
        movement_type="receipt",
        reference_type="purchase_receipt",
        reference_id=req.batch_reference,
        reason_notes=req.notes or f"Staff stock receipt intake (+{req.quantity} units)",
    )
    item, movement = await adjust_stock(db, adj_req, actor_user=actor_user)

    await log_audit_event(
        db=db,
        action="staff.stock_received",
        entity_type="inventory_item",
        entity_id=str(item.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "variant_id": req.variant_id,
            "quantity_received": req.quantity,
            "new_on_hand": item.quantity_on_hand,
            "batch_reference": req.batch_reference,
        },
    )

    return {
        "success": True,
        "variant_id": item.variant_id,
        "location_id": item.location_id,
        "quantity_on_hand": item.quantity_on_hand,
        "movement_id": movement.id,
    }


async def staff_cycle_count(
    db: AsyncSession,
    req: StaffCycleCountRequest,
    actor_user: User,
) -> Dict[str, Any]:
    """
    Inventory Manager action: record physical inventory cycle count adjustment.
    """
    item = await get_or_create_inventory_item(db, req.variant_id, req.location_id, for_update=True)
    current_on_hand = item.quantity_on_hand
    delta = req.actual_quantity - current_on_hand

    adj_req = StockAdjustmentRequest(
        variant_id=req.variant_id,
        location_id=req.location_id,
        quantity_delta=delta,
        movement_type="cycle_count",
        reference_type="physical_count",
        reason_notes=f"Cycle count adjustment: {req.reason} (count={req.actual_quantity}, prior={current_on_hand})",
    )
    item, movement = await adjust_stock(db, adj_req, actor_user=actor_user)

    await log_audit_event(
        db=db,
        action="staff.cycle_count_adjusted",
        entity_type="inventory_item",
        entity_id=str(item.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "variant_id": req.variant_id,
            "actual_quantity": req.actual_quantity,
            "delta": delta,
            "reason": req.reason,
        },
    )

    return {
        "success": True,
        "variant_id": item.variant_id,
        "location_id": item.location_id,
        "prior_on_hand": current_on_hand,
        "new_on_hand": item.quantity_on_hand,
        "delta": delta,
    }
