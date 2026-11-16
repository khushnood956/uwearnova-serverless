"""
Payment and Cash on Delivery (COD) API Endpoints (Module M13)
Customer payment status lookup, administrative COD confirmation, dispatch tracking,
cash collection recording, and courier remittance reconciliation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.models import User
from app.modules.orders.models import Order
from app.modules.payments.schemas import (
    CODCancellationRequest,
    CODCollectionRecordRequest,
    CODConfirmationRequest,
    CODDispatchRecordRequest,
    CODReconciliationRequest,
    PaymentEventListResponse,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentListResponse,
    PaymentResponse,
    RefundCreateRequest,
    RefundResponse,
)
from app.modules.payments.service import (
    cancel_cod_payment,
    confirm_cod_payment,
    create_payment_refund,
    get_payment_by_id,
    get_payment_by_order_id,
    initiate_online_payment,
    list_payment_events,
    list_payment_refunds,
    list_payments,
    process_webhook_callback,
    reconcile_cod_payment,
    record_cod_collection,
    record_cod_dispatch,
)
from app.modules.rbac.dependencies import require_permission

public_payments_router = APIRouter(prefix="/payments", tags=["Storefront: Payments & Webhooks"])
customer_payments_router = APIRouter(prefix="/customer/payments", tags=["Customer: Order Payments"])
admin_payments_router = APIRouter(prefix="/admin/payments", tags=["Admin: Payments & COD Reconciliation"])


# ===========================================================================
# Storefront Public Webhooks & Callbacks (Module M14)
# ===========================================================================

@public_payments_router.post(
    "/webhooks/{provider_code}",
    status_code=status.HTTP_200_OK,
    summary="Process Provider Webhook Callback",
)
async def process_gateway_webhook(
    provider_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Receive and process asynchronous provider callback notifications.
    Validates HMAC cryptographic signatures, prevents duplicate payments,
    and executes idempotent processing.
    """
    raw_body = await request.body()
    headers_dict = dict(request.headers)
    return await process_webhook_callback(
        db=db,
        provider_code=provider_code,
        headers=headers_dict,
        raw_body=raw_body,
    )


# ===========================================================================
# Customer Account Payment Endpoints
# ===========================================================================

@customer_payments_router.get(
    "/order/{order_number}",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Order Payment Status for Customer",
)
async def get_customer_order_payment(
    order_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Retrieve payment and collection status for an authenticated customer's order."""
    order_stmt = select(Order).where(Order.order_number == order_number)
    res = await db.execute(order_stmt)
    order = res.scalar_one_or_none()

    if not order or order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return await get_payment_by_order_id(db, order_id=order.id)


@customer_payments_router.post(
    "/order/{order_number}/confirm-cod",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Customer Self-Confirmation of COD Order",
)
async def customer_confirm_cod(
    order_number: str,
    req: CODConfirmationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Customer confirms intent to accept and pay for Cash on Delivery parcel."""
    order_stmt = select(Order).where(Order.order_number == order_number)
    res = await db.execute(order_stmt)
    order = res.scalar_one_or_none()

    if not order or order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    payment_res = await get_payment_by_order_id(db, order_id=order.id)
    return await confirm_cod_payment(
        db,
        payment_id=payment_res.id,
        req=req,
        actor_user=current_user,
    )


@customer_payments_router.post(
    "/initiate",
    response_model=PaymentInitiateResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate Online Payment Checkout Session",
)
async def customer_initiate_payment(
    req: PaymentInitiateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentInitiateResponse:
    """Initialize an online payment gateway transaction session."""
    return await initiate_online_payment(
        db=db,
        req=req,
        current_user=current_user,
    )


# ===========================================================================
# Administrative Payment and COD Reconciliation Endpoints
# ===========================================================================

@admin_payments_router.get(
    "",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: List and Search Payments",
)
async def admin_list_payments(
    status_filter: Optional[str] = Query(None, alias="status"),
    payment_method: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by order number or references"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("payments.read")),
    db: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    """Administrative payment work queue with filtering and pagination."""
    offset = (page - 1) * page_size
    payments, total = await list_payments(
        db,
        status_filter=status_filter,
        payment_method=payment_method,
        search=search,
        limit=page_size,
        offset=offset,
    )
    return PaymentListResponse(
        payments=payments,
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_payments_router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Retrieve Payment Details with Transaction Ledger",
)
async def admin_get_payment(
    payment_id: int,
    current_user: User = Depends(require_permission("payments.read")),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Retrieve full payment details, outstanding balance, and transaction history."""
    return await get_payment_by_id(db, payment_id=payment_id)


@admin_payments_router.get(
    "/order/{order_id}",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Retrieve Payment by Order ID",
)
async def admin_get_payment_by_order(
    order_id: int,
    current_user: User = Depends(require_permission("payments.read")),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Retrieve payment details associated with an order ID."""
    return await get_payment_by_order_id(db, order_id=order_id)


@admin_payments_router.post(
    "/{payment_id}/confirm-cod",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Confirm COD Order Verification",
)
async def admin_confirm_cod(
    payment_id: int,
    req: CODConfirmationRequest,
    current_user: User = Depends(require_permission("orders.update")),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Verify and confirm a Cash on Delivery order after customer phone verification."""
    return await confirm_cod_payment(
        db,
        payment_id=payment_id,
        req=req,
        actor_user=current_user,
    )


@admin_payments_router.post(
    "/{payment_id}/dispatch",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Record Courier Dispatch for COD Order",
)
async def admin_dispatch_cod(
    payment_id: int,
    req: CODDispatchRecordRequest,
    current_user: User = Depends(require_permission("orders.update")),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Record courier dispatch, tracking reference, and handover for COD delivery."""
    return await record_cod_dispatch(
        db,
        payment_id=payment_id,
        req=req,
        actor_user=current_user,
    )


@admin_payments_router.post(
    "/{payment_id}/record-collection",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Record Cash Collection by Courier",
)
async def admin_record_cod_collection(
    payment_id: int,
    req: CODCollectionRecordRequest,
    current_user: User = Depends(require_permission("payments.reconcile")),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """
    Record verified cash collection by courier or delivery rider.
    Updates amount collected and remaining outstanding balance.
    When full amount is collected, marks order as paid.
    """
    return await record_cod_collection(
        db,
        payment_id=payment_id,
        req=req,
        actor_user=current_user,
    )


@admin_payments_router.post(
    "/{payment_id}/reconcile",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Reconcile Courier Remittance Voucher",
)
async def admin_reconcile_cod(
    payment_id: int,
    req: CODReconciliationRequest,
    current_user: User = Depends(require_permission("payments.reconcile")),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """
    Reconcile courier remittance settlement against collected COD payments.
    Requires permission: 'payments.reconcile'.
    """
    return await reconcile_cod_payment(
        db,
        payment_id=payment_id,
        req=req,
        actor_user=current_user,
    )


@admin_payments_router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Cancel COD Payment and Release Inventory",
)
async def admin_cancel_cod(
    payment_id: int,
    req: CODCancellationRequest,
    current_user: User = Depends(require_permission("orders.cancel")),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Cancel uncollected COD payment, update order to cancelled, and safely release reserved stock."""
    return await cancel_cod_payment(
        db,
        payment_id=payment_id,
        req=req,
        actor_user=current_user,
    )


# ===========================================================================
# Refunds & Audit Event Inspection (Module M14)
# ===========================================================================

@admin_payments_router.post(
    "/{payment_id}/refund",
    response_model=RefundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Process Payment Refund",
)
async def admin_process_refund(
    payment_id: int,
    req: RefundCreateRequest,
    current_user: User = Depends(require_permission("refunds.create")),
    db: AsyncSession = Depends(get_db),
) -> RefundResponse:
    """Execute refund through provider adapter and record ledger update."""
    return await create_payment_refund(
        db=db,
        payment_id=payment_id,
        req=req,
        actor_user=current_user,
    )


@admin_payments_router.get(
    "/{payment_id}/refunds",
    response_model=List[RefundResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List Refunds for Payment",
)
async def admin_get_refunds(
    payment_id: int,
    current_user: User = Depends(require_permission("payments.read")),
    db: AsyncSession = Depends(get_db),
) -> List[RefundResponse]:
    """Retrieve all refund records issued for a payment."""
    return await list_payment_refunds(db, payment_id=payment_id)


@admin_payments_router.get(
    "/events/audit",
    response_model=PaymentEventListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Audit Log of Webhook Events",
)
async def admin_get_webhook_events(
    provider_code: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("payments.read")),
    db: AsyncSession = Depends(get_db),
) -> PaymentEventListResponse:
    """Inspect raw provider webhook callbacks and signature verification status."""
    offset = (page - 1) * page_size
    events, total = await list_payment_events(
        db,
        provider_code=provider_code,
        limit=page_size,
        offset=offset,
    )
    return PaymentEventListResponse(
        events=events,
        total=total,
        page=page,
        page_size=page_size,
    )
