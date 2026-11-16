"""
Payment and COD Workflow Schemas (Module M13)
Pydantic schemas for payment records, transaction ledgers, COD lifecycle operations,
collection recording, and courier remittance reconciliation.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PaymentTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    amount: Decimal
    currency_code: str
    collected_by: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    recorded_by_user_id: Optional[int] = None
    created_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    order_number: Optional[str] = None
    payment_method: str
    provider_code: str
    provider_reference: Optional[str] = None
    status: str
    currency_code: str
    amount: Decimal
    amount_collected: Decimal
    amount_outstanding: Decimal
    initiated_at: datetime
    confirmed_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    reconciled_at: Optional[datetime] = None
    reconciled_by_user_id: Optional[int] = None
    settlement_reference: Optional[str] = None
    notes: Optional[str] = None
    transactions: List[PaymentTransactionResponse] = []
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int
    page: int
    page_size: int


class CODConfirmationRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=500, description="Verification details (e.g. phone call confirmed)")


class CODDispatchRecordRequest(BaseModel):
    courier_code: str = Field(..., min_length=2, max_length=64, description="Courier provider code (e.g. blue_ex, tcs, leopards)")
    tracking_number: str = Field(..., min_length=3, max_length=128, description="Courier consignment number or AWB")
    notes: Optional[str] = Field(None, max_length=500)


class CODCollectionRecordRequest(BaseModel):
    amount_collected: Decimal = Field(..., gt=Decimal("0.00"), description="Monetary cash amount collected from customer in PKR")
    collected_by: Optional[str] = Field(None, max_length=128, description="Courier name or delivery agent")
    reference: Optional[str] = Field(None, max_length=255, description="Rider receipt number or courier delivery confirmation ref")
    notes: Optional[str] = Field(None, max_length=500)


class CODReconciliationRequest(BaseModel):
    settlement_reference: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Courier remittance advice number or bank deposit voucher reference",
    )
    notes: Optional[str] = Field(None, max_length=500, description="Audit reconciliation notes")


class CODCancellationRequest(BaseModel):
    reason: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Cancellation justification (e.g. customer refused confirmation, fake address, duplicate)",
    )
    notes: Optional[str] = Field(None, max_length=500)


# ===========================================================================
# Online Gateway Initiation & Callback Schemas (Module M14)
# ===========================================================================

class PaymentInitiateRequest(BaseModel):
    order_id: int = Field(..., description="Order ID to initiate payment for")
    provider_code: Optional[str] = Field(None, description="Optional target gateway (e.g. mock, safepay, payfast)")
    return_url: str = Field(default="http://localhost:3000/checkout/success", description="Success return URL")
    cancel_url: str = Field(default="http://localhost:3000/checkout", description="Cancel return URL")


class PaymentInitiateResponse(BaseModel):
    payment_id: int
    order_id: int
    order_number: str
    provider_code: str
    provider_reference: str
    redirect_url: Optional[str] = None
    client_token: Optional[str] = None
    status: str
    amount: Decimal
    currency_code: str


class PaymentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: Optional[int] = None
    provider_code: str
    provider_event_id: Optional[str] = None
    event_type: str
    signature_verified: bool
    processing_status: str
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


class PaymentEventListResponse(BaseModel):
    events: List[PaymentEventResponse]
    total: int
    page: int
    page_size: int


class RefundCreateRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Refund monetary amount in PKR")
    reason: str = Field(..., min_length=3, max_length=255, description="Reason for refund")
    notes: Optional[str] = Field(None, max_length=500)


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    payment_id: int
    refund_number: str
    amount: Decimal
    currency_code: str
    reason: str
    status: str
    provider_reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class RefundListResponse(BaseModel):
    refunds: List[RefundResponse]
    total: int
    page: int
    page_size: int
