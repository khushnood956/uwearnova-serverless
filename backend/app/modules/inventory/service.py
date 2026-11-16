"""
Inventory Service Layer (M09)
Handles warehouse locations, stock adjustments, reservations, releases,
reorder threshold evaluations, and immutable movement logging.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.catalog.models import Product, ProductVariant
from app.modules.inventory.models import InventoryItem, InventoryLocation, InventoryMovement
from app.modules.inventory.schemas import (
    BulkStockAdjustmentRequest,
    BulkStockAdjustmentResponse,
    InventoryItemResponse,
    InventoryMovementResponse,
    LowStockItemResponse,
    LowStockReportResponse,
    StockAdjustmentRequest,
    StockReleaseRequest,
    StockReservationRequest,
)


async def get_or_create_default_location(db: AsyncSession) -> InventoryLocation:
    """Ensure at least the primary fulfillment warehouse location exists."""
    stmt = select(InventoryLocation).where(InventoryLocation.code == "WH-PRIMARY")
    res = await db.execute(stmt)
    location = res.scalar_one_or_none()
    if location is not None:
        return location

    try:
        async with db.begin_nested():
            location = InventoryLocation(
                name="Primary Fulfillment Warehouse",
                code="WH-PRIMARY",
                address_line_1="Site Industrial Area",
                city="Karachi",
                postal_code="75700",
                country_code="PK",
                is_active=True,
            )
            db.add(location)
            await db.flush()
    except Exception:
        # Handled if another coroutine inserted WH-PRIMARY concurrently
        pass

    stmt = select(InventoryLocation).where(InventoryLocation.code == "WH-PRIMARY")
    res = await db.execute(stmt)
    return res.scalar_one()


async def get_inventory_item(
    db: AsyncSession,
    variant_id: int,
    location_id: int,
    for_update: bool = False,
) -> Optional[InventoryItem]:
    """Retrieve an inventory item record for a given variant and location, optionally locking row."""
    stmt = select(InventoryItem).where(
        InventoryItem.variant_id == variant_id,
        InventoryItem.location_id == location_id,
    )
    if for_update:
        # SQLite does not support row-level locks, but SQLAlchemy handles it or we guard it
        stmt = stmt.with_for_update()

    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def get_or_create_inventory_item(
    db: AsyncSession,
    variant_id: int,
    location_id: int,
    for_update: bool = False,
) -> InventoryItem:
    """Retrieve existing inventory item or initialize one at zero stock if valid variant & location."""
    item = await get_inventory_item(db, variant_id, location_id, for_update=for_update)
    if item is not None:
        return item

    # Verify variant exists
    variant_stmt = select(ProductVariant).where(ProductVariant.id == variant_id)
    variant_res = await db.execute(variant_stmt)
    variant = variant_res.scalar_one_or_none()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product variant ID {variant_id} not found",
        )

    # Verify location exists
    loc_stmt = select(InventoryLocation).where(InventoryLocation.id == location_id)
    loc_res = await db.execute(loc_stmt)
    location = loc_res.scalar_one_or_none()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory location ID {location_id} not found",
        )

    try:
        async with db.begin_nested():
            item = InventoryItem(
                variant_id=variant_id,
                location_id=location_id,
                quantity_on_hand=0,
                quantity_reserved=0,
                reorder_threshold=5,
            )
            db.add(item)
            await db.flush()
    except Exception:
        pass

    item = await get_inventory_item(db, variant_id, location_id, for_update=for_update)
    if item is not None:
        return item

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to retrieve or create inventory item record",
    )


async def _sync_variant_inventory(db: AsyncSession, variant_id: int) -> None:
    """Synchronize parent ProductVariant.inventory_count and in_stock flag based on active available stock."""
    stmt = select(InventoryItem).where(InventoryItem.variant_id == variant_id)
    res = await db.execute(stmt)
    items = res.scalars().all()

    total_available = sum(max(0, it.quantity_on_hand - it.quantity_reserved) for it in items)

    v_stmt = select(ProductVariant).where(ProductVariant.id == variant_id)
    v_res = await db.execute(v_stmt)
    variant = v_res.scalar_one_or_none()
    if variant:
        variant.inventory_count = total_available
        variant.in_stock = total_available > 0
        await db.flush()


async def adjust_stock(
    db: AsyncSession,
    request: StockAdjustmentRequest,
    actor_user: Optional[User] = None,
) -> Tuple[InventoryItem, InventoryMovement]:
    """
    Execute manual stock adjustment.
    Prevents negative on-hand stock and ensures on-hand cannot drop below reserved quantity.
    Uses atomic conditional database updates for concurrency safety.
    Records immutable movement entry and updates variant availability.
    """
    if request.location_id is None:
        default_loc = await get_or_create_default_location(db)
        location_id = default_loc.id
    else:
        location_id = request.location_id

    item = await get_or_create_inventory_item(db, request.variant_id, location_id, for_update=True)

    # Capture before snapshots
    on_hand_before = item.quantity_on_hand
    reserved_before = item.quantity_reserved
    reserved_after = item.quantity_reserved

    # Conditional atomic update preventing negative stock or drop below reserved
    stmt = (
        update(InventoryItem)
        .where(
            InventoryItem.id == item.id,
            (InventoryItem.quantity_on_hand + request.quantity_delta) >= InventoryItem.quantity_reserved,
            (InventoryItem.quantity_on_hand + request.quantity_delta) >= 0,
        )
        .values(quantity_on_hand=InventoryItem.quantity_on_hand + request.quantity_delta)
    )
    res = await db.execute(stmt)
    if res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"INSUFFICIENT_STOCK: Adjustment delta ({request.quantity_delta}) would result in negative or insufficient stock for active reservations",
        )

    await db.flush()
    await db.refresh(item)
    on_hand_after = item.quantity_on_hand

    movement = InventoryMovement(
        variant_id=item.variant_id,
        location_id=item.location_id,
        movement_type=request.reason,
        quantity_delta=request.quantity_delta,
        quantity_on_hand_before=on_hand_before,
        quantity_on_hand_after=on_hand_after,
        quantity_reserved_before=reserved_before,
        quantity_reserved_after=reserved_after,
        reference_type=request.reference_type or "manual_adjustment",
        reference_id=request.reference_id,
        reason_notes=request.notes,
        created_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(movement)
    await db.flush()

    await _sync_variant_inventory(db, item.variant_id)

    # Audit logging
    await log_audit_event(
        db=db,
        action="inventory.adjusted",
        entity_type="inventory_item",
        entity_id=str(item.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "variant_id": item.variant_id,
            "location_id": item.location_id,
            "delta": request.quantity_delta,
            "reason": request.reason,
            "on_hand_before": on_hand_before,
            "on_hand_after": on_hand_after,
            "notes": request.notes,
        },
    )

    return item, movement


async def reserve_stock(
    db: AsyncSession,
    request: StockReservationRequest,
    actor_user: Optional[User] = None,
) -> Tuple[InventoryItem, InventoryMovement]:
    """
    Reserve available stock for checkout or order fulfillment foundation.
    Uses conditional atomic database updates to reject reservations exceeding available stock.
    """
    if request.location_id is None:
        default_loc = await get_or_create_default_location(db)
        location_id = default_loc.id
    else:
        location_id = request.location_id

    item = await get_or_create_inventory_item(db, request.variant_id, location_id, for_update=True)

    on_hand_before = item.quantity_on_hand
    on_hand_after = item.quantity_on_hand
    reserved_before = item.quantity_reserved

    stmt = (
        update(InventoryItem)
        .where(
            InventoryItem.id == item.id,
            (InventoryItem.quantity_on_hand - InventoryItem.quantity_reserved) >= request.quantity,
        )
        .values(quantity_reserved=InventoryItem.quantity_reserved + request.quantity)
    )
    res = await db.execute(stmt)
    if res.rowcount == 0:
        available = max(0, item.quantity_on_hand - item.quantity_reserved)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"INSUFFICIENT_STOCK: Requested reservation of {request.quantity} units exceeds available stock of {available}",
        )

    await db.flush()
    await db.refresh(item)
    reserved_after = item.quantity_reserved

    movement = InventoryMovement(
        variant_id=item.variant_id,
        location_id=item.location_id,
        movement_type="reservation",
        quantity_delta=-request.quantity,  # delta on available inventory
        quantity_on_hand_before=on_hand_before,
        quantity_on_hand_after=on_hand_after,
        quantity_reserved_before=reserved_before,
        quantity_reserved_after=reserved_after,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        reason_notes=request.notes,
        created_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(movement)
    await db.flush()

    await _sync_variant_inventory(db, item.variant_id)

    await log_audit_event(
        db=db,
        action="inventory.reserved",
        entity_type="inventory_item",
        entity_id=str(item.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "variant_id": item.variant_id,
            "quantity_reserved": request.quantity,
            "reference_type": request.reference_type,
            "reference_id": request.reference_id,
        },
    )

    return item, movement


async def release_stock(
    db: AsyncSession,
    request: StockReleaseRequest,
    actor_user: Optional[User] = None,
) -> Tuple[InventoryItem, InventoryMovement]:
    """
    Release previously reserved stock back to available stock (e.g. checkout expired or cancelled).
    Uses conditional atomic database updates to reject releasing more than currently reserved.
    """
    if request.location_id is None:
        default_loc = await get_or_create_default_location(db)
        location_id = default_loc.id
    else:
        location_id = request.location_id

    item = await get_or_create_inventory_item(db, request.variant_id, location_id, for_update=True)

    on_hand_before = item.quantity_on_hand
    on_hand_after = item.quantity_on_hand
    reserved_before = item.quantity_reserved

    stmt = (
        update(InventoryItem)
        .where(
            InventoryItem.id == item.id,
            InventoryItem.quantity_reserved >= request.quantity,
        )
        .values(quantity_reserved=InventoryItem.quantity_reserved - request.quantity)
    )
    res = await db.execute(stmt)
    if res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"INVALID_RELEASE_QUANTITY: Cannot release {request.quantity} units; only {item.quantity_reserved} units are currently reserved",
        )

    await db.flush()
    await db.refresh(item)
    reserved_after = item.quantity_reserved

    movement = InventoryMovement(
        variant_id=item.variant_id,
        location_id=item.location_id,
        movement_type="release",
        quantity_delta=request.quantity,  # delta restoring available stock
        quantity_on_hand_before=on_hand_before,
        quantity_on_hand_after=on_hand_after,
        quantity_reserved_before=reserved_before,
        quantity_reserved_after=reserved_after,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        reason_notes=request.notes,
        created_by_user_id=actor_user.id if actor_user else None,
    )
    db.add(movement)
    await db.flush()

    await _sync_variant_inventory(db, item.variant_id)

    await log_audit_event(
        db=db,
        action="inventory.released",
        entity_type="inventory_item",
        entity_id=str(item.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={
            "variant_id": item.variant_id,
            "quantity_released": request.quantity,
            "reference_type": request.reference_type,
            "reference_id": request.reference_id,
        },
    )

    return item, movement


async def update_reorder_threshold(
    db: AsyncSession,
    variant_id: int,
    location_id: int,
    threshold: int,
    actor_user: Optional[User] = None,
) -> InventoryItem:
    """Update replenishment alert threshold for an inventory item."""
    item = await get_or_create_inventory_item(db, variant_id, location_id)
    item.reorder_threshold = threshold
    await db.flush()

    await log_audit_event(
        db=db,
        action="inventory.threshold_updated",
        entity_type="inventory_item",
        entity_id=str(item.id),
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={"reorder_threshold": threshold},
    )
    return item


async def list_inventory_items(
    db: AsyncSession,
    location_id: Optional[int] = None,
    low_stock_only: bool = False,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[InventoryItemResponse], int]:
    """Retrieve paginated inventory records with enriched variant and product metadata."""
    query = (
        select(
            InventoryItem,
            ProductVariant.sku.label("variant_sku"),
            ProductVariant.size.label("variant_size"),
            ProductVariant.color_name.label("variant_color"),
            Product.name.label("product_name"),
            InventoryLocation.name.label("location_name"),
            InventoryLocation.code.label("location_code"),
        )
        .join(ProductVariant, InventoryItem.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .join(InventoryLocation, InventoryItem.location_id == InventoryLocation.id)
    )

    if location_id is not None:
        query = query.where(InventoryItem.location_id == location_id)

    if low_stock_only:
        query = query.where(
            (InventoryItem.quantity_on_hand - InventoryItem.quantity_reserved) <= InventoryItem.reorder_threshold
        )

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            ProductVariant.sku.ilike(search_term) | Product.name.ilike(search_term)
        )

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    # Paginate
    query = query.order_by(Product.name.asc(), ProductVariant.sku.asc()).offset(offset).limit(limit)
    res = await db.execute(query)
    rows = res.all()

    items: List[InventoryItemResponse] = []
    for row in rows:
        item: InventoryItem = row[0]
        items.append(
            InventoryItemResponse(
                id=item.id,
                variant_id=item.variant_id,
                location_id=item.location_id,
                quantity_on_hand=item.quantity_on_hand,
                quantity_reserved=item.quantity_reserved,
                quantity_available=item.quantity_available,
                reorder_threshold=item.reorder_threshold,
                is_low_stock=item.is_low_stock,
                variant_sku=row.variant_sku,
                variant_size=row.variant_size,
                variant_color=row.variant_color,
                product_name=row.product_name,
                location_name=row.location_name,
                location_code=row.location_code,
                updated_at=item.updated_at,
            )
        )

    return items, total


async def list_inventory_movements(
    db: AsyncSession,
    variant_id: Optional[int] = None,
    location_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[InventoryMovementResponse], int]:
    """Retrieve paginated immutable inventory movement records."""
    query = (
        select(
            InventoryMovement,
            ProductVariant.sku.label("variant_sku"),
            InventoryLocation.code.label("location_code"),
        )
        .join(ProductVariant, InventoryMovement.variant_id == ProductVariant.id)
        .join(InventoryLocation, InventoryMovement.location_id == InventoryLocation.id)
    )

    if variant_id is not None:
        query = query.where(InventoryMovement.variant_id == variant_id)

    if location_id is not None:
        query = query.where(InventoryMovement.location_id == location_id)

    if movement_type is not None:
        query = query.where(InventoryMovement.movement_type == movement_type)

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    query = query.order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    rows = res.all()

    movements: List[InventoryMovementResponse] = []
    for row in rows:
        m: InventoryMovement = row[0]
        movements.append(
            InventoryMovementResponse(
                id=m.id,
                variant_id=m.variant_id,
                location_id=m.location_id,
                movement_type=m.movement_type,
                quantity_delta=m.quantity_delta,
                quantity_on_hand_before=m.quantity_on_hand_before,
                quantity_on_hand_after=m.quantity_on_hand_after,
                quantity_reserved_before=m.quantity_reserved_before,
                quantity_reserved_after=m.quantity_reserved_after,
                reference_type=m.reference_type,
                reference_id=m.reference_id,
                reason_notes=m.reason_notes,
                created_by_user_id=m.created_by_user_id,
                created_at=m.created_at,
                variant_sku=row.variant_sku,
                location_code=row.location_code,
            )
        )

    return movements, total


async def bulk_adjust_stock(
    db: AsyncSession,
    request: BulkStockAdjustmentRequest,
    actor_user: Optional[User] = None,
) -> BulkStockAdjustmentResponse:
    """
    Execute batch stock adjustments within an atomic database transaction.
    """
    total_delta = 0
    adjusted_count = 0

    for adj in request.adjustments:
        adj_req = StockAdjustmentRequest(
            variant_id=adj.variant_id,
            location_id=adj.location_id,
            quantity_delta=adj.quantity_delta,
            reason=adj.reason,
            notes=adj.notes,
            reference_type="bulk_adjustment",
        )
        await adjust_stock(db, adj_req, actor_user=actor_user)
        total_delta += adj.quantity_delta
        adjusted_count += 1

    await log_audit_event(
        db=db,
        action="inventory.bulk_adjusted",
        entity_type="inventory",
        entity_id="bulk",
        user_id=actor_user.id if actor_user else None,
        actor_email=actor_user.email if actor_user else None,
        details={"adjusted_count": adjusted_count, "total_delta": total_delta},
    )

    return BulkStockAdjustmentResponse(
        adjusted_count=adjusted_count,
        total_delta=total_delta,
        timestamp=datetime.now(timezone.utc),
    )


async def get_low_stock_report(
    db: AsyncSession,
    location_id: Optional[int] = None,
) -> LowStockReportResponse:
    """
    Generate actionable low-stock replenishment deficit report across variants.
    """
    query = (
        select(
            InventoryItem,
            ProductVariant.sku.label("variant_sku"),
            ProductVariant.size.label("variant_size"),
            ProductVariant.color_name.label("variant_color"),
            Product.name.label("product_name"),
            InventoryLocation.name.label("location_name"),
            InventoryLocation.code.label("location_code"),
        )
        .join(ProductVariant, InventoryItem.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .join(InventoryLocation, InventoryItem.location_id == InventoryLocation.id)
        .where(
            (InventoryItem.quantity_on_hand - InventoryItem.quantity_reserved) <= InventoryItem.reorder_threshold
        )
        .order_by((InventoryItem.reorder_threshold - (InventoryItem.quantity_on_hand - InventoryItem.quantity_reserved)).desc())
    )

    if location_id is not None:
        query = query.where(InventoryItem.location_id == location_id)

    res = await db.execute(query)
    rows = res.all()

    report: List[LowStockItemResponse] = []
    for row in rows:
        item: InventoryItem = row[0]
        avail = max(0, item.quantity_on_hand - item.quantity_reserved)
        deficit = max(0, item.reorder_threshold - avail)
        report.append(
            LowStockItemResponse(
                item_id=item.id,
                variant_id=item.variant_id,
                variant_sku=row.variant_sku,
                product_name=row.product_name,
                variant_size=row.variant_size,
                variant_color=row.variant_color,
                location_id=item.location_id,
                location_name=row.location_name,
                location_code=row.location_code,
                quantity_on_hand=item.quantity_on_hand,
                quantity_reserved=item.quantity_reserved,
                quantity_available=avail,
                reorder_threshold=item.reorder_threshold,
                deficit=deficit,
                updated_at=item.updated_at,
            )
        )

    return LowStockReportResponse(
        items=report,
        total_low_stock_items=len(report),
        generated_at=datetime.now(timezone.utc),
    )

