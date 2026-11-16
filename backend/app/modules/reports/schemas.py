"""
Reports and Analytics Schemas (Module M22)
Pydantic contracts for financial summaries, sales trends, payment reconciliations,
inventory health, and customer statistics.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Overview & Financials
# ---------------------------------------------------------------------------

class FinancialSummary(BaseModel):
    currency_code: str = "PKR"
    gross_order_value: Decimal = Field(
        ...,
        description="Total monetary value of orders placed in period (excluding cancelled)",
    )
    recognized_revenue: Decimal = Field(
        ...,
        description="Monetary value of delivered/fulfilled orders minus completed refunds",
    )
    collected_payments: Decimal = Field(
        ...,
        description="Verified payments actually collected into accounts/cash drawer",
    )
    outstanding_cod: Decimal = Field(
        ...,
        description="Pending Cash on Delivery balance currently in transit or awaiting courier collection",
    )
    total_refunded: Decimal = Field(
        ...,
        description="Total monetary amount refunded to customers in period",
    )
    net_sales: Decimal = Field(
        ...,
        description="Gross order value minus discounts and processed refunds",
    )


class OrderCountsSummary(BaseModel):
    total_orders: int
    completed_orders: int
    pending_orders: int
    cancelled_orders: int
    returned_orders: int
    average_order_value: Decimal


class InventoryHealthSummary(BaseModel):
    total_skus: int
    total_units_on_hand: int
    total_units_reserved: int
    total_units_available: int
    low_stock_variant_count: int
    out_of_stock_variant_count: int


class CustomerMetricsSummary(BaseModel):
    total_registered_customers: int
    new_customers_in_period: int
    guest_orders_count: int
    registered_orders_count: int
    repeat_customers_count: int


class ReportsOverviewResponse(BaseModel):
    financials: FinancialSummary
    order_counts: OrderCountsSummary
    inventory_health: InventoryHealthSummary
    customer_metrics: CustomerMetricsSummary
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Sales Trends & Time Series
# ---------------------------------------------------------------------------

class SalesTimeSeriesPoint(BaseModel):
    date: str
    order_count: int
    gross_sales: Decimal
    discounts: Decimal
    shipping_charges: Decimal
    net_sales: Decimal
    cancelled_count: int


class SalesTrendResponse(BaseModel):
    interval: str
    currency_code: str = "PKR"
    total_gross_sales: Decimal
    total_net_sales: Decimal
    total_orders: int
    total_discounts: Decimal
    total_shipping_charges: Decimal
    points: List[SalesTimeSeriesPoint]
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Payment & COD Breakdowns
# ---------------------------------------------------------------------------

class PaymentMethodBreakdown(BaseModel):
    payment_method: str
    transaction_count: int
    total_amount: Decimal
    collected_amount: Decimal
    outstanding_amount: Decimal


class PaymentStatusBreakdown(BaseModel):
    status: str
    count: int
    total_amount: Decimal


class CodReconciliationMetrics(BaseModel):
    total_cod_orders: int
    cod_gross_amount: Decimal
    cod_collected_amount: Decimal
    cod_outstanding_amount: Decimal
    cod_reconciled_amount: Decimal
    cod_pending_remittance_amount: Decimal


class PaymentsReportResponse(BaseModel):
    currency_code: str = "PKR"
    total_payments_count: int
    total_amount: Decimal
    total_collected: Decimal
    total_outstanding: Decimal
    by_method: List[PaymentMethodBreakdown]
    by_status: List[PaymentStatusBreakdown]
    cod_reconciliation: CodReconciliationMetrics
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Best Selling Products
# ---------------------------------------------------------------------------

class BestSellingItem(BaseModel):
    product_id: Optional[int]
    product_title: str
    sku: str
    units_sold: int
    gross_revenue: Decimal
    order_count: int


class BestSellersResponse(BaseModel):
    items: List[BestSellingItem]
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Inventory Reports
# ---------------------------------------------------------------------------

class InventoryReportItem(BaseModel):
    variant_id: int
    sku: str
    product_title: str
    size: str
    color: str
    location_name: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    reorder_threshold: int
    is_low_stock: bool
    is_out_of_stock: bool


class InventoryReportResponse(BaseModel):
    total_skus: int
    total_units_on_hand: int
    total_units_reserved: int
    total_units_available: int
    low_stock_count: int
    out_of_stock_count: int
    estimated_inventory_value: Decimal
    items: List[InventoryReportItem]


# ---------------------------------------------------------------------------
# Customer Statistics
# ---------------------------------------------------------------------------

class TopCustomerItem(BaseModel):
    user_id: Optional[int]
    customer_email: str
    customer_name: str
    order_count: int
    total_spend: Decimal


class CustomerReportResponse(BaseModel):
    total_registered_customers: int
    new_customers_in_period: int
    guest_orders_count: int
    registered_orders_count: int
    repeat_buyer_count: int
    single_order_buyer_count: int
    top_customers: List[TopCustomerItem]
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Returns & Refunds Summary
# ---------------------------------------------------------------------------

class ReturnStatusCount(BaseModel):
    status: str
    count: int


class ReturnTypeCount(BaseModel):
    request_type: str
    count: int


class ReturnsRefundsReportResponse(BaseModel):
    currency_code: str = "PKR"
    total_return_requests: int
    return_rate_percentage: Decimal
    by_status: List[ReturnStatusCount]
    by_type: List[ReturnTypeCount]
    total_refunds_processed_count: int
    total_refunds_processed_amount: Decimal
    pending_refunds_count: int
    pending_refunds_amount: Decimal
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
