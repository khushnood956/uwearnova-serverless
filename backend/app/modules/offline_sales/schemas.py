"""
Offline Sales Pydantic Schemas
Defines request and response payloads for POS walk-in transactions.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OfflineSaleItemCreate(BaseModel):
    variant_id: int = Field(..., description="ID of product variant SKU sold")
    quantity: int = Field(..., ge=1, description="Quantity of units sold")
    unit_price_override: Optional[Decimal] = Field(
        None,
        ge=Decimal("0.00"),
        description="Optional cashier price override (e.g. damaged box, clearance)",
    )


class OfflineSaleCreate(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=128, description="Client full name")
    customer_phone: Optional[str] = Field(None, max_length=32, description="Contact phone number")
    customer_email: Optional[str] = Field(None, max_length=255, description="Client email address")
    payment_method: str = Field(
        "cash",
        pattern="^(cash|pos_card|bank_transfer|other)$",
        description="Payment tender method",
    )
    discount_amount: Decimal = Field(
        Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Cash discount amount in PKR",
    )
    tax_amount: Decimal = Field(
        Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Tax or VAT amount in PKR",
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Cashier or register notes")
    items: List[OfflineSaleItemCreate] = Field(
        ...,
        min_length=1,
        description="List of product variants purchased",
    )


class OfflineSaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    product_id: int
    variant_id: int
    product_name: str
    sku: str
    variant_label: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OfflineSaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_number: str
    sale_date: datetime
    customer_name: Optional[str]
    customer_phone: Optional[str]
    customer_email: Optional[str]
    payment_method: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    notes: Optional[str]
    staff_id: Optional[int]
    staff_name: Optional[str]
    items: List[OfflineSaleItemResponse]
    created_at: datetime
    updated_at: datetime


class OfflineSaleSummaryStats(BaseModel):
    total_sales_count: int = 0
    total_revenue: Decimal = Decimal("0.00")
    total_units_sold: int = 0
    cash_revenue: Decimal = Decimal("0.00")
    card_revenue: Decimal = Decimal("0.00")


class OfflineSalesListResponse(BaseModel):
    items: List[OfflineSaleResponse]
    total: int
    limit: int
    offset: int
    summary: OfflineSaleSummaryStats
