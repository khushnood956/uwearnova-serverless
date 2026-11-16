"""
Staff Operations Pydantic Schemas (Module M20)
Defines request/response contracts for role-filtered work queues,
task assignment, order fulfillment processing, stock operations,
and customer support ticket handling.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------
# Work Queues Summary / Staff Dashboard
# ---------------------------------------------------------

class StaffDashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    staff_user_id: int
    email: str
    roles: List[str]
    permissions: List[str]
    assigned_tasks_count: int
    orders_queue_count: Optional[int] = None
    fulfillment_queue_count: Optional[int] = None
    inventory_low_stock_count: Optional[int] = None
    returns_queue_count: Optional[int] = None
    support_tickets_queue_count: Optional[int] = None


# ---------------------------------------------------------
# Work Queues Item Schemas
# ---------------------------------------------------------

class StaffOrderQueueItem(BaseModel):
    order_id: int
    order_number: str
    status: str
    payment_status: str
    payment_method: str
    fulfillment_status: str
    total_amount: Decimal
    currency: str
    item_count: int
    customer_email: str
    customer_name: str
    customer_city: str
    created_at: datetime
    operational_stage: str


class StaffOrderQueueResponse(BaseModel):
    items: List[StaffOrderQueueItem]
    total: int
    page: int
    page_size: int


class StaffFulfillmentQueueItem(BaseModel):
    shipment_id: int
    shipment_number: str
    order_id: int
    order_number: str
    courier_code: str
    status: str
    item_count: int
    shipping_city: str
    created_at: datetime
    tracking_number: Optional[str] = None


class StaffFulfillmentQueueResponse(BaseModel):
    items: List[StaffFulfillmentQueueItem]
    total: int
    page: int
    page_size: int


class StaffInventoryQueueItem(BaseModel):
    variant_id: int
    sku: str
    product_id: int
    product_title: str
    location_id: int
    location_name: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    reorder_threshold: int
    deficit: int


class StaffInventoryQueueResponse(BaseModel):
    items: List[StaffInventoryQueueItem]
    total: int
    page: int
    page_size: int


class StaffReturnQueueItem(BaseModel):
    request_id: int
    request_number: str
    order_id: int
    order_number: str
    status: str
    request_type: str
    item_count: int
    created_at: datetime
    stage: str


class StaffReturnQueueResponse(BaseModel):
    items: List[StaffReturnQueueItem]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------
# Support Tickets Schemas
# ---------------------------------------------------------

class SupportTicketCreateRequest(BaseModel):
    customer_email: EmailStr
    customer_name: str = Field(..., min_length=2, max_length=255)
    order_id: Optional[int] = None
    subject: str = Field(..., min_length=3, max_length=255)
    category: str = Field(default="general", max_length=64)
    priority: str = Field(default="normal", max_length=32)
    message: str = Field(..., min_length=2)


class SupportTicketMessageCreateRequest(BaseModel):
    message: str = Field(..., min_length=1)
    is_internal_note: bool = False


class SupportTicketStatusUpdateRequest(BaseModel):
    status: str = Field(..., max_length=32)
    resolution_notes: Optional[str] = None


class SupportTicketAssignRequest(BaseModel):
    staff_user_id: int


class SupportTicketMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    sender_user_id: Optional[int] = None
    sender_type: str
    sender_name: str
    message: str
    is_internal_note: bool
    created_at: datetime


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    customer_id: Optional[int] = None
    customer_email: str
    customer_name: str
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    subject: str
    category: str
    priority: str
    status: str
    assigned_staff_id: Optional[int] = None
    assigned_staff_email: Optional[str] = None
    assigned_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    messages: List[SupportTicketMessageResponse] = []


class SupportTicketListResponse(BaseModel):
    items: List[SupportTicketResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------
# Staff Tasks Schemas
# ---------------------------------------------------------

class StaffTaskCreateRequest(BaseModel):
    task_type: str = Field(..., max_length=64)
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    priority: str = Field(default="normal", max_length=32)
    assigned_staff_id: Optional[int] = None
    order_id: Optional[int] = None
    shipment_id: Optional[int] = None
    return_request_id: Optional[int] = None
    support_ticket_id: Optional[int] = None
    due_date: Optional[datetime] = None


class StaffTaskAssignRequest(BaseModel):
    staff_user_id: int


class StaffTaskStatusUpdateRequest(BaseModel):
    status: str = Field(..., max_length=32)
    resolution_notes: Optional[str] = None


class StaffTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_number: str
    task_type: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assigned_staff_id: Optional[int] = None
    assigned_staff_email: Optional[str] = None
    created_by_user_id: Optional[int] = None
    order_id: Optional[int] = None
    shipment_id: Optional[int] = None
    return_request_id: Optional[int] = None
    support_ticket_id: Optional[int] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StaffTaskListResponse(BaseModel):
    items: List[StaffTaskResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------
# Operational Processing Requests
# ---------------------------------------------------------

class StaffOrderProcessRequest(BaseModel):
    notes: Optional[str] = None


class StaffFulfillmentPackRequest(BaseModel):
    package_weight_kg: Optional[Decimal] = None
    package_dimensions: Optional[str] = None
    notes: Optional[str] = None


class StaffFulfillmentDispatchRequest(BaseModel):
    tracking_number: str = Field(..., min_length=3, max_length=128)
    courier_code: Optional[str] = None
    notes: Optional[str] = None


class StaffStockReceiveRequest(BaseModel):
    variant_id: int
    location_id: int
    quantity: int = Field(..., gt=0)
    batch_reference: Optional[str] = None
    notes: Optional[str] = None


class StaffCycleCountRequest(BaseModel):
    variant_id: int
    location_id: int
    actual_quantity: int = Field(..., ge=0)
    reason: str = Field(..., min_length=3, max_length=255)
