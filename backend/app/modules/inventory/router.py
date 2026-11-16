"""
Inventory API Endpoints (M09)
Protected administrative routes for stock tracking, adjustments,
reservations, releases, and movement history.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.inventory.models import InventoryLocation
from app.modules.inventory.schemas import (
    BulkStockAdjustmentRequest,
    BulkStockAdjustmentResponse,
    InventoryItemListResponse,
    InventoryItemResponse,
    InventoryLocationCreate,
    InventoryLocationResponse,
    InventoryMovementListResponse,
    InventoryMovementResponse,
    LowStockReportResponse,
    StockAdjustmentRequest,
    StockReleaseRequest,
    StockReservationRequest,
    StockThresholdUpdateRequest,
)
from app.modules.inventory.service import (
    adjust_stock,
    bulk_adjust_stock,
    get_low_stock_report,
    get_or_create_default_location,
    list_inventory_items,
    list_inventory_movements,
    release_stock,
    reserve_stock,
    update_reorder_threshold,
)
from app.modules.rbac.dependencies import require_permission

admin_inventory_router = APIRouter(
    prefix="/admin/inventory",
    tags=["Admin: Inventory"],
)


class StockOperationResponse(BaseModel):
    item: InventoryItemResponse
    movement: InventoryMovementResponse


@admin_inventory_router.get(
    "/locations",
    response_model=List[InventoryLocationResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List Warehouse Locations",
)
async def list_locations(
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> List[InventoryLocationResponse]:
    """Retrieve all warehouse locations."""
    # Ensure default location exists
    await get_or_create_default_location(db)
    stmt = select(InventoryLocation).order_by(InventoryLocation.name.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


@admin_inventory_router.post(
    "/locations",
    response_model=InventoryLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create Warehouse Location",
)
async def create_location(
    req: InventoryLocationCreate,
    current_user: User = Depends(require_permission("inventory.adjust")),
    db: AsyncSession = Depends(get_db),
) -> InventoryLocationResponse:
    """Create a new fulfillment or retail inventory location."""
    location = InventoryLocation(**req.model_dump())
    db.add(location)
    await db.flush()
    await db.refresh(location)
    return location


@admin_inventory_router.get(
    "",
    response_model=InventoryItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: List Inventory Stock Levels",
)
async def list_inventory(
    location_id: Optional[int] = Query(None, description="Filter by warehouse location ID"),
    low_stock_only: bool = Query(False, description="Filter to items at or below reorder threshold"),
    search: Optional[str] = Query(None, description="Search by variant SKU or product name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemListResponse:
    """Retrieve paginated inventory levels across variants and locations."""
    offset = (page - 1) * page_size
    items, total = await list_inventory_items(
        db,
        location_id=location_id,
        low_stock_only=low_stock_only,
        search=search,
        limit=page_size,
        offset=offset,
    )
    return InventoryItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_inventory_router.get(
    "/low-stock",
    response_model=InventoryItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: List Low Stock Items",
)
async def list_low_stock(
    location_id: Optional[int] = Query(None, description="Filter by warehouse location ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemListResponse:
    """Convenience endpoint returning all inventory items at or below their reorder threshold."""
    offset = (page - 1) * page_size
    items, total = await list_inventory_items(
        db,
        location_id=location_id,
        low_stock_only=True,
        limit=page_size,
        offset=offset,
    )
    return InventoryItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_inventory_router.get(
    "/low-stock-report",
    response_model=LowStockReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Get Actionable Low Stock Deficit Report",
)
async def get_low_stock_report_endpoint(
    location_id: Optional[int] = Query(None, description="Filter by warehouse location ID"),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> LowStockReportResponse:
    """Actionable inventory replenishment report calculating real-time deficits against reorder thresholds."""
    return await get_low_stock_report(db, location_id=location_id)


@admin_inventory_router.post(
    "/bulk-adjust",
    response_model=BulkStockAdjustmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Bulk Adjust Stock Levels",
)
async def bulk_adjust_stock_endpoint(
    req: BulkStockAdjustmentRequest,
    current_user: User = Depends(require_permission("inventory.adjust")),
    db: AsyncSession = Depends(get_db),
) -> BulkStockAdjustmentResponse:
    """Atomic bulk inventory adjustment across multiple SKUs with audit logging."""
    return await bulk_adjust_stock(db, request=req, actor_user=current_user)


@admin_inventory_router.post(
    "/adjust",
    response_model=StockOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Execute Manual Stock Adjustment",
)
async def adjust_stock_endpoint(
    req: StockAdjustmentRequest,
    current_user: User = Depends(require_permission("inventory.adjust")),
    db: AsyncSession = Depends(get_db),
) -> StockOperationResponse:
    """
    Adjust physical stock levels with mandatory reason tracking.
    Enforces non-negative stock and updates catalog availability in real time.
    """
    item, movement = await adjust_stock(db, req, actor_user=current_user)
    # Query enriched view
    items, _ = await list_inventory_items(db, location_id=item.location_id, limit=100)
    enriched_item = next((i for i in items if i.id == item.id), None)
    if not enriched_item:
        enriched_item = InventoryItemResponse(
            id=item.id,
            variant_id=item.variant_id,
            location_id=item.location_id,
            quantity_on_hand=item.quantity_on_hand,
            quantity_reserved=item.quantity_reserved,
            quantity_available=item.quantity_available,
            reorder_threshold=item.reorder_threshold,
            is_low_stock=item.is_low_stock,
            updated_at=item.updated_at,
        )

    movement_res = InventoryMovementResponse(
        id=movement.id,
        variant_id=movement.variant_id,
        location_id=movement.location_id,
        movement_type=movement.movement_type,
        quantity_delta=movement.quantity_delta,
        quantity_on_hand_before=movement.quantity_on_hand_before,
        quantity_on_hand_after=movement.quantity_on_hand_after,
        quantity_reserved_before=movement.quantity_reserved_before,
        quantity_reserved_after=movement.quantity_reserved_after,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        reason_notes=movement.reason_notes,
        created_by_user_id=movement.created_by_user_id,
        created_at=movement.created_at,
    )
    return StockOperationResponse(item=enriched_item, movement=movement_res)


@admin_inventory_router.post(
    "/reserve",
    response_model=StockOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Reserve Stock Units",
)
async def reserve_stock_endpoint(
    req: StockReservationRequest,
    current_user: User = Depends(require_permission("inventory.adjust")),
    db: AsyncSession = Depends(get_db),
) -> StockOperationResponse:
    """Reserve available stock units for active checkout or order fulfillment foundation."""
    item, movement = await reserve_stock(db, req, actor_user=current_user)
    items, _ = await list_inventory_items(db, location_id=item.location_id, limit=100)
    enriched_item = next((i for i in items if i.id == item.id), None)
    if not enriched_item:
        enriched_item = InventoryItemResponse(
            id=item.id,
            variant_id=item.variant_id,
            location_id=item.location_id,
            quantity_on_hand=item.quantity_on_hand,
            quantity_reserved=item.quantity_reserved,
            quantity_available=item.quantity_available,
            reorder_threshold=item.reorder_threshold,
            is_low_stock=item.is_low_stock,
            updated_at=item.updated_at,
        )

    movement_res = InventoryMovementResponse(
        id=movement.id,
        variant_id=movement.variant_id,
        location_id=movement.location_id,
        movement_type=movement.movement_type,
        quantity_delta=movement.quantity_delta,
        quantity_on_hand_before=movement.quantity_on_hand_before,
        quantity_on_hand_after=movement.quantity_on_hand_after,
        quantity_reserved_before=movement.quantity_reserved_before,
        quantity_reserved_after=movement.quantity_reserved_after,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        reason_notes=movement.reason_notes,
        created_by_user_id=movement.created_by_user_id,
        created_at=movement.created_at,
    )
    return StockOperationResponse(item=enriched_item, movement=movement_res)


@admin_inventory_router.post(
    "/release",
    response_model=StockOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Release Reserved Stock",
)
async def release_stock_endpoint(
    req: StockReleaseRequest,
    current_user: User = Depends(require_permission("inventory.adjust")),
    db: AsyncSession = Depends(get_db),
) -> StockOperationResponse:
    """Release reserved stock back to available pool upon checkout cancellation or expiration."""
    item, movement = await release_stock(db, req, actor_user=current_user)
    items, _ = await list_inventory_items(db, location_id=item.location_id, limit=100)
    enriched_item = next((i for i in items if i.id == item.id), None)
    if not enriched_item:
        enriched_item = InventoryItemResponse(
            id=item.id,
            variant_id=item.variant_id,
            location_id=item.location_id,
            quantity_on_hand=item.quantity_on_hand,
            quantity_reserved=item.quantity_reserved,
            quantity_available=item.quantity_available,
            reorder_threshold=item.reorder_threshold,
            is_low_stock=item.is_low_stock,
            updated_at=item.updated_at,
        )

    movement_res = InventoryMovementResponse(
        id=movement.id,
        variant_id=movement.variant_id,
        location_id=movement.location_id,
        movement_type=movement.movement_type,
        quantity_delta=movement.quantity_delta,
        quantity_on_hand_before=movement.quantity_on_hand_before,
        quantity_on_hand_after=movement.quantity_on_hand_after,
        quantity_reserved_before=movement.quantity_reserved_before,
        quantity_reserved_after=movement.quantity_reserved_after,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        reason_notes=movement.reason_notes,
        created_by_user_id=movement.created_by_user_id,
        created_at=movement.created_at,
    )
    return StockOperationResponse(item=enriched_item, movement=movement_res)


@admin_inventory_router.patch(
    "/variants/{variant_id}/locations/{location_id}/threshold",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Reorder Threshold",
)
async def update_threshold_endpoint(
    variant_id: int,
    location_id: int,
    req: StockThresholdUpdateRequest,
    current_user: User = Depends(require_permission("inventory.adjust")),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemResponse:
    """Update replenishment alert threshold for a specific variant and location."""
    item = await update_reorder_threshold(
        db,
        variant_id=variant_id,
        location_id=location_id,
        threshold=req.reorder_threshold,
        actor_user=current_user,
    )
    items, _ = await list_inventory_items(db, location_id=location_id, limit=100)
    enriched_item = next((i for i in items if i.id == item.id), None)
    if not enriched_item:
        enriched_item = InventoryItemResponse(
            id=item.id,
            variant_id=item.variant_id,
            location_id=item.location_id,
            quantity_on_hand=item.quantity_on_hand,
            quantity_reserved=item.quantity_reserved,
            quantity_available=item.quantity_available,
            reorder_threshold=item.reorder_threshold,
            is_low_stock=item.is_low_stock,
            updated_at=item.updated_at,
        )
    return enriched_item


@admin_inventory_router.get(
    "/movements",
    response_model=InventoryMovementListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: List Inventory Movement Ledger",
)
async def list_movements_endpoint(
    variant_id: Optional[int] = Query(None, description="Filter by variant ID"),
    location_id: Optional[int] = Query(None, description="Filter by warehouse location ID"),
    movement_type: Optional[str] = Query(None, description="Filter by movement type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> InventoryMovementListResponse:
    """Retrieve immutable chronological audit trail of all inventory events."""
    offset = (page - 1) * page_size
    movements, total = await list_inventory_movements(
        db,
        variant_id=variant_id,
        location_id=location_id,
        movement_type=movement_type,
        limit=page_size,
        offset=offset,
    )
    return InventoryMovementListResponse(
        movements=movements,
        total=total,
        page=page,
        page_size=page_size,
    )
