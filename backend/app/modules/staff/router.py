"""
Staff Operations API Router (Module M20)
Provides role-filtered work queues, operational task management,
order confirmation/processing, fulfillment packing/dispatch,
warehouse stock intake/cycle counts, and customer support ticket handling.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.rbac.dependencies import (
    require_any_permission,
    require_permission,
    require_staff,
)
from app.modules.staff.schemas import (
    StaffCycleCountRequest,
    StaffDashboardSummaryResponse,
    StaffFulfillmentDispatchRequest,
    StaffFulfillmentPackRequest,
    StaffFulfillmentQueueResponse,
    StaffInventoryQueueResponse,
    StaffOrderProcessRequest,
    StaffOrderQueueResponse,
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
from app.modules.staff.service import (
    add_ticket_message,
    assign_staff_task,
    assign_support_ticket,
    create_staff_task,
    create_support_ticket,
    get_fulfillment_work_queue,
    get_inventory_work_queue,
    get_orders_work_queue,
    get_returns_work_queue,
    get_staff_dashboard_summary,
    get_staff_task_detail,
    get_support_ticket_detail,
    list_staff_tasks,
    list_support_tickets,
    staff_cycle_count,
    staff_dispatch_shipment,
    staff_pack_shipment,
    staff_process_order,
    staff_receive_stock,
    update_staff_task_status,
    update_support_ticket_status,
)

staff_router = APIRouter(prefix="/staff", tags=["Staff Operations"])


# ---------------------------------------------------------
# Staff Dashboard Overview
# ---------------------------------------------------------

@staff_router.get(
    "/dashboard",
    response_model=StaffDashboardSummaryResponse,
    summary="Get role-tailored operational staff dashboard overview",
)
async def get_staff_dashboard(
    current_user: User = Depends(require_staff()),
    db: AsyncSession = Depends(get_db),
):
    """Returns work queue metrics tailored strictly to the authenticated staff member's permissions."""
    return await get_staff_dashboard_summary(db=db, current_user=current_user)


# ---------------------------------------------------------
# Role-Specific Work Queues
# ---------------------------------------------------------

@staff_router.get(
    "/queues/orders",
    response_model=StaffOrderQueueResponse,
    summary="Order operations work queue",
    dependencies=[Depends(require_permission("orders.read"))],
)
async def list_orders_queue(
    queue_type: str = Query("all", description="Queue filter: pending_confirmation, awaiting_fulfillment, all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve operational orders work queue."""
    return await get_orders_work_queue(db=db, queue_type=queue_type, page=page, page_size=page_size)


@staff_router.get(
    "/queues/fulfillment",
    response_model=StaffFulfillmentQueueResponse,
    summary="Fulfillment & dispatch parcel work queue",
    dependencies=[Depends(require_permission("shipments.manage"))],
)
async def list_fulfillment_queue(
    stage: str = Query("all", description="Fulfillment stage: packing, dispatch, all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve parcel packaging and courier dispatch work queue."""
    return await get_fulfillment_work_queue(db=db, stage=stage, page=page, page_size=page_size)


@staff_router.get(
    "/queues/inventory",
    response_model=StaffInventoryQueueResponse,
    summary="Inventory replenishment and intake queue",
    dependencies=[Depends(require_permission("inventory.read"))],
)
async def list_inventory_queue(
    deficit_only: bool = Query(True, description="Filter only items at or below reorder threshold"),
    location_id: Optional[int] = Query(None, description="Optional warehouse location ID filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve stock replenishment and low-stock work queue."""
    return await get_inventory_work_queue(
        db=db,
        deficit_only=deficit_only,
        location_id=location_id,
        page=page,
        page_size=page_size,
    )


@staff_router.get(
    "/queues/returns",
    response_model=StaffReturnQueueResponse,
    summary="Return and exchange inspection queue",
    dependencies=[Depends(require_permission("returns.read"))],
)
async def list_returns_queue(
    stage: str = Query("all", description="Return stage: review, inspection, all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve return request inspection and processing queue."""
    return await get_returns_work_queue(db=db, stage=stage, page=page, page_size=page_size)


@staff_router.get(
    "/queues/support",
    response_model=SupportTicketListResponse,
    summary="Customer support tickets queue",
    dependencies=[Depends(require_any_permission(["customers.read", "returns.read", "orders.read"]))],
)
async def list_support_queue(
    status_filter: Optional[str] = Query("open", description="Ticket status filter"),
    unassigned_only: bool = Query(False, description="Filter unassigned tickets"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve customer support work queue."""
    return await list_support_tickets(
        db=db,
        status_filter=status_filter,
        unassigned_only=unassigned_only,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------
# Staff Order & Fulfillment Actions
# ---------------------------------------------------------

@staff_router.post(
    "/orders/{order_id}/process",
    summary="Process and confirm order for fulfillment",
    dependencies=[Depends(require_permission("orders.update"))],
)
async def process_order(
    order_id: int,
    req: StaffOrderProcessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Order Manager action: verifies and marks order confirmed for warehouse fulfillment."""
    return await staff_process_order(db=db, order_id=order_id, req=req, actor_user=current_user)


@staff_router.post(
    "/fulfillment/{shipment_id}/pack",
    summary="Pack parcel and update weight/dimensions",
    dependencies=[Depends(require_permission("shipments.manage"))],
)
async def pack_shipment(
    shipment_id: int,
    req: StaffFulfillmentPackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fulfillment Staff action: packs parcel and transitions shipment to 'packed'."""
    return await staff_pack_shipment(db=db, shipment_id=shipment_id, req=req, actor_user=current_user)


@staff_router.post(
    "/fulfillment/{shipment_id}/dispatch",
    summary="Dispatch parcel with courier tracking number",
    dependencies=[Depends(require_permission("shipments.manage"))],
)
async def dispatch_shipment(
    shipment_id: int,
    req: StaffFulfillmentDispatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fulfillment Staff action: dispatches parcel with courier consignment tracking number."""
    return await staff_dispatch_shipment(db=db, shipment_id=shipment_id, req=req, actor_user=current_user)


# ---------------------------------------------------------
# Staff Stock Operations
# ---------------------------------------------------------

@staff_router.post(
    "/inventory/receive",
    summary="Warehouse stock intake receipt",
    dependencies=[Depends(require_permission("inventory.adjust"))],
)
async def receive_stock(
    req: StaffStockReceiveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inventory Manager action: warehouse stock intake receipt with audit movement logging."""
    return await staff_receive_stock(db=db, req=req, actor_user=current_user)


@staff_router.post(
    "/inventory/cycle-count",
    summary="Physical inventory cycle count adjustment",
    dependencies=[Depends(require_permission("inventory.adjust"))],
)
async def cycle_count(
    req: StaffCycleCountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inventory Manager action: records physical cycle count adjustment with audit movement logging."""
    return await staff_cycle_count(db=db, req=req, actor_user=current_user)


# ---------------------------------------------------------
# Customer Support Tickets Management
# ---------------------------------------------------------

@staff_router.post(
    "/support/tickets",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer support case ticket",
    dependencies=[Depends(require_any_permission(["customers.read", "orders.read", "returns.read"]))],
)
async def create_ticket(
    req: SupportTicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Customer Support action: create support case for client inquiry or issue."""
    return await create_support_ticket(db=db, req=req, actor_user=current_user)


@staff_router.get(
    "/support/tickets",
    response_model=SupportTicketListResponse,
    summary="List support tickets with filtering",
    dependencies=[Depends(require_any_permission(["customers.read", "orders.read", "returns.read"]))],
)
async def list_tickets(
    status_filter: Optional[str] = Query(None, description="Status filter: open, in_progress, waiting_customer, resolved, closed"),
    category_filter: Optional[str] = Query(None, description="Category filter"),
    priority_filter: Optional[str] = Query(None, description="Priority filter"),
    assigned_staff_id: Optional[int] = Query(None, description="Assigned staff user ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List customer support tickets."""
    return await list_support_tickets(
        db=db,
        status_filter=status_filter,
        category_filter=category_filter,
        priority_filter=priority_filter,
        assigned_staff_id=assigned_staff_id,
        page=page,
        page_size=page_size,
    )


@staff_router.get(
    "/support/tickets/{ticket_id}",
    response_model=SupportTicketResponse,
    summary="Get support ticket details and conversation thread",
    dependencies=[Depends(require_any_permission(["customers.read", "orders.read", "returns.read"]))],
)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve support ticket detail and conversation history."""
    return await get_support_ticket_detail(db=db, ticket_id=ticket_id)


@staff_router.post(
    "/support/tickets/{ticket_id}/assign",
    response_model=SupportTicketResponse,
    summary="Assign support ticket to staff member",
    dependencies=[Depends(require_any_permission(["customers.read", "orders.read", "returns.read"]))],
)
async def assign_ticket(
    ticket_id: int,
    req: SupportTicketAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign ticket to specific staff user."""
    return await assign_support_ticket(
        db=db,
        ticket_id=ticket_id,
        staff_user_id=req.staff_user_id,
        actor_user=current_user,
    )


@staff_router.post(
    "/support/tickets/{ticket_id}/messages",
    response_model=SupportTicketMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add response message or internal note to ticket",
    dependencies=[Depends(require_any_permission(["customers.read", "orders.read", "returns.read"]))],
)
async def post_ticket_message(
    ticket_id: int,
    req: SupportTicketMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Append response or internal operational note to ticket."""
    return await add_ticket_message(
        db=db,
        ticket_id=ticket_id,
        req=req,
        actor_user=current_user,
    )


@staff_router.patch(
    "/support/tickets/{ticket_id}/status",
    response_model=SupportTicketResponse,
    summary="Update support ticket status",
    dependencies=[Depends(require_any_permission(["customers.read", "orders.read", "returns.read"]))],
)
async def update_ticket_status(
    ticket_id: int,
    req: SupportTicketStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update support ticket status with optional resolution notes."""
    return await update_support_ticket_status(
        db=db,
        ticket_id=ticket_id,
        req=req,
        actor_user=current_user,
    )


# ---------------------------------------------------------
# Staff Tasks & Task Assignment
# ---------------------------------------------------------

@staff_router.post(
    "/tasks",
    response_model=StaffTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an operational work task",
    dependencies=[Depends(require_staff())],
)
async def create_task(
    req: StaffTaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an operational task item and optionally assign to staff."""
    return await create_staff_task(db=db, req=req, creator_user=current_user)


@staff_router.get(
    "/tasks",
    response_model=StaffTaskListResponse,
    summary="List operational staff tasks",
    dependencies=[Depends(require_staff())],
)
async def list_tasks(
    assigned_to_me: bool = Query(False, description="Filter only tasks assigned to caller"),
    status_filter: Optional[str] = Query(None, description="Status filter: pending, in_progress, completed, cancelled"),
    task_type: Optional[str] = Query(None, description="Task type filter"),
    priority: Optional[str] = Query(None, description="Priority filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List operational work tasks."""
    assigned_staff_id = current_user.id if assigned_to_me else None
    return await list_staff_tasks(
        db=db,
        assigned_staff_id=assigned_staff_id,
        status_filter=status_filter,
        task_type=task_type,
        priority=priority,
        page=page,
        page_size=page_size,
    )


@staff_router.get(
    "/tasks/{task_id}",
    response_model=StaffTaskResponse,
    summary="Get operational task detail",
    dependencies=[Depends(require_staff())],
)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get operational task detail."""
    return await get_staff_task_detail(db=db, task_id=task_id)


@staff_router.post(
    "/tasks/{task_id}/assign",
    response_model=StaffTaskResponse,
    summary="Assign task to staff member",
    dependencies=[Depends(require_staff())],
)
async def assign_task(
    task_id: int,
    req: StaffTaskAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign operational task to a staff member."""
    return await assign_staff_task(
        db=db,
        task_id=task_id,
        staff_user_id=req.staff_user_id,
        actor_user=current_user,
    )


@staff_router.patch(
    "/tasks/{task_id}/status",
    response_model=StaffTaskResponse,
    summary="Update task status",
    dependencies=[Depends(require_staff())],
)
async def update_task_status(
    task_id: int,
    req: StaffTaskStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update task execution status (in_progress, completed, cancelled) with resolution notes."""
    return await update_staff_task_status(
        db=db,
        task_id=task_id,
        req=req,
        actor_user=current_user,
    )
