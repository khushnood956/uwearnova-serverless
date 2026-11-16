"""
Returns, Exchanges, and Refunds API Schemas (Module M16)
Pydantic schemas for return request submission, staff policy review,
item quality inspection, inventory restock, and payment refund execution.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReturnItemCreateRequest(BaseModel):
    """Line item in a return or exchange request."""
    order_item_id: int
    quantity: int = Field(default=1, gt=0)
    reason: str = Field(..., description="Categorized reason code (e.g. size_fit, defective_garment, changed_mind)")
    customer_comments: Optional[str] = Field(default=None, max_length=500)
    exchange_variant_id: Optional[int] = Field(default=None, description="Target replacement variant ID for exchanges")


class ReturnRequestCreatePayload(BaseModel):
    """Customer payload to initiate an order return or doorstep exchange."""
    request_type: str = Field(default="return", description="'return' or 'exchange'")
    resolution_type: str = Field(default="refund", description="'refund', 'exchange', or 'store_credit'")
    refund_payout_method: Optional[str] = Field(
        default=None,
        description="Payout method: original_payment_method, bank_transfer, wallet_transfer, store_credit",
    )
    payout_account_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Beneficiary account details for manual COD refund (Bank name, IBAN, Account title)",
    )
    customer_notes: Optional[str] = Field(default=None, max_length=1000)
    items: List[ReturnItemCreateRequest] = Field(..., min_length=1)


class ReturnReviewRequest(BaseModel):
    """Staff approval or rejection decision."""
    decision: str = Field(..., description="'approved' or 'rejected'")
    rejection_reason: Optional[str] = Field(default=None, max_length=255, description="Required if rejected")
    staff_notes: Optional[str] = Field(default=None, max_length=1000)


class ReturnReceiveRequest(BaseModel):
    """Staff marks parcel arrived at warehouse."""
    staff_notes: Optional[str] = Field(default=None, max_length=500)


class ReturnItemInspectionPayload(BaseModel):
    """Item-level quality assessment."""
    return_item_id: int
    inspection_status: str = Field(..., description="'passed' or 'failed'")
    restock_condition: str = Field(
        ...,
        description="'unopened', 'like_new', 'damaged', 'altered', 'missing_tags'",
    )
    restock_action: str = Field(
        ...,
        description="'restock_available', 'write_off', 'return_to_customer'",
    )
    inspector_notes: Optional[str] = Field(default=None, max_length=500)


class ReturnInspectionRequest(BaseModel):
    """Warehouse quality inspection assessment submission."""
    items: List[ReturnItemInspectionPayload] = Field(..., min_length=1)
    staff_notes: Optional[str] = Field(default=None, max_length=1000)


class ReturnRefundResolveRequest(BaseModel):
    """Execute refund resolution for inspected return."""
    refund_amount: Optional[Decimal] = Field(default=None, gt=0, description="Optional override of calculated refund amount")
    payout_method: Optional[str] = Field(
        default=None,
        description="Payout rail: original_payment_method, bank_transfer, wallet_transfer, store_credit",
    )
    payout_reference: Optional[str] = Field(
        default=None,
        description="Voucher reference, bank transfer transaction ID, or wallet transaction ID for manual COD refunds",
    )
    notes: Optional[str] = Field(default=None, max_length=1000)


class ReturnExchangeResolveRequest(BaseModel):
    """Execute replacement dispatch resolution for inspected exchange."""
    courier_code: str = Field(default="manual")
    dispatch_notes: Optional[str] = Field(default=None, max_length=1000)


# ==============================================================================
# Response Schemas
# ==============================================================================


class ReturnItemResponse(BaseModel):
    """Line item in return request response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    return_request_id: int
    order_item_id: int
    quantity: int
    reason: str
    customer_comments: Optional[str] = None
    exchange_variant_id: Optional[int] = None
    exchange_size: Optional[str] = None
    exchange_color: Optional[str] = None
    inspection_status: str
    restock_condition: Optional[str] = None
    restock_action: Optional[str] = None
    restocked_quantity: int
    inspector_notes: Optional[str] = None
    inspected_at: Optional[datetime] = None
    refund_amount: Decimal
    product_name_snapshot: str
    sku_snapshot: str
    size_snapshot: str
    color_snapshot: str
    unit_price: Decimal


class ReturnRequestResponse(BaseModel):
    """Complete return or exchange request response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_number: str
    order_id: int
    user_id: Optional[int] = None
    request_type: str
    status: str
    resolution_type: str
    refund_payout_method: Optional[str] = None
    customer_notes: Optional[str] = None
    staff_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    refund_id: Optional[int] = None
    replacement_order_id: Optional[int] = None
    total_refund_amount: Decimal
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    inspected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    items: List[ReturnItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ReturnRequestListResponse(BaseModel):
    """Paginated list of return requests."""
    items: List[ReturnRequestResponse]
    total: int
    page: int
    page_size: int
