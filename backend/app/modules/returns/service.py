"""
Returns, Exchanges, and Refunds Service Layer (Module M16)
Orchestrates return eligibility checking, review workflows, warehouse inspection checkpoints,
transaction-safe inventory restock, doorstep exchanges, and authorized online and COD payment refunds.
"""

from datetime import datetime, timedelta, timezone
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
from app.modules.catalog.models import ProductVariant
from app.modules.fulfillment.models import Shipment, ShipmentEvent, ShipmentItem
from app.modules.fulfillment.provider import get_courier_provider
from app.modules.fulfillment.service import generate_shipment_number
from app.modules.inventory.schemas import StockAdjustmentRequest
from app.modules.inventory.service import adjust_stock
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory
from app.modules.payments.models import Payment, PaymentTransaction, Refund
from app.modules.payments.schemas import RefundCreateRequest
from app.modules.payments.service import create_payment_refund, generate_refund_number
from app.modules.returns.models import ReturnItem, ReturnRequest
from app.modules.returns.schemas import (
    ReturnExchangeResolveRequest,
    ReturnInspectionRequest,
    ReturnItemResponse,
    ReturnReceiveRequest,
    ReturnRefundResolveRequest,
    ReturnRequestCreatePayload,
    ReturnRequestResponse,
    ReturnReviewRequest,
)

# UniNova Standard Return Policy Window (14 calendar days from delivery)
RETURN_POLICY_WINDOW_DAYS = 14


def generate_return_request_number() -> str:
    """Generate unique human-readable return reference: RET-YYYYMMDD-XXXXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_hex = secrets.token_hex(3).upper()
    return f"RET-{date_str}-{random_hex}"


def build_return_response(ret: ReturnRequest) -> ReturnRequestResponse:
    """Safely build ReturnRequestResponse from model instance without async lazy load errors."""
    items = [
        ReturnItemResponse(
            id=item.id,
            return_request_id=item.return_request_id,
            order_item_id=item.order_item_id,
            quantity=item.quantity,
            reason=item.reason,
            customer_comments=item.customer_comments,
            exchange_variant_id=item.exchange_variant_id,
            exchange_size=item.exchange_size,
            exchange_color=item.exchange_color,
            inspection_status=item.inspection_status,
            restock_condition=item.restock_condition,
            restock_action=item.restock_action,
            restocked_quantity=item.restocked_quantity,
            inspector_notes=item.inspector_notes,
            inspected_at=item.inspected_at,
            refund_amount=item.refund_amount,
            product_name_snapshot=item.product_name_snapshot,
            sku_snapshot=item.sku_snapshot,
            size_snapshot=item.size_snapshot,
            color_snapshot=item.color_snapshot,
            unit_price=item.unit_price,
        )
        for item in (ret.items if "items" in ret.__dict__ else [])
    ]

    return ReturnRequestResponse(
        id=ret.id,
        request_number=ret.request_number,
        order_id=ret.order_id,
        user_id=ret.user_id,
        request_type=ret.request_type,
        status=ret.status,
        resolution_type=ret.resolution_type,
        refund_payout_method=ret.refund_payout_method,
        customer_notes=ret.customer_notes,
        staff_notes=ret.staff_notes,
        rejection_reason=ret.rejection_reason,
        refund_id=ret.refund_id,
        replacement_order_id=ret.replacement_order_id,
        total_refund_amount=ret.total_refund_amount,
        reviewed_by_user_id=ret.reviewed_by_user_id,
        reviewed_at=ret.reviewed_at,
        received_at=ret.received_at,
        inspected_at=ret.inspected_at,
        resolved_at=ret.resolved_at,
        items=items,
        created_at=ret.created_at,
        updated_at=ret.updated_at,
    )


async def create_return_request(
    db: AsyncSession,
    order_number: str,
    payload: ReturnRequestCreatePayload,
    current_user: Optional[User] = None,
    customer_phone: Optional[str] = None,
) -> ReturnRequestResponse:
    """
    Customer or guest initiates an order return or exchange.
    Validates policy window, delivery status, non-zero quantities, and unreturned item bounds.
    """
    # 1. Fetch Order with Items and Existing Returns
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.shipments),
            selectinload(Order.returns).selectinload(ReturnRequest.items),
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

    # 2. Ownership / Phone Verification
    if current_user and current_user.user_type == "customer":
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
    elif not current_user:
        if not customer_phone or customer_phone.strip() != order.customer_phone.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number verification required for guest return requests",
            )

    # 3. Eligibility Checks
    # Must be in delivered state or return_requested
    if order.status not in ("delivered", "return_requested", "shipped"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"INELIGIBLE_FOR_RETURN: Order status '{order.status}' is not eligible for returns. "
                "Order must be delivered before initiating a return or exchange."
            ),
        )

    # Delivery Window Policy Check
    delivered_timestamp = order.placed_at
    if order.shipments:
        delivered_shipments = [s.delivered_at for s in order.shipments if s.delivered_at]
        if delivered_shipments:
            delivered_timestamp = max(delivered_shipments)

    days_since_delivery = (datetime.now(timezone.utc) - delivered_timestamp.replace(tzinfo=timezone.utc)).days
    if days_since_delivery > RETURN_POLICY_WINDOW_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"RETURN_WINDOW_EXPIRED: Returns must be requested within {RETURN_POLICY_WINDOW_DAYS} days of delivery. "
                f"This order was delivered {days_since_delivery} days ago."
            ),
        )

    # 4. Validate Requested Items & Unreturned Quantities
    order_items_map = {item.id: item for item in order.items}

    # Count units already involved in active or completed returns
    already_requested_counts: Dict[int, int] = {item.id: 0 for item in order.items}
    for existing_ret in order.returns:
        if existing_ret.status not in ("rejected", "cancelled"):
            for ret_item in existing_ret.items:
                already_requested_counts[ret_item.order_item_id] = (
                    already_requested_counts.get(ret_item.order_item_id, 0) + ret_item.quantity
                )

    new_return_items: List[ReturnItem] = []
    for it_req in payload.items:
        if it_req.order_item_id not in order_items_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Line item {it_req.order_item_id} does not belong to order {order.order_number}",
            )
        order_item = order_items_map[it_req.order_item_id]
        remaining = order_item.quantity - already_requested_counts.get(order_item.id, 0)
        if it_req.quantity > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Requested return quantity ({it_req.quantity}) exceeds remaining returnable "
                    f"units ({remaining}) for SKU {order_item.sku_snapshot}"
                ),
            )

        # Exchange Variant Validation
        exchange_variant: Optional[ProductVariant] = None
        if payload.request_type == "exchange" and it_req.exchange_variant_id:
            v_stmt = select(ProductVariant).where(ProductVariant.id == it_req.exchange_variant_id)
            v_res = await db.execute(v_stmt)
            exchange_variant = v_res.scalar_one_or_none()
            if not exchange_variant or not exchange_variant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Requested replacement variant ID {it_req.exchange_variant_id} is unavailable or inactive",
                )

        item_refund_est = order_item.unit_price * it_req.quantity
        new_item = ReturnItem(
            order_item_id=order_item.id,
            quantity=it_req.quantity,
            reason=it_req.reason,
            customer_comments=it_req.customer_comments,
            exchange_variant_id=exchange_variant.id if exchange_variant else None,
            exchange_size=exchange_variant.size if exchange_variant else None,
            exchange_color=exchange_variant.color_name if exchange_variant else None,
            inspection_status="pending",
            restocked_quantity=0,
            refund_amount=item_refund_est,
            product_name_snapshot=order_item.product_name_snapshot,
            sku_snapshot=order_item.sku_snapshot,
            size_snapshot=order_item.size_snapshot,
            color_snapshot=order_item.color_snapshot,
            unit_price=order_item.unit_price,
        )
        new_return_items.append(new_item)

    # 5. Create ReturnRequest Header
    request_number = generate_return_request_number()
    account_details_json = json.dumps(payload.payout_account_details) if payload.payout_account_details else None

    return_request = ReturnRequest(
        request_number=request_number,
        order_id=order.id,
        user_id=current_user.id if current_user else order.user_id,
        request_type=payload.request_type,
        status="requested",
        resolution_type=payload.resolution_type,
        refund_payout_method=payload.refund_payout_method,
        payout_account_details=account_details_json,
        customer_notes=payload.customer_notes,
        total_refund_amount=sum(i.refund_amount for i in new_return_items),
    )
    db.add(return_request)
    await db.flush()

    for item in new_return_items:
        item.return_request_id = return_request.id
        db.add(item)

    # Update Order status
    prev_order_status = order.status
    if order.status != "return_requested":
        order.status = "return_requested"

        history = OrderStatusHistory(
            order_id=order.id,
            from_status=prev_order_status,
            to_status=order.status,
            note=f"Return request {request_number} submitted ({payload.request_type.upper()})",
            changed_by_user_id=current_user.id if current_user else None,
        )
        db.add(history)

    await db.flush()

    # 6. Audit Logging
    await log_audit_event(
        db=db,
        action="return.requested",
        entity_type="return_request",
        entity_id=str(return_request.id),
        user_id=current_user.id if current_user else None,
        actor_email=current_user.email if current_user else order.customer_email,
        details={
            "request_number": request_number,
            "order_number": order.order_number,
            "request_type": payload.request_type,
            "resolution_type": payload.resolution_type,
            "items_count": len(new_return_items),
        },
    )

    return await get_return_request_by_id(db, return_request.id)


async def review_return_request(
    db: AsyncSession,
    return_id: int,
    req: ReturnReviewRequest,
    actor_user: User,
) -> ReturnRequestResponse:
    """
    Staff reviews and approves or rejects a return/exchange request.
    Requires permission: 'returns.review' or 'returns.resolve'.
    """
    stmt = (
        select(ReturnRequest)
        .options(
            selectinload(ReturnRequest.order).selectinload(Order.returns),
            selectinload(ReturnRequest.items),
        )
        .where(ReturnRequest.id == return_id)
    )
    res = await db.execute(stmt)
    ret = res.scalar_one_or_none()

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if ret.status not in ("requested", "under_review"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review return request with status '{ret.status}'",
        )

    decision = req.decision.lower().strip()
    if decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be either 'approved' or 'rejected'",
        )

    now = datetime.now(timezone.utc)
    ret.reviewed_by_user_id = actor_user.id
    ret.reviewed_at = now
    ret.staff_notes = req.staff_notes

    if decision == "approved":
        ret.status = "approved"
    else:
        if not req.rejection_reason or not req.rejection_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is mandatory when declining a return request",
            )
        ret.status = "rejected"
        ret.rejection_reason = req.rejection_reason.strip()

        # If all other returns for this order are rejected/cancelled, revert order status back to delivered
        order = ret.order
        if order and order.status == "return_requested":
            has_active = any(
                r.id != ret.id and r.status not in ("rejected", "cancelled")
                for r in order.returns
            )
            if not has_active:
                order.status = "delivered"
                db.add(
                    OrderStatusHistory(
                        order_id=order.id,
                        from_status="return_requested",
                        to_status="delivered",
                        note=f"Return {ret.request_number} rejected: {ret.rejection_reason}",
                        changed_by_user_id=actor_user.id,
                    )
                )

    await db.flush()

    await log_audit_event(
        db=db,
        action=f"return.{decision}",
        entity_type="return_request",
        entity_id=str(ret.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "request_number": ret.request_number,
            "decision": decision,
            "rejection_reason": ret.rejection_reason,
        },
    )

    return await get_return_request_by_id(db, ret.id)


async def receive_returned_items(
    db: AsyncSession,
    return_id: int,
    req: ReturnReceiveRequest,
    actor_user: User,
) -> ReturnRequestResponse:
    """
    Warehouse staff marks returned parcel physically received.
    Requires permission: 'returns.review'.
    """
    stmt = select(ReturnRequest).where(ReturnRequest.id == return_id)
    res = await db.execute(stmt)
    ret = res.scalar_one_or_none()

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if ret.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot receive items for return with status '{ret.status}'. Must be in 'approved' status.",
        )

    ret.status = "items_received"
    ret.received_at = datetime.now(timezone.utc)
    if req.staff_notes:
        ret.staff_notes = (ret.staff_notes or "") + f"\n[Received]: {req.staff_notes}"

    await db.flush()

    await log_audit_event(
        db=db,
        action="return.items_received",
        entity_type="return_request",
        entity_id=str(ret.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"request_number": ret.request_number},
    )

    return await get_return_request_by_id(db, ret.id)


async def inspect_returned_items(
    db: AsyncSession,
    return_id: int,
    req: ReturnInspectionRequest,
    actor_user: User,
) -> ReturnRequestResponse:
    """
    Quality control inspection of returned garments.
    Requires permission: 'returns.review'.
    Assesses garment condition (unopened, like_new, damaged, altered, missing_tags),
    executes inventory restock adjustments for restockable items, and computes approved refund amounts.
    """
    stmt = (
        select(ReturnRequest)
        .options(
            selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
            selectinload(ReturnRequest.order),
        )
        .where(ReturnRequest.id == return_id)
    )
    res = await db.execute(stmt)
    ret = res.scalar_one_or_none()

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if ret.status not in ("items_received", "inspected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot inspect return with status '{ret.status}'. Items must be received at warehouse first.",
        )

    items_map = {item.id: item for item in ret.items}
    now = datetime.now(timezone.utc)

    total_approved_refund = Decimal("0.00")

    for insp in req.items:
        if insp.return_item_id not in items_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {insp.return_item_id} does not belong to return request {ret.request_number}",
            )
        item = items_map[insp.return_item_id]

        status_val = insp.inspection_status.lower().strip()
        condition_val = insp.restock_condition.lower().strip()
        action_val = insp.restock_action.lower().strip()

        if status_val not in ("passed", "failed"):
            raise HTTPException(status_code=400, detail="Inspection status must be 'passed' or 'failed'")

        item.inspection_status = status_val
        item.restock_condition = condition_val
        item.restock_action = action_val
        item.inspector_notes = insp.inspector_notes
        item.inspected_at = now

        if status_val == "passed":
            item.refund_amount = item.unit_price * item.quantity
            total_approved_refund += item.refund_amount

            # Transactional Stock Restock if action is restock_available and not yet restocked
            if action_val == "restock_available" and item.restocked_quantity == 0:
                variant_id = item.order_item.variant_id
                if variant_id:
                    adj_req = StockAdjustmentRequest(
                        variant_id=variant_id,
                        quantity_delta=item.quantity,
                        reason="return",
                        notes=f"Return {ret.request_number} passed inspection ({condition_val}) - Restocked",
                        reference_type="return_request",
                        reference_id=ret.request_number,
                    )
                    await adjust_stock(db, request=adj_req, actor_user=actor_user)
                    item.restocked_quantity = item.quantity
        else:
            item.refund_amount = Decimal("0.00")
            item.restocked_quantity = 0

    ret.status = "inspected"
    ret.inspected_at = now
    ret.total_refund_amount = total_approved_refund
    if req.staff_notes:
        ret.staff_notes = (ret.staff_notes or "") + f"\n[Inspection]: {req.staff_notes}"

    await db.flush()

    await log_audit_event(
        db=db,
        action="return.inspected",
        entity_type="return_request",
        entity_id=str(ret.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "request_number": ret.request_number,
            "total_refund_amount": str(total_approved_refund),
            "items_inspected": len(req.items),
        },
    )

    return await get_return_request_by_id(db, ret.id)


async def resolve_return_refund(
    db: AsyncSession,
    return_id: int,
    req: ReturnRefundResolveRequest,
    actor_user: User,
) -> ReturnRequestResponse:
    """
    Execute monetary refund for inspected return request.
    Requires permission: 'refunds.create'.
    Connects to payment adapter for online payments, or validates documented manual payout
    for Cash on Delivery orders (Bank transfer / JazzCash / EasyPaisa voucher).
    """
    stmt = (
        select(ReturnRequest)
        .options(
            selectinload(ReturnRequest.order).selectinload(Order.payments),
            selectinload(ReturnRequest.items),
        )
        .where(ReturnRequest.id == return_id)
    )
    res = await db.execute(stmt)
    ret = res.scalar_one_or_none()

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if ret.status != "inspected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot execute refund for return with status '{ret.status}'. Inspection must be completed first.",
        )

    if ret.resolution_type not in ("refund", "store_credit"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Return request resolution type is '{ret.resolution_type}', not refund.",
        )

    refund_amount = req.refund_amount if req.refund_amount is not None else ret.total_refund_amount

    # Case 1: Zero refund (all items failed inspection)
    if refund_amount <= Decimal("0.00"):
        ret.status = "completed"
        ret.resolved_at = datetime.now(timezone.utc)
        await db.flush()
        return await get_return_request_by_id(db, ret.id)

    order = ret.order
    payment_stmt = (
        select(Payment)
        .options(selectinload(Payment.order))
        .where(Payment.order_id == order.id)
        .order_by(Payment.id.desc())
    )
    p_res = await db.execute(payment_stmt)
    payment = p_res.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No payment record found for order {order.order_number} to process refund against",
        )

    # Check that payment collected funds can cover refund
    if refund_amount > payment.amount_collected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Refund amount (PKR {refund_amount}) exceeds verified collected funds "
                f"(PKR {payment.amount_collected}) on order {order.order_number}"
            ),
        )

    # Online Payment vs COD Documented Operational Payout
    now = datetime.now(timezone.utc)
    if payment.payment_method != "cod" and payment.provider_code != "cod":
        # Online gateway refund (processed via payment adapter)
        ref_req = RefundCreateRequest(
            amount=refund_amount,
            reason=f"Return {ret.request_number}: Customer return passed inspection",
            notes=req.notes,
        )
        ref_resp = await create_payment_refund(db, payment_id=payment.id, req=ref_req, actor_user=actor_user)
        ret.refund_id = ref_resp.id
        ret.refund_payout_method = "original_payment_method"
    else:
        # Cash on Delivery Documented Operational Payout
        payout_method = req.payout_method or ret.refund_payout_method or "bank_transfer"
        if payout_method not in ("bank_transfer", "wallet_transfer", "store_credit"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For COD orders, refund payout method must be 'bank_transfer', 'wallet_transfer', or 'store_credit'",
            )

        if payout_method in ("bank_transfer", "wallet_transfer") and not req.payout_reference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"A verified payout transaction reference (e.g. Bank IMD/FT reference or "
                    f"JazzCash/EasyPaisa transaction ID) is required for manual COD {payout_method} refund."
                ),
            )

        refund_num = generate_refund_number()
        payout_ref = req.payout_reference or f"SC-{ret.request_number}"

        refund = Refund(
            order_id=order.id,
            payment_id=payment.id,
            refund_number=refund_num,
            amount=refund_amount,
            currency_code=payment.currency_code,
            reason=f"Return {ret.request_number}: Manual COD {payout_method} refund",
            status="completed",
            provider_reference=payout_ref,
            created_by_user_id=actor_user.id,
            notes=f"Payout Method: {payout_method}. Ref: {payout_ref}. Notes: {req.notes or 'None'}",
            completed_at=now,
        )
        db.add(refund)
        await db.flush()

        # Update payment balance
        payment.amount_collected -= refund_amount
        payment.amount_outstanding += refund_amount
        if payment.amount_collected == Decimal("0.00"):
            payment.status = "refunded"
            order.payment_status = "refunded"
        else:
            payment.status = "partially_refunded"
            order.payment_status = "partially_refunded"

        txn = PaymentTransaction(
            payment_id=payment.id,
            order_id=order.id,
            action="refunded",
            amount=refund_amount,
            currency_code=payment.currency_code,
            reference=refund_num,
            notes=f"COD {payout_method} refund executed: {payout_ref}",
            recorded_by_user_id=actor_user.id,
        )
        db.add(txn)
        ret.refund_id = refund.id
        ret.refund_payout_method = payout_method

    # Finalize return request
    ret.status = "completed"
    ret.resolved_at = now

    # Check if order is fully returned
    order_items_total = sum(i.quantity for i in order.items)
    returned_units = sum(i.quantity for i in ret.items if i.inspection_status == "passed")
    if returned_units >= order_items_total:
        order.status = "returned"
    else:
        order.status = "delivered"

    history = OrderStatusHistory(
        order_id=order.id,
        from_status="return_requested",
        to_status=order.status,
        note=f"Return {ret.request_number} completed: Refund PKR {refund_amount}",
        changed_by_user_id=actor_user.id,
    )
    db.add(history)
    await db.flush()

    await log_audit_event(
        db=db,
        action="return.refund_processed",
        entity_type="return_request",
        entity_id=str(ret.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "request_number": ret.request_number,
            "refund_amount": str(refund_amount),
            "payout_method": ret.refund_payout_method,
            "refund_id": ret.refund_id,
        },
    )

    return await get_return_request_by_id(db, ret.id)


async def resolve_return_exchange(
    db: AsyncSession,
    return_id: int,
    req: ReturnExchangeResolveRequest,
    actor_user: User,
) -> ReturnRequestResponse:
    """
    Execute doorstep replacement dispatch for inspected exchange request.
    Requires permission: 'returns.resolve'.
    Allocates replacement items, creates a zero-fee replacement parcel with the courier,
    and advances order to completed exchange.
    """
    stmt = (
        select(ReturnRequest)
        .options(
            selectinload(ReturnRequest.order),
            selectinload(ReturnRequest.items)
            .selectinload(ReturnItem.exchange_variant)
            .selectinload(ProductVariant.product),
            selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
        )
        .where(ReturnRequest.id == return_id)
    )
    res = await db.execute(stmt)
    ret = res.scalar_one_or_none()

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if ret.status != "inspected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot execute exchange for return with status '{ret.status}'. Inspection must be completed first.",
        )

    if ret.resolution_type != "exchange":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Return request resolution type is '{ret.resolution_type}', not exchange.",
        )

    order = ret.order
    now = datetime.now(timezone.utc)

    # Verify that exchange items passed inspection
    passed_exchange_items = [it for it in ret.items if it.inspection_status == "passed"]
    if not passed_exchange_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot dispatch exchange: No returned items passed quality inspection",
        )

    # Reserve and create replacement shipment
    provider = get_courier_provider(req.courier_code)
    try:
        addr = json.loads(order.shipping_address_snapshot)
    except Exception:
        addr = {}

    shipment_number = generate_shipment_number()
    destination_city = addr.get("city") or "Pakistan"
    total_weight = 500 * sum(it.quantity for it in passed_exchange_items)

    consignment = await provider.book_consignment(
        shipment_number=shipment_number,
        destination_city=destination_city,
        destination_address=addr,
        cod_amount=Decimal("0.00"),
        weight_grams=total_weight,
        order_number=order.order_number,
        customer_phone=order.customer_phone,
        customer_name=order.customer_name,
        manual_tracking_number=None,
    )

    courier_name = consignment.courier_name
    tracking_num = consignment.tracking_number
    tracking_url = consignment.tracking_url

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
        total_weight_grams=total_weight,
        package_count=1,
        cod_amount_to_collect=Decimal("0.00"),
        dispatch_notes=f"Doorstep Exchange for {ret.request_number}: {req.dispatch_notes or 'Deliver replacement'}",
        allocated_at=now,
        created_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(shipment)
    await db.flush()

    for it in passed_exchange_items:
        s_item = ShipmentItem(
            shipment_id=shipment.id,
            order_item_id=it.order_item_id,
            quantity=it.quantity,
            product_name_snapshot=(
                it.exchange_variant.product.name
                if (it.exchange_variant and it.exchange_variant.product)
                else (it.order_item.product_name_snapshot if it.order_item else "Exchange Item")
            ),
            sku_snapshot=(
                it.exchange_variant.sku
                if it.exchange_variant
                else (it.order_item.sku_snapshot if it.order_item else "EXCHANGE-SKU")
            ),
            size_snapshot=(
                it.exchange_variant.size
                if it.exchange_variant
                else (it.order_item.size_snapshot if it.order_item else None)
            ),
            color_snapshot=(
                (it.exchange_variant.color_name if hasattr(it.exchange_variant, "color_name") else None)
                if it.exchange_variant
                else (it.order_item.color_snapshot if it.order_item else None)
            ),
        )
        db.add(s_item)

    init_event = ShipmentEvent(
        shipment_id=shipment.id,
        status="allocated",
        location=destination_city or "Warehouse Fulfillment Center",
        description=f"Replacement parcel booked with {courier_name} for exchange {ret.request_number}",
        source="staff",
        recorded_by_user_id=actor_user.id if actor_user else None,
        occurred_at=now,
    )
    db.add(init_event)

    ret.status = "completed"
    ret.resolved_at = now
    if req.dispatch_notes:
        ret.staff_notes = (ret.staff_notes or "") + f"\n[Exchange Dispatched]: {req.dispatch_notes} (Shipment: {shipment.shipment_number})"

    order.status = "delivered"
    history = OrderStatusHistory(
        order_id=order.id,
        from_status="return_requested",
        to_status="delivered",
        note=f"Exchange {ret.request_number} resolved with replacement shipment {shipment.shipment_number}",
        changed_by_user_id=actor_user.id,
    )
    db.add(history)
    await db.flush()

    await log_audit_event(
        db=db,
        action="return.exchange_processed",
        entity_type="return_request",
        entity_id=str(ret.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "request_number": ret.request_number,
            "shipment_number": shipment.shipment_number,
            "items_count": len(passed_exchange_items),
        },
    )

    return await get_return_request_by_id(db, ret.id)


async def get_return_request_by_id(db: AsyncSession, return_id: int) -> ReturnRequestResponse:
    """Retrieve full return request details with items."""
    stmt = (
        select(ReturnRequest)
        .options(
            selectinload(ReturnRequest.items),
        )
        .where(ReturnRequest.id == return_id)
    )
    res = await db.execute(stmt)
    ret = res.scalar_one_or_none()

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    return build_return_response(ret)


async def list_return_requests(
    db: AsyncSession,
    order_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    request_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ReturnRequestResponse], int]:
    """Search and paginate return and exchange requests for administrative operations."""
    query = (
        select(ReturnRequest)
        .options(selectinload(ReturnRequest.items))
        .order_by(ReturnRequest.id.desc())
    )

    if order_id:
        query = query.where(ReturnRequest.order_id == order_id)
    if status_filter:
        query = query.where(ReturnRequest.status == status_filter)
    if request_type:
        query = query.where(ReturnRequest.request_type == request_type)
    if search:
        search_pat = f"%{search.strip()}%"
        query = query.where(
            (ReturnRequest.request_number.ilike(search_pat))
            | (ReturnRequest.customer_notes.ilike(search_pat))
            | (ReturnRequest.rejection_reason.ilike(search_pat))
        )

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar_one()

    paginated = query.limit(limit).offset(offset)
    res = await db.execute(paginated)
    items = res.scalars().all()

    return [build_return_response(r) for r in items], total


async def get_order_return_requests(
    db: AsyncSession,
    order_number: str,
    current_user: Optional[User] = None,
    customer_phone: Optional[str] = None,
) -> List[ReturnRequestResponse]:
    """Retrieve return and exchange history for a customer's order."""
    order_stmt = (
        select(Order)
        .options(selectinload(Order.returns).selectinload(ReturnRequest.items))
        .where(Order.order_number == order_number)
    )
    res = await db.execute(order_stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if current_user and current_user.user_type == "customer":
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
    elif not current_user:
        if not customer_phone or customer_phone.strip() != order.customer_phone.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number verification required to view guest order return history",
            )

    return [build_return_response(r) for r in order.returns]
