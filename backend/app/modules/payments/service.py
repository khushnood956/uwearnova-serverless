"""
Payments and Cash on Delivery (COD) Service Layer (Module M13)
Implements COD payment tracking, order confirmation, courier dispatch, cash collection,
remittance reconciliation, transaction audit ledgers, and safe inventory release upon cancellation.
"""

import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.orders.models import Order, OrderStatusHistory
from app.modules.orders.service import update_order_status
from app.modules.payments.models import Payment, PaymentEvent, PaymentTransaction, Refund
from app.modules.payments.provider import get_payment_provider
from app.modules.payments.schemas import (
    CODCancellationRequest,
    CODCollectionRecordRequest,
    CODConfirmationRequest,
    CODDispatchRecordRequest,
    CODReconciliationRequest,
    PaymentEventResponse,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentResponse,
    PaymentTransactionResponse,
    RefundCreateRequest,
    RefundResponse,
)


def build_payment_response(payment: Payment, order_number: Optional[str] = None) -> PaymentResponse:
    """Transform Payment entity into strongly typed PaymentResponse."""
    resolved_order_num = order_number
    if not resolved_order_num and "order" in payment.__dict__:
        order_obj = payment.__dict__["order"]
        if order_obj:
            resolved_order_num = getattr(order_obj, "order_number", None)

    txns = []
    if "transactions" in payment.__dict__:
        txn_list = payment.__dict__["transactions"]
        txns = [
            PaymentTransactionResponse(
                id=t.id,
                action=t.action,
                amount=t.amount,
                currency_code=t.currency_code,
                collected_by=t.collected_by,
                reference=t.reference,
                notes=t.notes,
                recorded_by_user_id=t.recorded_by_user_id,
                created_at=t.created_at,
            )
            for t in txn_list
        ]

    return PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        order_number=resolved_order_num,
        payment_method=payment.payment_method,
        provider_code=payment.provider_code,
        provider_reference=payment.provider_reference,
        status=payment.status,
        currency_code=payment.currency_code,
        amount=payment.amount,
        amount_collected=payment.amount_collected,
        amount_outstanding=payment.amount_outstanding,
        initiated_at=payment.initiated_at,
        confirmed_at=payment.confirmed_at,
        dispatched_at=payment.dispatched_at,
        collected_at=payment.collected_at,
        reconciled_at=payment.reconciled_at,
        reconciled_by_user_id=payment.reconciled_by_user_id,
        settlement_reference=payment.settlement_reference,
        notes=payment.notes,
        transactions=txns,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


async def create_initial_payment_for_order(
    db: AsyncSession,
    order: Order,
    actor_user: Optional[User] = None,
) -> Payment:
    """
    Initialize a Payment record when an order is created.
    Guarantees that COD orders start with payment_status='unpaid' and payment.status='pending'.
    """
    # Check if payment already exists
    existing_stmt = select(Payment).where(Payment.order_id == order.id)
    res = await db.execute(existing_stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    provider_code = "cod" if order.payment_method == "cod" else order.payment_method

    payment = Payment(
        order_id=order.id,
        payment_method=order.payment_method,
        provider_code=provider_code,
        status="pending",
        currency_code=order.currency_code,
        amount=order.grand_total,
        amount_collected=Decimal("0.00"),
        amount_outstanding=order.grand_total,
        initiated_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    await db.flush()

    # Initial transaction event
    init_txn = PaymentTransaction(
        payment_id=payment.id,
        order_id=order.id,
        action="initiated",
        amount=Decimal("0.00"),
        currency_code=order.currency_code,
        notes=f"Order placed with payment method '{order.payment_method.upper()}'. Status: UNPAID.",
        recorded_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(init_txn)
    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.initiated",
        entity_type="payment",
        entity_id=str(payment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "order_id": order.id,
            "order_number": order.order_number,
            "payment_method": order.payment_method,
            "amount": str(order.grand_total),
            "status": "pending",
        },
    )

    return payment


async def get_payment_by_id(db: AsyncSession, payment_id: int) -> PaymentResponse:
    """Retrieve full payment detail by ID."""
    stmt = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
        .where(Payment.id == payment_id)
    )
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )

    return build_payment_response(payment)


async def get_payment_by_order_id(db: AsyncSession, order_id: int) -> PaymentResponse:
    """Retrieve payment associated with a given order ID."""
    stmt = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
        .where(Payment.order_id == order_id)
    )
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record for order not found",
        )

    return build_payment_response(payment)


async def list_payments(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    payment_method: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[PaymentResponse], int]:
    """Administrative payment work queue with filtering and pagination."""
    query = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
    )

    if status_filter:
        query = query.where(Payment.status == status_filter)

    if payment_method:
        query = query.where(Payment.payment_method == payment_method)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.join(Payment.order).where(
            or_(
                Order.order_number.ilike(search_term),
                Payment.provider_reference.ilike(search_term),
                Payment.settlement_reference.ilike(search_term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    query = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    payments = res.scalars().all()

    return [build_payment_response(p) for p in payments], total


async def confirm_cod_payment(
    db: AsyncSession,
    payment_id: int,
    req: CODConfirmationRequest,
    actor_user: Optional[User] = None,
) -> PaymentResponse:
    """
    Verify and confirm a Cash on Delivery order.
    Transitions Payment.status from 'pending' to 'confirmed'.
    Synchronizes Order.status to 'confirmed' if currently 'pending_confirmation'.
    IMPORTANT: Order.payment_status remains strictly 'unpaid' until cash is collected!
    """
    stmt = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
        .where(Payment.id == payment_id)
    )
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )

    if payment.payment_method != "cod":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation is only applicable to Cash on Delivery payments",
        )

    if payment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm COD payment with status '{payment.status}'",
        )

    now = datetime.now(timezone.utc)
    payment.status = "confirmed"
    payment.confirmed_at = now
    if req.notes:
        payment.notes = f"{payment.notes or ''}\nConfirmed: {req.notes}".strip()

    # Record confirmation event
    txn = PaymentTransaction(
        payment_id=payment.id,
        order_id=payment.order_id,
        action="confirmed",
        amount=Decimal("0.00"),
        currency_code=payment.currency_code,
        notes=req.notes or "COD verification confirmed",
        recorded_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(txn)

    # Sync order status to 'confirmed' if currently pending confirmation
    if payment.order and payment.order.status == "pending_confirmation":
        payment.order.status = "confirmed"
        order_history = OrderStatusHistory(
            order_id=payment.order.id,
            from_status="pending_confirmation",
            to_status="confirmed",
            note="COD order verified and confirmed",
            changed_by_user_id=actor_user.id if actor_user else None,
        )
        db.add(order_history)

    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.cod_confirmed",
        entity_type="payment",
        entity_id=str(payment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "order_id": payment.order_id,
            "order_number": payment.order.order_number if payment.order else None,
            "notes": req.notes,
        },
    )

    return build_payment_response(payment)


async def record_cod_dispatch(
    db: AsyncSession,
    payment_id: int,
    req: CODDispatchRecordRequest,
    actor_user: Optional[User] = None,
) -> PaymentResponse:
    """
    Record courier dispatch and tracking number for a COD order.
    Transitions Payment.status to 'dispatched'.
    Advances Order.status to 'shipped' if currently in fulfillment pipeline.
    Payment status remains strictly 'unpaid'.
    """
    stmt = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
        .where(Payment.id == payment_id)
    )
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )

    if payment.payment_method != "cod":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dispatch recording is only applicable to Cash on Delivery payments",
        )

    if payment.status not in ("pending", "confirmed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dispatch COD order with payment status '{payment.status}'",
        )

    now = datetime.now(timezone.utc)
    payment.status = "dispatched"
    payment.dispatched_at = now
    payment.provider_reference = req.tracking_number

    txn = PaymentTransaction(
        payment_id=payment.id,
        order_id=payment.order_id,
        action="dispatched",
        amount=Decimal("0.00"),
        currency_code=payment.currency_code,
        collected_by=req.courier_code,
        reference=req.tracking_number,
        notes=req.notes or f"Dispatched via {req.courier_code.upper()} AWB# {req.tracking_number}",
        recorded_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(txn)

    # Sync order status to shipped if in processing/packed
    if payment.order and payment.order.status in ("pending_confirmation", "confirmed", "processing", "packed"):
        old_status = payment.order.status
        payment.order.status = "shipped"
        order_history = OrderStatusHistory(
            order_id=payment.order.id,
            from_status=old_status,
            to_status="shipped",
            note=f"Dispatched with {req.courier_code.upper()} AWB# {req.tracking_number}",
            changed_by_user_id=actor_user.id if actor_user else None,
        )
        db.add(order_history)

    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.cod_dispatched",
        entity_type="payment",
        entity_id=str(payment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "order_id": payment.order_id,
            "courier_code": req.courier_code,
            "tracking_number": req.tracking_number,
        },
    )

    return build_payment_response(payment)


async def record_cod_collection(
    db: AsyncSession,
    payment_id: int,
    req: CODCollectionRecordRequest,
    actor_user: Optional[User] = None,
) -> PaymentResponse:
    """
    Record verified cash collection by courier or delivery rider.
    Computes updated amount_collected and outstanding balance.
    If full amount collected: marks payment 'collected' and order payment_status 'paid'.
    If partial amount collected: marks payment 'partially_collected' and order payment_status 'partially_paid'.
    Advances Order.status to 'delivered' if currently 'shipped'.
    """
    stmt = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
        .where(Payment.id == payment_id)
    )
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )

    if payment.status in ("reconciled", "cancelled", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot record collection for payment in terminal state '{payment.status}'",
        )

    if req.amount_collected > payment.amount_outstanding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Collection amount (PKR {req.amount_collected}) cannot exceed outstanding balance (PKR {payment.amount_outstanding})",
        )

    now = datetime.now(timezone.utc)
    payment.amount_collected += req.amount_collected
    payment.amount_outstanding = max(Decimal("0.00"), payment.amount - payment.amount_collected)
    payment.collected_at = now

    is_full = payment.amount_outstanding == Decimal("0.00")
    payment.status = "collected" if is_full else "partially_collected"

    # Synchronize order payment status
    if payment.order:
        payment.order.payment_status = "paid" if is_full else "partially_paid"
        # If currently shipped, transition to delivered
        if payment.order.status == "shipped":
            payment.order.status = "delivered"
            payment.order.fulfillment_status = "fulfilled"
            order_history = OrderStatusHistory(
                order_id=payment.order.id,
                from_status="shipped",
                to_status="delivered",
                note=f"Delivered and cash collected (PKR {req.amount_collected})",
                changed_by_user_id=actor_user.id if actor_user else None,
            )
            db.add(order_history)

    # Record transaction event
    txn = PaymentTransaction(
        payment_id=payment.id,
        order_id=payment.order_id,
        action="collected" if is_full else "partially_collected",
        amount=req.amount_collected,
        currency_code=payment.currency_code,
        collected_by=req.collected_by,
        reference=req.reference,
        notes=req.notes or f"Cash collection of PKR {req.amount_collected}",
        recorded_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(txn)
    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.cod_collected",
        entity_type="payment",
        entity_id=str(payment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "order_id": payment.order_id,
            "amount_collected": str(req.amount_collected),
            "amount_outstanding": str(payment.amount_outstanding),
            "payment_status": payment.status,
            "collected_by": req.collected_by,
        },
    )

    return build_payment_response(payment)


async def reconcile_cod_payment(
    db: AsyncSession,
    payment_id: int,
    req: CODReconciliationRequest,
    actor_user: Optional[User] = None,
) -> PaymentResponse:
    """
    Reconcile courier remittance against collected COD payments.
    Requires permission: 'payments.reconcile'.
    Only payments with status 'collected' or 'partially_collected' can be reconciled.
    """
    stmt = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
        .where(Payment.id == payment_id)
    )
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )

    if payment.status not in ("collected", "partially_collected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reconcile payment with status '{payment.status}'. Payment must be collected before reconciliation.",
        )

    now = datetime.now(timezone.utc)
    payment.status = "reconciled"
    payment.reconciled_at = now
    payment.reconciled_by_user_id = actor_user.id if actor_user else None
    payment.settlement_reference = req.settlement_reference
    if req.notes:
        payment.notes = f"{payment.notes or ''}\nReconciled: {req.notes}".strip()

    txn = PaymentTransaction(
        payment_id=payment.id,
        order_id=payment.order_id,
        action="reconciled",
        amount=payment.amount_collected,
        currency_code=payment.currency_code,
        reference=req.settlement_reference,
        notes=req.notes or f"Reconciled courier settlement: {req.settlement_reference}",
        recorded_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(txn)
    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.cod_reconciled",
        entity_type="payment",
        entity_id=str(payment.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "order_id": payment.order_id,
            "settlement_reference": req.settlement_reference,
            "amount_settled": str(payment.amount_collected),
        },
    )

    return build_payment_response(payment)


async def cancel_cod_payment(
    db: AsyncSession,
    payment_id: int,
    req: CODCancellationRequest,
    actor_user: Optional[User] = None,
) -> PaymentResponse:
    """
    Cancel an uncollected Cash on Delivery payment.
    Automatically transitions order to 'cancelled' and releases reserved stock via M09.
    Cannot cancel an order that was already collected or reconciled.
    """
    stmt = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
        .where(Payment.id == payment_id)
    )
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )

    if payment.status in ("collected", "reconciled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel payment that has already been {payment.status}. Process a refund or return instead.",
        )

    if payment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment is already cancelled",
        )

    payment.status = "cancelled"
    txn = PaymentTransaction(
        payment_id=payment.id,
        order_id=payment.order_id,
        action="cancelled",
        amount=Decimal("0.00"),
        currency_code=payment.currency_code,
        notes=f"COD Cancelled: {req.reason}. {req.notes or ''}".strip(),
        recorded_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(txn)
    order_id = payment.order_id

    # Cancel order and release stock if not already cancelled
    if payment.order and payment.order.status != "cancelled":
        await update_order_status(
            db,
            order_id=order_id,
            to_status="cancelled",
            note=f"Cancelled via COD management: {req.reason}",
            actor_user=actor_user,
        )

    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.cod_cancelled",
        entity_type="payment",
        entity_id=str(payment_id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "order_id": order_id,
            "reason": req.reason,
            "notes": req.notes,
        },
    )

    # Re-query payment with relationships eagerly populated
    stmt = (
        select(Payment)
        .options(
            selectinload(Payment.order),
            selectinload(Payment.transactions),
        )
        .where(Payment.id == payment_id)
        .execution_options(populate_existing=True)
    )
    res = await db.execute(stmt)
    refreshed_payment = res.scalar_one()
    return build_payment_response(refreshed_payment)


# ===========================================================================
# Online Gateway Integration & Webhook Lifecycle (Module M14)
# ===========================================================================

def generate_refund_number() -> str:
    """Generate unique refund reference code (e.g. RFD-20261111-849201)."""
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    random_part = secrets.randbelow(900000) + 100000
    return f"RFD-{date_part}-{random_part}"


def build_refund_response(refund: Refund) -> RefundResponse:
    """Transform Refund entity into strongly typed RefundResponse."""
    return RefundResponse(
        id=refund.id,
        order_id=refund.order_id,
        payment_id=refund.payment_id,
        refund_number=refund.refund_number,
        amount=refund.amount,
        currency_code=refund.currency_code,
        reason=refund.reason,
        status=refund.status,
        provider_reference=refund.provider_reference,
        notes=refund.notes,
        created_at=refund.created_at,
        completed_at=refund.completed_at,
    )


def build_payment_event_response(event: PaymentEvent) -> PaymentEventResponse:
    """Transform PaymentEvent entity into strongly typed PaymentEventResponse."""
    return PaymentEventResponse(
        id=event.id,
        payment_id=event.payment_id,
        provider_code=event.provider_code,
        provider_event_id=event.provider_event_id,
        event_type=event.event_type,
        signature_verified=event.signature_verified,
        processing_status=event.processing_status,
        processed_at=event.processed_at,
        error_message=event.error_message,
        created_at=event.created_at,
    )


async def initiate_online_payment(
    db: AsyncSession,
    req: PaymentInitiateRequest,
    current_user: Optional[User] = None,
) -> PaymentInitiateResponse:
    """
    Initiate an online payment session through the configured provider adapter.
    Enforces that unconfigured providers fail cleanly without simulating fake success.
    """
    order_stmt = select(Order).where(Order.id == req.order_id)
    res = await db.execute(order_stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.payment_status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already paid",
        )

    # Ownership check if authenticated customer
    if current_user and current_user.user_type == "customer":
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

    # Retrieve or initialize payment record
    payment_stmt = select(Payment).where(Payment.order_id == order.id)
    p_res = await db.execute(payment_stmt)
    payment = p_res.scalar_one_or_none()

    if not payment:
        payment = await create_initial_payment_for_order(db, order, actor_user=current_user)

    # Resolve provider adapter (raises HTTPException if unconfigured)
    provider = get_payment_provider(req.provider_code or payment.provider_code)
    init_result = await provider.initiate_payment(
        order=order,
        payment=payment,
        return_url=req.return_url,
        cancel_url=req.cancel_url,
    )

    # Update payment entity with provider metadata
    payment.provider_code = init_result.provider_code
    payment.provider_reference = init_result.provider_reference
    payment.payment_method = "card" if init_result.provider_code != "cod" else "cod"

    txn = PaymentTransaction(
        payment_id=payment.id,
        order_id=order.id,
        action="checkout_initiated",
        amount=Decimal("0.00"),
        currency_code=payment.currency_code,
        reference=init_result.provider_reference,
        notes=f"Checkout session initiated via {init_result.provider_code.upper()}",
        recorded_by_user_id=current_user.id if current_user else None,
    )
    db.add(txn)
    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.online_initiated",
        entity_type="payment",
        entity_id=str(payment.id),
        user_id=current_user.id if current_user else None,
        actor_email=current_user.email if current_user else None,
        details={
            "order_number": order.order_number,
            "provider_code": init_result.provider_code,
            "provider_reference": init_result.provider_reference,
        },
    )

    return PaymentInitiateResponse(
        payment_id=payment.id,
        order_id=order.id,
        order_number=order.order_number,
        provider_code=init_result.provider_code,
        provider_reference=init_result.provider_reference,
        redirect_url=init_result.redirect_url,
        client_token=init_result.client_token,
        status=init_result.status,
        amount=payment.amount,
        currency_code=payment.currency_code,
    )


async def process_webhook_callback(
    db: AsyncSession,
    provider_code: str,
    headers: Dict[str, str],
    raw_body: bytes,
) -> dict:
    """
    Process incoming provider webhook notifications with strict idempotency and signature validation.
    Prevents duplicate payment application, verifies HMAC signatures, and logs every event in the ledger.
    """
    provider = get_payment_provider(provider_code)
    is_valid_sig = provider.verify_webhook_signature(headers, raw_body)
    event_payload = provider.parse_webhook_event(headers, raw_body)

    # 1. Idempotency Check: Check if this event was already processed
    if event_payload.provider_event_id:
        existing_stmt = select(PaymentEvent).where(
            PaymentEvent.provider_code == provider_code,
            PaymentEvent.provider_event_id == event_payload.provider_event_id,
        )
        ex_res = await db.execute(existing_stmt)
        existing_event = ex_res.scalar_one_or_none()

        if existing_event and existing_event.processing_status == "processed":
            return {
                "status": "already_processed",
                "event_id": event_payload.provider_event_id,
                "message": "Webhook event was previously processed idempotently",
            }

    # Record incoming event record
    raw_text = raw_body.decode("utf-8", errors="replace")
    payment_event = PaymentEvent(
        provider_code=provider_code,
        provider_event_id=event_payload.provider_event_id,
        event_type=event_payload.event_type,
        signature_verified=is_valid_sig,
        payload=raw_text,
        processing_status="received",
    )
    db.add(payment_event)
    await db.flush()

    # 2. Signature Validation Enforcement
    if not is_valid_sig:
        payment_event.processing_status = "failed"
        payment_event.error_message = "Cryptographic webhook signature verification failed"
        await db.flush()

        await log_audit_event(
            db=db,
            action="payment.webhook_signature_failed",
            entity_type="payment_event",
            entity_id=str(payment_event.id),
            details={"provider_code": provider_code, "event_type": event_payload.event_type},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_WEBHOOK_SIGNATURE: Webhook signature verification failed",
        )

    # 3. Resolve Associated Payment Entity
    payment: Optional[Payment] = None
    if event_payload.provider_reference:
        p_ref = event_payload.provider_reference
        is_num = p_ref.isdigit()
        p_stmt = (
            select(Payment)
            .options(selectinload(Payment.order))
            .where(
                (Payment.provider_reference == p_ref)
                | (Payment.id == (int(p_ref) if is_num else -1))
            )
        )
        p_res = await db.execute(p_stmt)
        payment = p_res.scalar_one_or_none()

    if not payment and event_payload.order_reference:
        ord_stmt = select(Order).where(Order.order_number == event_payload.order_reference)
        ord_res = await db.execute(ord_stmt)
        matched_order = ord_res.scalar_one_or_none()
        if matched_order:
            p_stmt = (
                select(Payment)
                .options(selectinload(Payment.order))
                .where(Payment.order_id == matched_order.id)
            )
            p_res = await db.execute(p_stmt)
            payment = p_res.scalar_one_or_none()

    if payment:
        payment_event.payment_id = payment.id

        # 4. State Machine Transition & Duplicate Payment Prevention
        if event_payload.event_type in ("payment.succeeded", "charge.succeeded") or event_payload.status == "paid":
            if payment.status in ("paid", "collected", "reconciled"):
                # Duplicate success event for already settled payment
                payment_event.processing_status = "duplicate"
                payment_event.processed_at = datetime.now(timezone.utc)
                await db.flush()
                return {
                    "status": "duplicate_payment",
                    "event_id": event_payload.provider_event_id,
                    "message": "Payment is already marked as paid. Duplicate avoided.",
                }

            # Mark payment and order as paid
            payment.status = "paid"
            payment.amount_collected = event_payload.amount or payment.amount
            payment.amount_outstanding = max(Decimal("0.00"), payment.amount - payment.amount_collected)
            payment.collected_at = datetime.now(timezone.utc)
            if payment.order:
                payment.order.payment_status = "paid"

            txn = PaymentTransaction(
                payment_id=payment.id,
                order_id=payment.order_id,
                action="paid",
                amount=payment.amount_collected,
                currency_code=payment.currency_code,
                reference=event_payload.provider_reference,
                notes=f"Online payment verified via {provider_code.upper()} webhook",
            )
            db.add(txn)

            await log_audit_event(
                db=db,
                action="payment.online_succeeded",
                entity_type="payment",
                entity_id=str(payment.id),
                details={
                    "order_id": payment.order_id,
                    "provider_code": provider_code,
                    "amount": str(payment.amount_collected),
                },
            )

        elif event_payload.event_type in ("payment.failed", "charge.failed") or event_payload.status == "failed":
            if payment.status != "paid":
                payment.status = "failed"
                if payment.order:
                    payment.order.payment_status = "failed"

                txn = PaymentTransaction(
                    payment_id=payment.id,
                    order_id=payment.order_id,
                    action="failed",
                    amount=Decimal("0.00"),
                    currency_code=payment.currency_code,
                    reference=event_payload.provider_reference,
                    notes=f"Online payment failed via {provider_code.upper()}",
                )
                db.add(txn)

                await log_audit_event(
                    db=db,
                    action="payment.online_failed",
                    entity_type="payment",
                    entity_id=str(payment.id),
                    details={"order_id": payment.order_id, "provider_code": provider_code},
                )

    payment_event.processing_status = "processed"
    payment_event.processed_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "status": "success",
        "event_id": event_payload.provider_event_id,
        "processing_status": "processed",
    }


async def create_payment_refund(
    db: AsyncSession,
    payment_id: int,
    req: RefundCreateRequest,
    actor_user: Optional[User] = None,
) -> RefundResponse:
    """
    Process refund for an order payment.
    Requires permission: 'refunds.create'.
    Verifies that payment was paid or collected, and that refund does not exceed collected funds.
    """
    payment_stmt = (
        select(Payment)
        .options(selectinload(Payment.order))
        .where(Payment.id == payment_id)
    )
    p_res = await db.execute(payment_stmt)
    payment = p_res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    if payment.status not in ("paid", "collected", "reconciled", "partially_refunded"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot refund payment with status '{payment.status}'. Payment must be collected or paid before issuing a refund.",
        )

    if req.amount > payment.amount_collected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount (PKR {req.amount}) exceeds total collected amount (PKR {payment.amount_collected})",
        )

    refund_number = generate_refund_number()
    refund = Refund(
        order_id=payment.order_id,
        payment_id=payment.id,
        refund_number=refund_number,
        amount=req.amount,
        currency_code=payment.currency_code,
        reason=req.reason,
        status="pending",
        created_by_user_id=actor_user.id if actor_user else None,
        notes=req.notes,
    )
    db.add(refund)
    await db.flush()

    # Process through provider adapter
    provider = get_payment_provider(payment.provider_code)
    refund_res = await provider.process_refund(payment=payment, refund=refund, reason=req.reason)

    if refund_res.status == "completed":
        refund.status = "completed"
        refund.completed_at = datetime.now(timezone.utc)
        refund.provider_reference = refund_res.provider_reference

        payment.amount_collected -= req.amount
        payment.amount_outstanding += req.amount
        if payment.amount_collected == Decimal("0.00"):
            payment.status = "refunded"
            if payment.order:
                payment.order.payment_status = "refunded"
        else:
            payment.status = "partially_refunded"
            if payment.order:
                payment.order.payment_status = "partially_refunded"

        txn = PaymentTransaction(
            payment_id=payment.id,
            order_id=payment.order_id,
            action="refunded",
            amount=req.amount,
            currency_code=payment.currency_code,
            reference=refund.refund_number,
            notes=f"Refund processed: {req.reason}",
            recorded_by_user_id=actor_user.id if actor_user else None,
        )
        db.add(txn)
    else:
        refund.status = "failed"

    await db.flush()

    await log_audit_event(
        db=db,
        action="payment.refund_processed",
        entity_type="refund",
        entity_id=str(refund.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "refund_number": refund.refund_number,
            "order_id": payment.order_id,
            "amount": str(req.amount),
            "status": refund.status,
            "reason": req.reason,
        },
    )

    return build_refund_response(refund)


async def list_payment_refunds(db: AsyncSession, payment_id: int) -> List[RefundResponse]:
    """List all refunds associated with a payment."""
    stmt = (
        select(Refund)
        .where(Refund.payment_id == payment_id)
        .order_by(Refund.created_at.desc())
    )
    res = await db.execute(stmt)
    refunds = res.scalars().all()
    return [build_refund_response(r) for r in refunds]


async def list_payment_events(
    db: AsyncSession,
    provider_code: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[PaymentEventResponse], int]:
    """Administrative inspection of incoming webhook callbacks."""
    query = select(PaymentEvent)
    if provider_code:
        query = query.where(PaymentEvent.provider_code == provider_code)

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    query = query.order_by(PaymentEvent.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    events = res.scalars().all()

    return [build_payment_event_response(e) for e in events], total

