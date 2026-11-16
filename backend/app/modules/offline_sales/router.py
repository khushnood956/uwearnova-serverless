"""
Offline Sales & Point of Sale (POS) Router
Provides API endpoints to record walk-in shop sales, view receipts, and void transactions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.offline_sales.schemas import (
    OfflineSaleCreate,
    OfflineSaleResponse,
    OfflineSalesListResponse,
)
from app.modules.offline_sales.service import (
    create_offline_sale,
    get_offline_sale,
    list_offline_sales,
    void_offline_sale,
)
from app.modules.rbac.dependencies import require_permission

admin_offline_sales_router = APIRouter(
    prefix="/admin/offline-sales",
    tags=["Admin: Offline Sales & POS"],
)


@admin_offline_sales_router.post(
    "",
    response_model=OfflineSaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record New Offline / Shop Sale",
)
async def create_offline_sale_endpoint(
    data: OfflineSaleCreate,
    current_user: User = Depends(require_permission("orders.update")),
    db: AsyncSession = Depends(get_db),
) -> OfflineSaleResponse:
    """
    Rings up an offline/walk-in purchase on the boutique floor.
    Immediately reserves and deducts SKU inventory, records stock movement, and generates a POS receipt.
    """
    sale = await create_offline_sale(db, data, actor_user=current_user)
    return OfflineSaleResponse.model_validate(sale)


@admin_offline_sales_router.get(
    "",
    response_model=OfflineSalesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Offline Sales Transactions & Analytics",
)
async def list_offline_sales_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search receipt number, customer name, or phone"),
    payment_method: Optional[str] = Query(None, description="Filter by tender (cash, pos_card, bank_transfer)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (completed, voided)"),
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> OfflineSalesListResponse:
    """
    Returns a paginated log of physical store sales along with aggregated financial metrics.
    """
    items, total, summary = await list_offline_sales(
        db,
        limit=limit,
        offset=offset,
        search=search,
        payment_method=payment_method,
        status=status_filter,
    )
    return OfflineSalesListResponse(
        items=[OfflineSaleResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        summary=summary,
    )


@admin_offline_sales_router.get(
    "/{sale_id}",
    response_model=OfflineSaleResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Offline Sale Receipt by ID",
)
async def get_offline_sale_endpoint(
    sale_id: int,
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> OfflineSaleResponse:
    """Retrieve full offline sale details and line item breakdown."""
    sale = await get_offline_sale(db, sale_id)
    return OfflineSaleResponse.model_validate(sale)


@admin_offline_sales_router.post(
    "/{sale_id}/void",
    response_model=OfflineSaleResponse,
    status_code=status.HTTP_200_OK,
    summary="Void Offline Sale and Restore Inventory",
)
async def void_offline_sale_endpoint(
    sale_id: int,
    current_user: User = Depends(require_permission("orders.update")),
    db: AsyncSession = Depends(get_db),
) -> OfflineSaleResponse:
    """
    Voids an offline sale due to register mistake or immediate return, restoring stock counts.
    """
    sale = await void_offline_sale(db, sale_id, actor_user=current_user)
    return OfflineSaleResponse.model_validate(sale)
