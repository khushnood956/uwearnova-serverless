"""
Fulfillment and Shipment Tracking Endpoints (Module M15)
Customer order tracking, staff warehouse parcel packing, carrier consignment allocation,
and fulfillment state machine transitions.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.models import User
from app.modules.fulfillment.schemas import (
    OrderTrackingTimelineResponse,
    ShipmentCreateRequest,
    ShipmentEventCreateRequest,
    ShipmentEventResponse,
    ShipmentListResponse,
    ShipmentResponse,
    ShipmentStatusUpdateRequest,
    ShipmentTrackingUpdateRequest,
)
from app.modules.fulfillment.service import (
    create_shipment_for_order,
    get_order_tracking_timeline,
    get_shipment_by_id,
    list_shipments,
    record_shipment_event,
    update_shipment_status,
    update_shipment_tracking,
)
from app.modules.rbac.dependencies import require_permission

public_tracking_router = APIRouter(prefix="/orders", tags=["Storefront: Order Tracking"])
customer_fulfillment_router = APIRouter(prefix="/customer/orders", tags=["Customer: Order Tracking"])
admin_fulfillment_router = APIRouter(prefix="/admin", tags=["Admin: Fulfillment & Logistics"])


# ===========================================================================
# Public / Guest Storefront Tracking
# ===========================================================================

@public_tracking_router.get(
    "/{order_number}/tracking",
    response_model=OrderTrackingTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Guest Order Tracking Inquiry",
)
async def track_guest_order(
    order_number: str,
    phone: str = Query(..., description="Customer mobile phone number for verification"),
    db: AsyncSession = Depends(get_db),
) -> OrderTrackingTimelineResponse:
    """Guest lookup for delivery tracking timeline requiring phone verification."""
    return await get_order_tracking_timeline(
        db=db,
        order_number=order_number,
        customer_phone=phone,
    )


# ===========================================================================
# Customer Account Tracking
# ===========================================================================

@customer_fulfillment_router.get(
    "/{order_number}/tracking",
    response_model=OrderTrackingTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Customer Order Tracking Timeline",
)
async def track_customer_order(
    order_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderTrackingTimelineResponse:
    """Customer lookup for delivery tracking timeline (ownership verified)."""
    return await get_order_tracking_timeline(
        db=db,
        order_number=order_number,
        current_user=current_user,
    )


# ===========================================================================
# Administrative and Staff Logistics Operations
# ===========================================================================

@admin_fulfillment_router.post(
    "/orders/{order_id}/shipments",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create Shipment Parcel for Order",
)
async def create_order_shipment(
    order_id: int,
    req: ShipmentCreateRequest,
    current_user: User = Depends(require_permission("shipments.manage")),
    db: AsyncSession = Depends(get_db),
) -> ShipmentResponse:
    """Allocate order items, assign carrier, and book physical consignment."""
    return await create_shipment_for_order(
        db=db,
        order_id=order_id,
        req=req,
        actor_user=current_user,
    )


@admin_fulfillment_router.get(
    "/orders/{order_id}/shipments",
    response_model=List[ShipmentResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List Shipments for Order",
)
async def list_order_shipments(
    order_id: int,
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> List[ShipmentResponse]:
    """Retrieve all shipments allocated to a specific order."""
    shipments, _ = await list_shipments(db=db, order_id=order_id, limit=100)
    return shipments


@admin_fulfillment_router.get(
    "/shipments",
    response_model=ShipmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Search and Filter Work Queue Shipments",
)
async def search_shipments(
    status_filter: Optional[str] = Query(None, alias="status"),
    courier_code: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> ShipmentListResponse:
    """Search and paginate fulfillment queue parcels."""
    offset = (page - 1) * page_size
    items, total = await list_shipments(
        db=db,
        status_filter=status_filter,
        courier_code=courier_code,
        destination_city=city,
        search=search,
        limit=page_size,
        offset=offset,
    )
    return ShipmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_fulfillment_router.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Retrieve Shipment Details",
)
async def get_shipment_details(
    shipment_id: int,
    current_user: User = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
) -> ShipmentResponse:
    """Retrieve full shipment parcel with items and tracking timeline."""
    return await get_shipment_by_id(db=db, shipment_id=shipment_id)


@admin_fulfillment_router.patch(
    "/shipments/{shipment_id}/status",
    response_model=ShipmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Advance Fulfillment Status",
)
async def update_fulfillment_status(
    shipment_id: int,
    req: ShipmentStatusUpdateRequest,
    current_user: User = Depends(require_permission("shipments.manage")),
    db: AsyncSession = Depends(get_db),
) -> ShipmentResponse:
    """Transition shipment fulfillment state (packing, dispatched, delivered, etc.)."""
    return await update_shipment_status(
        db=db,
        shipment_id=shipment_id,
        req=req,
        actor_user=current_user,
    )


@admin_fulfillment_router.patch(
    "/shipments/{shipment_id}/tracking",
    response_model=ShipmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Carrier Tracking Reference",
)
async def update_carrier_tracking(
    shipment_id: int,
    req: ShipmentTrackingUpdateRequest,
    current_user: User = Depends(require_permission("shipments.manage")),
    db: AsyncSession = Depends(get_db),
) -> ShipmentResponse:
    """Update carrier assignment or Airway Bill / CN number."""
    return await update_shipment_tracking(
        db=db,
        shipment_id=shipment_id,
        req=req,
        actor_user=current_user,
    )


@admin_fulfillment_router.post(
    "/shipments/{shipment_id}/events",
    response_model=ShipmentEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Record Manual Tracking Event",
)
async def create_manual_tracking_event(
    shipment_id: int,
    req: ShipmentEventCreateRequest,
    current_user: User = Depends(require_permission("shipments.manage")),
    db: AsyncSession = Depends(get_db),
) -> ShipmentEventResponse:
    """Append a physical tracking checkpoint without advancing shipment status."""
    return await record_shipment_event(
        db=db,
        shipment_id=shipment_id,
        req=req,
        actor_user=current_user,
    )
