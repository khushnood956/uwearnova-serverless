"""
Offline Sales Service Layer
Orchestrates walk-in transactions, inventory decrements, movements ledger, and void reversals.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
import secrets
from typing import Optional, Tuple
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import AppException
from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.catalog.models import Product, ProductVariant
from app.modules.inventory.models import InventoryItem, InventoryLocation, InventoryMovement
from app.modules.offline_sales.models import OfflineSale, OfflineSaleItem
from app.modules.offline_sales.schemas import (
    OfflineSaleCreate,
    OfflineSaleSummaryStats,
)


def generate_receipt_number() -> str:
    """Generate high-entropy unique POS receipt code: POS-YYYYMMDD-XXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_hex = secrets.token_hex(3).upper()
    return f"POS-{date_str}-{random_hex}"


async def create_offline_sale(
    db: AsyncSession,
    data: OfflineSaleCreate,
    actor_user: Optional[User] = None,
) -> OfflineSale:
    """
    Record an in-store offline product sale.
    Deducts physical variant inventory in real time, creates audit logs and movement entries.
    """
    # 1. Resolve default inventory location for movement recording
    loc_res = await db.execute(select(InventoryLocation.id).where(InventoryLocation.is_active == True).limit(1))
    location_id = loc_res.scalar()
    if not location_id:
        fallback_loc = await db.execute(select(InventoryLocation.id).limit(1))
        location_id = fallback_loc.scalar() or 1

    receipt_number = generate_receipt_number()
    subtotal = Decimal("0.00")
    sale_items = []

    # 2. Process line items and check stock
    for item_in in data.items:
        # Load variant with product relation
        var_res = await db.execute(
            select(ProductVariant)
            .options(selectinload(ProductVariant.product))
            .where(ProductVariant.id == item_in.variant_id)
        )
        variant = var_res.scalar_one_or_none()
        if not variant:
            raise AppException(
                message=f"Product variant with ID {item_in.variant_id} does not exist.",
                code="VARIANT_NOT_FOUND",
                status_code=404,
            )

        if variant.inventory_count < item_in.quantity:
            raise AppException(
                message=(
                    f"Insufficient inventory for '{variant.product.name} ({variant.size} / {variant.color_name})'. "
                    f"Available stock: {variant.inventory_count}, requested: {item_in.quantity}."
                ),
                code="INSUFFICIENT_STOCK",
                status_code=400,
            )

        # Determine unit price (override > variant price > product price)
        if item_in.unit_price_override is not None:
            unit_price = item_in.unit_price_override
        elif variant.price is not None:
            unit_price = variant.price
        else:
            unit_price = variant.product.price

        line_total = unit_price * Decimal(item_in.quantity)
        subtotal += line_total

        # 3. Deduct stock from ProductVariant
        prev_count = variant.inventory_count
        variant.inventory_count -= item_in.quantity
        if variant.inventory_count <= 0:
            variant.inventory_count = 0
            variant.in_stock = False
        new_count = variant.inventory_count

        # 4. Deduct stock from InventoryItem if present
        inv_items_res = await db.execute(
            select(InventoryItem).where(InventoryItem.variant_id == variant.id)
        )
        for inv_item in inv_items_res.scalars().all():
            inv_item.quantity_on_hand = max(0, inv_item.quantity_on_hand - item_in.quantity)

        # 5. Ledger movement entry
        movement = InventoryMovement(
            variant_id=variant.id,
            location_id=location_id,
            movement_type="offline_sale",
            quantity_delta=-item_in.quantity,
            quantity_on_hand_before=prev_count,
            quantity_on_hand_after=new_count,
            quantity_reserved_before=0,
            quantity_reserved_after=0,
            reference_type="offline_sale",
            reference_id=receipt_number,
            reason_notes=f"Offline walk-in sale ({receipt_number})",
            created_by_user_id=actor_user.id if actor_user else None,
        )
        db.add(movement)

        # Build sale item record
        now = datetime.now(timezone.utc)
        variant_label = f"Size: {variant.size} | Color: {variant.color_name}"
        sale_item = OfflineSaleItem(
            product_id=variant.product_id,
            variant_id=variant.id,
            product_name=variant.product.name,
            sku=variant.sku,
            variant_label=variant_label,
            unit_price=unit_price,
            quantity=item_in.quantity,
            line_total=line_total,
            created_at=now,
            updated_at=now,
        )
        sale_items.append(sale_item)

    # 6. Calculate total tender
    total_amount = max(
        Decimal("0.00"),
        subtotal - data.discount_amount + data.tax_amount,
    )

    staff_name = None
    if actor_user:
        staff_name = actor_user.email.split("@")[0].capitalize()

    now = datetime.now(timezone.utc)
    sale = OfflineSale(
        receipt_number=receipt_number,
        sale_date=now,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        customer_email=data.customer_email,
        payment_method=data.payment_method,
        subtotal=subtotal,
        discount_amount=data.discount_amount,
        tax_amount=data.tax_amount,
        total_amount=total_amount,
        status="completed",
        notes=data.notes,
        staff_id=actor_user.id if actor_user else None,
        staff_name=staff_name,
        items=sale_items,
        created_at=now,
        updated_at=now,
    )
    db.add(sale)
    await db.flush()

    # 7. Audit log event
    if actor_user:
        await log_audit_event(
            db,
            action="offline_sale.recorded",
            entity_type="offline_sale",
            entity_id=str(sale.id),
            user_id=actor_user.id,
            actor_email=actor_user.email,
            details={
                "receipt_number": sale.receipt_number,
                "total_amount": str(sale.total_amount),
                "items_count": len(sale_items),
                "payment_method": sale.payment_method,
            },
        )
        await db.flush()

    return sale


async def list_offline_sales(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[list[OfflineSale], int, OfflineSaleSummaryStats]:
    """Retrieve paginated offline sales list with aggregate business metrics."""
    query = select(OfflineSale).options(selectinload(OfflineSale.items)).order_by(desc(OfflineSale.created_at))

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                OfflineSale.receipt_number.ilike(term),
                OfflineSale.customer_name.ilike(term),
                OfflineSale.customer_phone.ilike(term),
            )
        )

    if payment_method:
        query = query.where(OfflineSale.payment_method == payment_method)

    if status:
        query = query.where(OfflineSale.status == status)

    # Count total
    count_query = select(func.count(OfflineSale.id))
    if search and search.strip():
        term = f"%{search.strip()}%"
        count_query = count_query.where(
            or_(
                OfflineSale.receipt_number.ilike(term),
                OfflineSale.customer_name.ilike(term),
                OfflineSale.customer_phone.ilike(term),
            )
        )
    if payment_method:
        count_query = count_query.where(OfflineSale.payment_method == payment_method)
    if status:
        count_query = count_query.where(OfflineSale.status == status)

    total_count = (await db.execute(count_query)).scalar() or 0

    # Execute page
    result = await db.execute(query.limit(limit).offset(offset))
    items = list(result.scalars().all())

    # Calculate summary metrics over active (completed) sales
    stats_query = select(
        func.count(OfflineSale.id),
        func.coalesce(func.sum(OfflineSale.total_amount), Decimal("0.00")),
        func.coalesce(
            func.sum(
                case((OfflineSale.payment_method == "cash", OfflineSale.total_amount), else_=Decimal("0.00"))
            ),
            Decimal("0.00"),
        ),
        func.coalesce(
            func.sum(
                case((OfflineSale.payment_method == "pos_card", OfflineSale.total_amount), else_=Decimal("0.00"))
            ),
            Decimal("0.00"),
        ),
    ).where(OfflineSale.status == "completed")

    stats_res = await db.execute(stats_query)
    c_count, c_rev, c_cash, c_card = stats_res.first() or (0, Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))

    # Units sold
    units_query = select(func.coalesce(func.sum(OfflineSaleItem.quantity), 0)).join(
        OfflineSale, OfflineSaleItem.sale_id == OfflineSale.id
    ).where(OfflineSale.status == "completed")
    units_sold = (await db.execute(units_query)).scalar() or 0

    summary = OfflineSaleSummaryStats(
        total_sales_count=c_count or 0,
        total_revenue=Decimal(str(c_rev or 0)),
        total_units_sold=units_sold or 0,
        cash_revenue=Decimal(str(c_cash or 0)),
        card_revenue=Decimal(str(c_card or 0)),
    )

    return items, total_count, summary


async def get_offline_sale(db: AsyncSession, sale_id: int) -> OfflineSale:
    """Retrieve full offline sale transaction with items."""
    query = (
        select(OfflineSale)
        .options(selectinload(OfflineSale.items))
        .where(OfflineSale.id == sale_id)
    )
    result = await db.execute(query)
    sale = result.scalar_one_or_none()
    if not sale:
        raise AppException(
            message=f"Offline sale with ID {sale_id} not found.",
            code="SALE_NOT_FOUND",
            status_code=404,
        )
    return sale


async def void_offline_sale(
    db: AsyncSession,
    sale_id: int,
    actor_user: Optional[User] = None,
) -> OfflineSale:
    """
    Void a recorded offline sale, reversing inventory deductions.
    """
    sale = await get_offline_sale(db, sale_id)
    if sale.status == "voided":
        raise AppException(
            message=f"Offline sale {sale.receipt_number} has already been voided.",
            code="SALE_ALREADY_VOIDED",
            status_code=400,
        )

    loc_res = await db.execute(select(InventoryLocation.id).where(InventoryLocation.is_active == True).limit(1))
    location_id = loc_res.scalar() or 1

    # Reverse inventory for each item
    for item in sale.items:
        var_res = await db.execute(
            select(ProductVariant).where(ProductVariant.id == item.variant_id)
        )
        variant = var_res.scalar_one_or_none()
        if variant:
            prev_count = variant.inventory_count
            variant.inventory_count += item.quantity
            variant.in_stock = True
            new_count = variant.inventory_count

            # Reverse inventory item
            inv_items_res = await db.execute(
                select(InventoryItem).where(InventoryItem.variant_id == variant.id)
            )
            for inv_item in inv_items_res.scalars().all():
                inv_item.quantity_on_hand += item.quantity

            # Reverse movement
            movement = InventoryMovement(
                variant_id=variant.id,
                location_id=location_id,
                movement_type="offline_sale_void",
                quantity_delta=item.quantity,
                quantity_on_hand_before=prev_count,
                quantity_on_hand_after=new_count,
                quantity_reserved_before=0,
                quantity_reserved_after=0,
                reference_type="offline_sale_void",
                reference_id=f"VOID-{sale.receipt_number}",
                reason_notes=f"Voided offline sale {sale.receipt_number}",
                created_by_user_id=actor_user.id if actor_user else None,
            )
            db.add(movement)

    sale.status = "voided"
    await db.flush()

    if actor_user:
        await log_audit_event(
            db,
            action="offline_sale.voided",
            entity_type="offline_sale",
            entity_id=str(sale.id),
            user_id=actor_user.id,
            actor_email=actor_user.email,
            details={"receipt_number": sale.receipt_number},
        )
        await db.flush()

    return sale
