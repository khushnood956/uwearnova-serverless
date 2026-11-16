"""
Reports and Analytics Service (Module M22)
Implements indexed SQL aggregations for store performance, financial breakdowns,
inventory warnings, and customer analytics.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    and_,
    case,
    desc,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.auth.models import User
from app.modules.catalog.models import Product, ProductVariant
from app.modules.inventory.models import InventoryItem, InventoryLocation
from app.modules.orders.models import Order, OrderItem
from app.modules.payments.models import Payment, Refund
from app.modules.reports.schemas import (
    BestSellingItem,
    BestSellersResponse,
    CodReconciliationMetrics,
    CustomerMetricsSummary,
    CustomerReportResponse,
    FinancialSummary,
    InventoryHealthSummary,
    InventoryReportItem,
    InventoryReportResponse,
    OrderCountsSummary,
    PaymentMethodBreakdown,
    PaymentStatusBreakdown,
    PaymentsReportResponse,
    ReportsOverviewResponse,
    ReturnStatusCount,
    ReturnTypeCount,
    ReturnsRefundsReportResponse,
    SalesTimeSeriesPoint,
    SalesTrendResponse,
    TopCustomerItem,
)
from app.modules.returns.models import ReturnRequest


# ---------------------------------------------------------------------------
# 1. Overview & Financial Summary
# ---------------------------------------------------------------------------

async def get_reports_overview(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> ReportsOverviewResponse:
    """
    Compile comprehensive store reporting overview.
    Clearly distinguishes gross order value, recognized revenue, collected payments, and outstanding COD.
    """
    order_filters = []
    if date_from:
        order_filters.append(Order.created_at >= date_from)
    if date_to:
        order_filters.append(Order.created_at <= date_to)

    # 1. Order Status & Value Aggregation
    order_stmt = select(
        Order.status,
        func.count(Order.id).label("status_count"),
        func.coalesce(func.sum(Order.grand_total), 0).label("status_total"),
        func.coalesce(func.sum(Order.discount_total), 0).label("status_discount"),
    )
    if order_filters:
        order_stmt = order_stmt.where(and_(*order_filters))
    order_stmt = order_stmt.group_by(Order.status)
    order_results = (await db.execute(order_stmt)).all()

    total_orders = 0
    completed_orders = 0
    pending_orders = 0
    cancelled_orders = 0
    returned_orders = 0
    gross_order_value = Decimal("0.00")
    total_discounts = Decimal("0.00")
    delivered_revenue = Decimal("0.00")

    pending_statuses = {"pending_confirmation", "confirmed", "processing", "packed", "shipped"}
    returned_statuses = {"return_requested", "returned", "refunded"}

    for row in order_results:
        s_name, s_count, s_total, s_disc = row[0], row[1], Decimal(str(row[2])), Decimal(str(row[3]))
        total_orders += s_count

        if s_name == "cancelled":
            cancelled_orders += s_count
        else:
            gross_order_value += s_total
            total_discounts += s_disc

        if s_name == "delivered":
            completed_orders += s_count
            delivered_revenue += s_total
        elif s_name in pending_statuses:
            pending_orders += s_count
        elif s_name in returned_statuses:
            returned_orders += s_count

    non_cancelled_count = total_orders - cancelled_orders
    average_order_value = (
        (gross_order_value / Decimal(non_cancelled_count)).quantize(Decimal("0.01"))
        if non_cancelled_count > 0
        else Decimal("0.00")
    )

    # 2. Refunds Aggregation
    refund_filters = [Refund.status == "completed"]
    if date_from:
        refund_filters.append(Refund.created_at >= date_from)
    if date_to:
        refund_filters.append(Refund.created_at <= date_to)

    refund_stmt = select(
        func.coalesce(func.sum(Refund.amount), 0),
        func.count(Refund.id),
    ).where(and_(*refund_filters))
    refund_res = (await db.execute(refund_stmt)).first()
    total_refunded = Decimal(str(refund_res[0])) if refund_res else Decimal("0.00")

    # Recognized Revenue = Delivered orders grand_total minus completed refunds
    recognized_revenue = max(Decimal("0.00"), delivered_revenue - total_refunded)
    net_sales = max(Decimal("0.00"), gross_order_value - total_refunded)

    # 3. Payments Aggregation: Collected Payments & Outstanding COD
    payment_filters = []
    if date_from:
        payment_filters.append(Payment.created_at >= date_from)
    if date_to:
        payment_filters.append(Payment.created_at <= date_to)

    collected_stmt = select(
        func.coalesce(func.sum(Payment.amount_collected), 0)
    )
    if payment_filters:
        collected_stmt = collected_stmt.where(and_(*payment_filters))
    collected_res = (await db.execute(collected_stmt)).scalar()
    collected_payments = Decimal(str(collected_res or 0))

    # Outstanding COD: Active COD payments not yet settled/collected
    cod_outstanding_stmt = select(
        func.coalesce(func.sum(Payment.amount_outstanding), 0)
    ).where(
        Payment.payment_method == "cod",
        Payment.status.in_(["pending", "confirmed", "dispatched"]),
    )
    cod_out_res = (await db.execute(cod_outstanding_stmt)).scalar()
    outstanding_cod = Decimal(str(cod_out_res or 0))

    # 4. Inventory Health Aggregates
    inv_stmt = select(
        func.count(InventoryItem.id),
        func.coalesce(func.sum(InventoryItem.quantity_on_hand), 0),
        func.coalesce(func.sum(InventoryItem.quantity_reserved), 0),
    )
    inv_res = (await db.execute(inv_stmt)).first()
    total_skus = inv_res[0] if inv_res else 0
    total_units_on_hand = int(inv_res[1] or 0) if inv_res else 0
    total_units_reserved = int(inv_res[2] or 0) if inv_res else 0
    total_units_available = max(0, total_units_on_hand - total_units_reserved)

    # Low-stock / out-of-stock counts
    all_inv_items = (await db.execute(select(InventoryItem))).scalars().all()
    low_stock_variant_count = sum(1 for it in all_inv_items if it.is_low_stock)
    out_of_stock_variant_count = sum(1 for it in all_inv_items if it.quantity_available == 0)

    # 5. Customer Metrics
    customer_count_stmt = select(func.count(User.id)).where(User.user_type == "customer")
    total_registered_customers = (await db.execute(customer_count_stmt)).scalar() or 0

    new_cust_filters = [User.user_type == "customer"]
    if date_from:
        new_cust_filters.append(User.created_at >= date_from)
    if date_to:
        new_cust_filters.append(User.created_at <= date_to)
    new_customers_in_period = (
        await db.execute(select(func.count(User.id)).where(and_(*new_cust_filters)))
    ).scalar() or 0

    guest_orders_stmt = select(func.count(Order.id)).where(
        Order.user_id.is_(None),
        Order.status != "cancelled",
    )
    if order_filters:
        guest_orders_stmt = guest_orders_stmt.where(and_(*order_filters))
    guest_orders_count = (await db.execute(guest_orders_stmt)).scalar() or 0

    reg_orders_stmt = select(func.count(Order.id)).where(
        Order.user_id.isnot(None),
        Order.status != "cancelled",
    )
    if order_filters:
        reg_orders_stmt = reg_orders_stmt.where(and_(*order_filters))
    registered_orders_count = (await db.execute(reg_orders_stmt)).scalar() or 0

    repeat_cust_stmt = (
        select(Order.user_id)
        .where(
            Order.user_id.isnot(None),
            Order.status != "cancelled",
        )
        .group_by(Order.user_id)
        .having(func.count(Order.id) > 1)
    )
    repeat_customers_count = len((await db.execute(repeat_cust_stmt)).all())

    return ReportsOverviewResponse(
        financials=FinancialSummary(
            currency_code="PKR",
            gross_order_value=gross_order_value,
            recognized_revenue=recognized_revenue,
            collected_payments=collected_payments,
            outstanding_cod=outstanding_cod,
            total_refunded=total_refunded,
            net_sales=net_sales,
        ),
        order_counts=OrderCountsSummary(
            total_orders=total_orders,
            completed_orders=completed_orders,
            pending_orders=pending_orders,
            cancelled_orders=cancelled_orders,
            returned_orders=returned_orders,
            average_order_value=average_order_value,
        ),
        inventory_health=InventoryHealthSummary(
            total_skus=total_skus,
            total_units_on_hand=total_units_on_hand,
            total_units_reserved=total_units_reserved,
            total_units_available=total_units_available,
            low_stock_variant_count=low_stock_variant_count,
            out_of_stock_variant_count=out_of_stock_variant_count,
        ),
        customer_metrics=CustomerMetricsSummary(
            total_registered_customers=total_registered_customers,
            new_customers_in_period=new_customers_in_period,
            guest_orders_count=guest_orders_count,
            registered_orders_count=registered_orders_count,
            repeat_customers_count=repeat_customers_count,
        ),
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# 2. Sales Trends & Time Series
# ---------------------------------------------------------------------------

async def get_sales_trends(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    interval: str = "day",
) -> SalesTrendResponse:
    """
    Compute daily/bucketed time-series sales trends with gross sales, discounts,
    shipping revenue, and cancellation counts.
    """
    filters = []
    if date_from:
        filters.append(Order.created_at >= date_from)
    if date_to:
        filters.append(Order.created_at <= date_to)

    date_expr = func.date(Order.created_at)

    stmt = (
        select(
            date_expr.label("bucket_date"),
            func.count(Order.id).label("total_orders"),
            func.coalesce(
                func.sum(case((Order.status != "cancelled", Order.grand_total), else_=0)), 0
            ).label("gross_sales"),
            func.coalesce(
                func.sum(case((Order.status != "cancelled", Order.discount_total), else_=0)), 0
            ).label("discounts"),
            func.coalesce(
                func.sum(case((Order.status != "cancelled", Order.shipping_total), else_=0)), 0
            ).label("shipping_charges"),
            func.coalesce(
                func.sum(case((Order.status == "cancelled", 1), else_=0)), 0
            ).label("cancelled_count"),
        )
    )
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.group_by(date_expr).order_by(date_expr.asc())

    rows = (await db.execute(stmt)).all()

    points: List[SalesTimeSeriesPoint] = []
    total_gross = Decimal("0.00")
    total_net = Decimal("0.00")
    total_disc = Decimal("0.00")
    total_ship = Decimal("0.00")
    total_orders = 0

    for r in rows:
        b_date = str(r[0])
        cnt = int(r[1])
        gross = Decimal(str(r[2]))
        disc = Decimal(str(r[3]))
        ship = Decimal(str(r[4]))
        canc = int(r[5])
        net = max(Decimal("0.00"), gross - disc)

        total_orders += cnt
        total_gross += gross
        total_net += net
        total_disc += disc
        total_ship += ship

        points.append(
            SalesTimeSeriesPoint(
                date=b_date,
                order_count=cnt,
                gross_sales=gross,
                discounts=disc,
                shipping_charges=ship,
                net_sales=net,
                cancelled_count=canc,
            )
        )

    return SalesTrendResponse(
        interval=interval,
        currency_code="PKR",
        total_gross_sales=total_gross,
        total_net_sales=total_net,
        total_orders=total_orders,
        total_discounts=total_disc,
        total_shipping_charges=total_ship,
        points=points,
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# 3. Payments & COD Breakdown
# ---------------------------------------------------------------------------

async def get_payments_report(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> PaymentsReportResponse:
    """
    Break down payments by method and lifecycle status, including detailed COD
    reconciliation metrics.
    """
    filters = []
    if date_from:
        filters.append(Payment.created_at >= date_from)
    if date_to:
        filters.append(Payment.created_at <= date_to)

    # 1. By Method Breakdown
    method_stmt = select(
        Payment.payment_method,
        func.count(Payment.id).label("txn_count"),
        func.coalesce(func.sum(Payment.amount), 0).label("tot_amt"),
        func.coalesce(func.sum(Payment.amount_collected), 0).label("col_amt"),
        func.coalesce(func.sum(Payment.amount_outstanding), 0).label("out_amt"),
    )
    if filters:
        method_stmt = method_stmt.where(and_(*filters))
    method_stmt = method_stmt.group_by(Payment.payment_method)
    method_rows = (await db.execute(method_stmt)).all()

    by_method: List[PaymentMethodBreakdown] = []
    total_payments_count = 0
    total_amount = Decimal("0.00")
    total_collected = Decimal("0.00")
    total_outstanding = Decimal("0.00")

    for r in method_rows:
        pm, count, amt, col, out = r[0], int(r[1]), Decimal(str(r[2])), Decimal(str(r[3])), Decimal(str(r[4]))
        total_payments_count += count
        total_amount += amt
        total_collected += col
        total_outstanding += out
        by_method.append(
            PaymentMethodBreakdown(
                payment_method=pm,
                transaction_count=count,
                total_amount=amt,
                collected_amount=col,
                outstanding_amount=out,
            )
        )

    # 2. By Status Breakdown
    status_stmt = select(
        Payment.status,
        func.count(Payment.id).label("stat_count"),
        func.coalesce(func.sum(Payment.amount), 0).label("stat_amt"),
    )
    if filters:
        status_stmt = status_stmt.where(and_(*filters))
    status_stmt = status_stmt.group_by(Payment.status)
    status_rows = (await db.execute(status_stmt)).all()

    by_status: List[PaymentStatusBreakdown] = [
        PaymentStatusBreakdown(
            status=r[0],
            count=int(r[1]),
            total_amount=Decimal(str(r[2])),
        )
        for r in status_rows
    ]

    # 3. COD Detailed Metrics
    cod_filters = [Payment.payment_method == "cod"]
    if filters:
        cod_filters.extend(filters)

    cod_stmt = select(
        func.count(Payment.id),
        func.coalesce(func.sum(Payment.amount), 0),
        func.coalesce(func.sum(Payment.amount_collected), 0),
        func.coalesce(func.sum(Payment.amount_outstanding), 0),
        func.coalesce(
            func.sum(case((Payment.status == "reconciled", Payment.amount), else_=0)), 0
        ),
        func.coalesce(
            func.sum(
                case((Payment.status == "collected", Payment.amount_collected), else_=0)
            ),
            0,
        ),
    ).where(and_(*cod_filters))
    cod_row = (await db.execute(cod_stmt)).first()

    cod_metrics = CodReconciliationMetrics(
        total_cod_orders=int(cod_row[0] or 0),
        cod_gross_amount=Decimal(str(cod_row[1] or 0)),
        cod_collected_amount=Decimal(str(cod_row[2] or 0)),
        cod_outstanding_amount=Decimal(str(cod_row[3] or 0)),
        cod_reconciled_amount=Decimal(str(cod_row[4] or 0)),
        cod_pending_remittance_amount=Decimal(str(cod_row[5] or 0)),
    )

    return PaymentsReportResponse(
        currency_code="PKR",
        total_payments_count=total_payments_count,
        total_amount=total_amount,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        by_method=by_method,
        by_status=by_status,
        cod_reconciliation=cod_metrics,
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# 4. Best Selling Products
# ---------------------------------------------------------------------------

async def get_best_sellers(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 10,
) -> BestSellersResponse:
    """
    Return top-selling products and variants ranked by units sold and revenue.
    """
    filters = [Order.status != "cancelled"]
    if date_from:
        filters.append(Order.created_at >= date_from)
    if date_to:
        filters.append(Order.created_at <= date_to)

    stmt = (
        select(
            OrderItem.product_id,
            OrderItem.product_name_snapshot,
            OrderItem.sku_snapshot,
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.line_total).label("gross_revenue"),
            func.count(func.distinct(OrderItem.order_id)).label("order_count"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(and_(*filters))
        .group_by(
            OrderItem.product_id,
            OrderItem.product_name_snapshot,
            OrderItem.sku_snapshot,
        )
        .order_by(desc("units_sold"), desc("gross_revenue"))
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()

    items = [
        BestSellingItem(
            product_id=r[0],
            product_title=r[1],
            sku=r[2],
            units_sold=int(r[3]),
            gross_revenue=Decimal(str(r[4])),
            order_count=int(r[5]),
        )
        for r in rows
    ]

    return BestSellersResponse(
        items=items,
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# 5. Inventory Summaries & Low Stock
# ---------------------------------------------------------------------------

async def get_inventory_report(
    db: AsyncSession,
    low_stock_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> InventoryReportResponse:
    """
    Detailed inventory health report, reorder warnings, and valuation.
    """
    stmt = (
        select(InventoryItem)
        .options(
            joinedload(InventoryItem.variant).joinedload(ProductVariant.product),
            joinedload(InventoryItem.location),
        )
    )
    items = (await db.execute(stmt)).scalars().all()

    total_skus = len(items)
    total_on_hand = sum(it.quantity_on_hand for it in items)
    total_reserved = sum(it.quantity_reserved for it in items)
    total_available = sum(it.quantity_available for it in items)
    low_stock_count = sum(1 for it in items if it.is_low_stock)
    out_of_stock_count = sum(1 for it in items if it.quantity_available == 0)

    # Estimate inventory value based on variant base price
    estimated_inventory_value = Decimal("0.00")
    for it in items:
        if it.variant and it.variant.price:
            price = it.variant.price
        elif it.variant and it.variant.product and it.variant.product.price:
            price = it.variant.product.price
        else:
            price = Decimal("0.00")
        estimated_inventory_value += Decimal(it.quantity_available) * price

    # Filtering for response list
    selected_items = items
    if low_stock_only:
        selected_items = [it for it in selected_items if it.is_low_stock]

    selected_slice = selected_items[offset : offset + limit]

    report_items: List[InventoryReportItem] = []
    for it in selected_slice:
        var = it.variant
        prod = var.product if var else None
        loc = it.location

        report_items.append(
            InventoryReportItem(
                variant_id=it.variant_id,
                sku=var.sku if var else "UNKNOWN",
                product_title=prod.name if prod else "Unknown Product",
                size=var.size if var else "Standard",
                color=var.color_name if var else "Default",
                location_name=loc.name if loc else "Primary Location",
                quantity_on_hand=it.quantity_on_hand,
                quantity_reserved=it.quantity_reserved,
                quantity_available=it.quantity_available,
                reorder_threshold=it.reorder_threshold,
                is_low_stock=it.is_low_stock,
                is_out_of_stock=(it.quantity_available == 0),
            )
        )

    return InventoryReportResponse(
        total_skus=total_skus,
        total_units_on_hand=total_on_hand,
        total_units_reserved=total_reserved,
        total_units_available=total_available,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        estimated_inventory_value=estimated_inventory_value,
        items=report_items,
    )


# ---------------------------------------------------------------------------
# 6. Customer Statistics
# ---------------------------------------------------------------------------

async def get_customers_report(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> CustomerReportResponse:
    """
    Customer acquisition, repeat purchasing behavior, and top buyers.
    """
    total_reg = (
        await db.execute(select(func.count(User.id)).where(User.user_type == "customer"))
    ).scalar() or 0

    new_cust_filters = [User.user_type == "customer"]
    if date_from:
        new_cust_filters.append(User.created_at >= date_from)
    if date_to:
        new_cust_filters.append(User.created_at <= date_to)
    new_in_period = (
        await db.execute(select(func.count(User.id)).where(and_(*new_cust_filters)))
    ).scalar() or 0

    order_filters = [Order.status != "cancelled"]
    if date_from:
        order_filters.append(Order.created_at >= date_from)
    if date_to:
        order_filters.append(Order.created_at <= date_to)

    guest_orders_count = (
        await db.execute(
            select(func.count(Order.id)).where(Order.user_id.is_(None), and_(*order_filters))
        )
    ).scalar() or 0

    registered_orders_count = (
        await db.execute(
            select(func.count(Order.id)).where(Order.user_id.isnot(None), and_(*order_filters))
        )
    ).scalar() or 0

    # Repeat buyers vs single buyers
    user_orders_stmt = (
        select(Order.user_id, func.count(Order.id))
        .where(Order.user_id.isnot(None), and_(*order_filters))
        .group_by(Order.user_id)
    )
    user_order_counts = (await db.execute(user_orders_stmt)).all()

    repeat_buyer_count = sum(1 for row in user_order_counts if row[1] > 1)
    single_order_buyer_count = sum(1 for row in user_order_counts if row[1] == 1)

    # Top customers by monetary spend
    top_stmt = (
        select(
            Order.user_id,
            Order.customer_email,
            Order.customer_name,
            func.count(Order.id).label("ord_cnt"),
            func.sum(Order.grand_total).label("tot_spd"),
        )
        .where(and_(*order_filters))
        .group_by(Order.user_id, Order.customer_email, Order.customer_name)
        .order_by(desc("tot_spd"))
        .limit(10)
    )
    top_rows = (await db.execute(top_stmt)).all()

    top_customers = [
        TopCustomerItem(
            user_id=r[0],
            customer_email=r[1],
            customer_name=r[2],
            order_count=int(r[3]),
            total_spend=Decimal(str(r[4])),
        )
        for r in top_rows
    ]

    return CustomerReportResponse(
        total_registered_customers=total_reg,
        new_customers_in_period=new_in_period,
        guest_orders_count=guest_orders_count,
        registered_orders_count=registered_orders_count,
        repeat_buyer_count=repeat_buyer_count,
        single_order_buyer_count=single_order_buyer_count,
        top_customers=top_customers,
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# 7. Returns and Refunds Summary
# ---------------------------------------------------------------------------

async def get_returns_refunds_report(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> ReturnsRefundsReportResponse:
    """
    Returns volume, return rates, and processed/pending refund metrics.
    """
    ret_filters = []
    if date_from:
        ret_filters.append(ReturnRequest.created_at >= date_from)
    if date_to:
        ret_filters.append(ReturnRequest.created_at <= date_to)

    # By status
    status_stmt = select(
        ReturnRequest.status,
        func.count(ReturnRequest.id),
    )
    if ret_filters:
        status_stmt = status_stmt.where(and_(*ret_filters))
    status_stmt = status_stmt.group_by(ReturnRequest.status)
    status_rows = (await db.execute(status_stmt)).all()

    by_status = [
        ReturnStatusCount(status=r[0], count=int(r[1])) for r in status_rows
    ]
    total_return_requests = sum(s.count for s in by_status)

    # By request type
    type_stmt = select(
        ReturnRequest.request_type,
        func.count(ReturnRequest.id),
    )
    if ret_filters:
        type_stmt = type_stmt.where(and_(*ret_filters))
    type_stmt = type_stmt.group_by(ReturnRequest.request_type)
    type_rows = (await db.execute(type_stmt)).all()

    by_type = [
        ReturnTypeCount(request_type=r[0], count=int(r[1])) for r in type_rows
    ]

    # Return rate % based on orders placed in same date range
    order_filters = [Order.status != "cancelled"]
    if date_from:
        order_filters.append(Order.created_at >= date_from)
    if date_to:
        order_filters.append(Order.created_at <= date_to)
    total_orders = (
        await db.execute(select(func.count(Order.id)).where(and_(*order_filters)))
    ).scalar() or 0

    return_rate_percentage = (
        (Decimal(total_return_requests) / Decimal(total_orders) * Decimal(100)).quantize(
            Decimal("0.01")
        )
        if total_orders > 0
        else Decimal("0.00")
    )

    # Refunds breakdown
    ref_filters = []
    if date_from:
        ref_filters.append(Refund.created_at >= date_from)
    if date_to:
        ref_filters.append(Refund.created_at <= date_to)

    ref_stmt = select(
        Refund.status,
        func.count(Refund.id),
        func.coalesce(func.sum(Refund.amount), 0),
    )
    if ref_filters:
        ref_stmt = ref_stmt.where(and_(*ref_filters))
    ref_stmt = ref_stmt.group_by(Refund.status)
    ref_rows = (await db.execute(ref_stmt)).all()

    total_refunds_processed_count = 0
    total_refunds_processed_amount = Decimal("0.00")
    pending_refunds_count = 0
    pending_refunds_amount = Decimal("0.00")

    for r in ref_rows:
        stat, cnt, amt = r[0], int(r[1]), Decimal(str(r[2]))
        if stat == "completed":
            total_refunds_processed_count = cnt
            total_refunds_processed_amount = amt
        elif stat == "pending":
            pending_refunds_count = cnt
            pending_refunds_amount = amt

    return ReturnsRefundsReportResponse(
        currency_code="PKR",
        total_return_requests=total_return_requests,
        return_rate_percentage=return_rate_percentage,
        by_status=by_status,
        by_type=by_type,
        total_refunds_processed_count=total_refunds_processed_count,
        total_refunds_processed_amount=total_refunds_processed_amount,
        pending_refunds_count=pending_refunds_count,
        pending_refunds_amount=pending_refunds_amount,
        date_from=date_from,
        date_to=date_to,
    )
