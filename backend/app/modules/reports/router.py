"""
Reports and Analytics API Endpoints (Module M22)
Administrative read endpoints protected strictly by 'reports.read' permission.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.rbac.dependencies import require_permission
from app.modules.reports.schemas import (
    BestSellersResponse,
    CustomerReportResponse,
    InventoryReportResponse,
    PaymentsReportResponse,
    ReportsOverviewResponse,
    ReturnsRefundsReportResponse,
    SalesTrendResponse,
)
from app.modules.reports.service import (
    get_best_sellers,
    get_customers_report,
    get_inventory_report,
    get_payments_report,
    get_reports_overview,
    get_returns_refunds_report,
    get_sales_trends,
)

admin_reports_router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin: Reports & Analytics"],
    dependencies=[Depends(require_permission("reports.read"))],
)


@admin_reports_router.get(
    "/overview",
    response_model=ReportsOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Store Operational & Financial Overview",
)
async def get_overview_endpoint(
    date_from: Optional[datetime] = Query(None, description="Start date/time UTC"),
    date_to: Optional[datetime] = Query(None, description="End date/time UTC"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("reports.read")),
) -> ReportsOverviewResponse:
    """
    Get top-level store overview with financial metrics, order counts,
    inventory health, and customer acquisition.
    """
    return await get_reports_overview(db, date_from=date_from, date_to=date_to)


@admin_reports_router.get(
    "/sales",
    response_model=SalesTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Sales Performance & Time-Series Trends",
)
async def get_sales_endpoint(
    date_from: Optional[datetime] = Query(None, description="Start date/time UTC"),
    date_to: Optional[datetime] = Query(None, description="End date/time UTC"),
    interval: str = Query("day", description="Aggregation bucket interval: day, week, month"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("reports.read")),
) -> SalesTrendResponse:
    """
    Get daily/weekly time series of sales, discount deductions, shipping fees, and cancellations.
    """
    return await get_sales_trends(db, date_from=date_from, date_to=date_to, interval=interval)


@admin_reports_router.get(
    "/payments",
    response_model=PaymentsReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Payments Breakdown & COD Reconciliation",
)
async def get_payments_endpoint(
    date_from: Optional[datetime] = Query(None, description="Start date/time UTC"),
    date_to: Optional[datetime] = Query(None, description="End date/time UTC"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("reports.read")),
) -> PaymentsReportResponse:
    """
    Get payment method totals, lifecycle status counts, and COD cash outstanding vs settled.
    """
    return await get_payments_report(db, date_from=date_from, date_to=date_to)


@admin_reports_router.get(
    "/products/best-sellers",
    response_model=BestSellersResponse,
    status_code=status.HTTP_200_OK,
    summary="Top-Selling Products and SKUs",
)
async def get_best_sellers_endpoint(
    date_from: Optional[datetime] = Query(None, description="Start date/time UTC"),
    date_to: Optional[datetime] = Query(None, description="End date/time UTC"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("reports.read")),
) -> BestSellersResponse:
    """
    Get top selling catalog items ranked by units sold and gross revenue.
    """
    return await get_best_sellers(db, date_from=date_from, date_to=date_to, limit=limit)


@admin_reports_router.get(
    "/inventory",
    response_model=InventoryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Inventory Valuation & Low-Stock Alerts",
)
async def get_inventory_endpoint(
    low_stock_only: bool = Query(False, description="Filter solely for items at or below reorder threshold"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("reports.read")),
) -> InventoryReportResponse:
    """
    Get inventory valuation, total units available/reserved, and low-stock alerts across warehouses.
    """
    return await get_inventory_report(
        db, low_stock_only=low_stock_only, limit=limit, offset=offset
    )


@admin_reports_router.get(
    "/customers",
    response_model=CustomerReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Customer Acquisition & Retention Analytics",
)
async def get_customers_endpoint(
    date_from: Optional[datetime] = Query(None, description="Start date/time UTC"),
    date_to: Optional[datetime] = Query(None, description="End date/time UTC"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("reports.read")),
) -> CustomerReportResponse:
    """
    Get registered vs guest buyer behavior, repeat customer ratios, and top spenders.
    """
    return await get_customers_report(db, date_from=date_from, date_to=date_to)


@admin_reports_router.get(
    "/returns-refunds",
    response_model=ReturnsRefundsReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Returns & Refund Summary",
)
async def get_returns_refunds_endpoint(
    date_from: Optional[datetime] = Query(None, description="Start date/time UTC"),
    date_to: Optional[datetime] = Query(None, description="End date/time UTC"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("reports.read")),
) -> ReturnsRefundsReportResponse:
    """
    Get return volumes, reason/type breakdown, and completed vs pending refund amounts.
    """
    return await get_returns_refunds_report(db, date_from=date_from, date_to=date_to)
