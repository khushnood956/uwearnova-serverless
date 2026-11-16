"""
Order and Checkout API Endpoints (M12)
Storefront checkout processing, customer order history, and administrative order management.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.models import User
from app.modules.orders.models import Order
from app.modules.orders.schemas import (
    AdminOrderDetailResponse,
    AdminOrderStatusHistoryResponse,
    CheckoutRequest,
    OrderCancellationRequest,
    OrderCODReconciliationRequest,
    OrderConfirmationRequest,
    OrderListResponse,
    OrderNoteCreateRequest,
    OrderPaymentSummary,
    OrderResponse,
    OrderReturnSummary,
    OrderStatusUpdateRequest,
)
from app.modules.orders.service import (
    add_order_note,
    cancel_order_admin,
    confirm_order_admin,
    create_order_from_checkout,
    get_admin_order,
    get_order_by_number,
    list_order_notes,
    list_orders,
    reconcile_order_cod,
    update_order_status,
)
from app.modules.rbac.dependencies import require_permission

public_orders_router = APIRouter(prefix="/orders", tags=["Storefront: Orders & Checkout"])
customer_orders_router = APIRouter(prefix="/customer/orders", tags=["Customer: Account Orders"])
admin_orders_router = APIRouter(prefix="/admin/orders", tags=["Admin: Order Operations"])


# ===========================================================================
# Storefront Checkout
# ===========================================================================

@public_orders_router.post(
    "/checkout",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Process Storefront Checkout & Order Creation",
)
async def checkout_endpoint(
    req: CheckoutRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_anonymous_cart_token: Optional[str] = Header(None, alias="X-Anonymous-Cart-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Execute order creation from current shopping cart.
    Validates cart items, verifies destination address, calculates authoritative shipping quote,
    safely reserves stock, creates immutable order snapshots, and prevents duplicate submissions.
    """
    # Accept idempotency key from HTTP header or request body
    if idempotency_key and not req.idempotency_key:
        req.idempotency_key = idempotency_key

    return await create_order_from_checkout(
        db,
        req=req,
        current_user=current_user,
        anonymous_token=x_anonymous_cart_token,
    )


@public_orders_router.get(
    "/{order_number}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Order Confirmation by Reference Number",
)
async def get_order_endpoint(
    order_number: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Retrieve full order details and item snapshots by order reference code."""
    return await get_order_by_number(db, order_number=order_number, current_user=current_user)


# ===========================================================================
# Customer Account Order History
# ===========================================================================

@customer_orders_router.get(
    "",
    response_model=OrderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Customer Order History",
)
async def list_customer_orders_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """Retrieve purchase history for the authenticated customer account."""
    offset = (page - 1) * page_size
    orders, total = await list_orders(
        db,
        current_user=current_user,
        limit=page_size,
        offset=offset,
    )
    return OrderListResponse(
        orders=orders,
        total=total,
        page=page,
        page_size=page_size,
    )


# ===========================================================================
# Administrative Order Management
# ===========================================================================

@admin_orders_router.get(
    "",
    response_model=OrderListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Search and List Orders with Filters",
)
async def admin_list_orders_endpoint(
    status_filter: Optional[str] = Query(None, alias="status"),
    payment_status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    fulfillment_status: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None, description="Search by order number, customer name, email, or phone"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """Administrative order work queue with faceted filtering and pagination."""
    offset = (page - 1) * page_size
    orders, total = await list_orders(
        db,
        current_user=None,
        status_filter=status_filter,
        payment_status=payment_status,
        payment_method=payment_method,
        fulfillment_status=fulfillment_status,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=page_size,
        offset=offset,
    )
    return OrderListResponse(
        orders=orders,
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_orders_router.get(
    "/{order_ref}",
    response_model=AdminOrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Comprehensive Order Detail Dossier",
)
async def admin_get_order_endpoint(
    order_ref: str,
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> AdminOrderDetailResponse:
    """Retrieve full order details, payment ledger, shipment tracking, returns, and operator timeline notes."""
    return await get_admin_order(db, order_ref=order_ref)


@admin_orders_router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Order Lifecycle Status",
)
async def admin_update_order_status_endpoint(
    order_id: int,
    req: OrderStatusUpdateRequest,
    current_user: User = Depends(require_permission("orders.update")),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order processing state machine. Automatically releases stock reservations upon cancellation."""
    return await update_order_status(
        db,
        order_id=order_id,
        to_status=req.to_status,
        note=req.note,
        actor_user=current_user,
    )


@admin_orders_router.post(
    "/{order_id}/confirm",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Confirm Pending Order",
)
async def admin_confirm_order_endpoint(
    order_id: int,
    req: Optional[OrderConfirmationRequest] = None,
    current_user: User = Depends(require_permission("orders.update")),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Transition order from pending_confirmation to confirmed state."""
    note = req.note if req else None
    return await confirm_order_admin(db, order_id=order_id, note=note, actor_user=current_user)


@admin_orders_router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Cancel Order with Restock",
)
async def admin_cancel_order_endpoint(
    order_id: int,
    req: OrderCancellationRequest,
    current_user: User = Depends(require_permission("orders.cancel")),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Cancel order within policy, release reserved stock, and cancel unpaid COD payments."""
    return await cancel_order_admin(db, order_id=order_id, reason=req.reason, actor_user=current_user)


@admin_orders_router.post(
    "/{order_id}/notes",
    response_model=AdminOrderStatusHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Add Internal Operational Note",
)
async def admin_add_order_note_endpoint(
    order_id: int,
    req: OrderNoteCreateRequest,
    current_user: User = Depends(require_permission("orders.update")),
    db: AsyncSession = Depends(get_db),
) -> AdminOrderStatusHistoryResponse:
    """Add staff-only operational note to order timeline (hidden from customers)."""
    return await add_order_note(db, order_id=order_id, note=req.note, actor_user=current_user)


@admin_orders_router.get(
    "/{order_id}/notes",
    response_model=List[AdminOrderStatusHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List Operational Timeline Notes",
)
async def admin_list_order_notes_endpoint(
    order_id: int,
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> List[AdminOrderStatusHistoryResponse]:
    """Retrieve full chronological operational notes and transition history."""
    return await list_order_notes(db, order_id=order_id)


@admin_orders_router.post(
    "/{order_id}/reconcile-cod",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Reconcile COD Remittance",
)
async def admin_reconcile_cod_endpoint(
    order_id: int,
    req: OrderCODReconciliationRequest,
    current_user: User = Depends(require_permission("payments.reconcile")),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Reconcile courier remittance for Cash on Delivery, updating ledger and payment status."""
    return await reconcile_order_cod(db, order_id=order_id, req=req, actor_user=current_user)


@admin_orders_router.get(
    "/{order_id}/payments",
    response_model=List[OrderPaymentSummary],
    status_code=status.HTTP_200_OK,
    summary="Admin: Inspect Order Payment Transactions",
)
async def admin_get_order_payments_endpoint(
    order_id: int,
    current_user: User = Depends(require_permission("payments.read")),
    db: AsyncSession = Depends(get_db),
) -> List[OrderPaymentSummary]:
    """Retrieve payment ledger entries associated with this order."""
    from app.modules.payments.models import Payment

    stmt = select(Payment).where(Payment.order_id == order_id).order_by(Payment.id.asc())
    res = await db.execute(stmt)
    payments = res.scalars().all()
    return [OrderPaymentSummary.model_validate(p) for p in payments]


@admin_orders_router.get(
    "/{order_id}/returns",
    response_model=List[OrderReturnSummary],
    status_code=status.HTTP_200_OK,
    summary="Admin: Inspect Order Return Requests",
)
async def admin_get_order_returns_endpoint(
    order_id: int,
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> List[OrderReturnSummary]:
    """Retrieve return and exchange requests associated with this order."""
    from app.modules.returns.models import ReturnRequest

    stmt = select(ReturnRequest).where(ReturnRequest.order_id == order_id).order_by(ReturnRequest.id.asc())
    res = await db.execute(stmt)
    returns = res.scalars().all()
    return [OrderReturnSummary.model_validate(r) for r in returns]
