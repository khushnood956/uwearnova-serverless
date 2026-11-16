"""
Returns, Exchanges, and Refunds API Endpoints (Module M16)
Customer return/exchange requests, administrative review, warehouse quality inspection,
inventory restock, doorstep exchange dispatch, and payment refund processing.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.rbac.dependencies import require_permission
from app.modules.returns.schemas import (
    ReturnExchangeResolveRequest,
    ReturnInspectionRequest,
    ReturnReceiveRequest,
    ReturnRefundResolveRequest,
    ReturnRequestCreatePayload,
    ReturnRequestListResponse,
    ReturnRequestResponse,
    ReturnReviewRequest,
)
from app.modules.returns.service import (
    create_return_request,
    get_order_return_requests,
    get_return_request_by_id,
    inspect_returned_items,
    list_return_requests,
    receive_returned_items,
    resolve_return_exchange,
    resolve_return_refund,
    review_return_request,
)

public_returns_router = APIRouter(prefix="/orders", tags=["Storefront: Returns & Exchanges"])
customer_returns_router = APIRouter(prefix="/customer/orders", tags=["Customer: Returns & Exchanges"])
admin_returns_router = APIRouter(prefix="/admin/returns", tags=["Admin: Returns & Quality Inspection"])


# ==============================================================================
# Public / Guest Storefront Returns
# ==============================================================================

@public_returns_router.post(
    "/{order_number}/returns",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Guest Submit Return or Exchange Request",
)
async def submit_guest_return_request(
    order_number: str,
    payload: ReturnRequestCreatePayload,
    phone: str = Query(..., description="Customer phone number for verification"),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestResponse:
    """Guest order return initiation requiring phone number verification."""
    return await create_return_request(
        db=db,
        order_number=order_number,
        payload=payload,
        current_user=None,
        customer_phone=phone,
    )


@public_returns_router.get(
    "/{order_number}/returns",
    response_model=List[ReturnRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Guest List Returns for Order",
)
async def list_guest_order_returns(
    order_number: str,
    phone: str = Query(..., description="Customer phone number for verification"),
    db: AsyncSession = Depends(get_db),
) -> List[ReturnRequestResponse]:
    """Guest lookup of submitted return and exchange requests."""
    return await get_order_return_requests(
        db=db,
        order_number=order_number,
        current_user=None,
        customer_phone=phone,
    )


# ==============================================================================
# Customer Portal Returns
# ==============================================================================

@customer_returns_router.post(
    "/{order_number}/returns",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Customer Submit Return or Exchange Request",
)
async def submit_customer_return_request(
    order_number: str,
    payload: ReturnRequestCreatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestResponse:
    """Customer account submission for return or doorstep exchange."""
    return await create_return_request(
        db=db,
        order_number=order_number,
        payload=payload,
        current_user=current_user,
    )


@customer_returns_router.get(
    "/{order_number}/returns",
    response_model=List[ReturnRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Customer List Returns for Order",
)
async def list_customer_order_returns(
    order_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ReturnRequestResponse]:
    """List return and exchange requests for an authenticated customer's order."""
    return await get_order_return_requests(
        db=db,
        order_number=order_number,
        current_user=current_user,
    )


# ==============================================================================
# Administrative and Warehouse Operations
# ==============================================================================

@admin_returns_router.get(
    "",
    response_model=ReturnRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Search and Filter Return Work Queue",
)
async def list_admin_returns(
    order_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    request_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("returns.read")),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestListResponse:
    """Administrative work queue for processing client return and exchange requests."""
    offset = (page - 1) * page_size
    items, total = await list_return_requests(
        db=db,
        order_id=order_id,
        status_filter=status_filter,
        request_type=request_type,
        search=search,
        limit=page_size,
        offset=offset,
    )
    return ReturnRequestListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_returns_router.get(
    "/{return_id}",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Retrieve Return Request Detail",
)
async def get_admin_return_detail(
    return_id: int,
    current_user: User = Depends(require_permission("returns.read")),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestResponse:
    """Retrieve full return request with line items and inspection reports."""
    return await get_return_request_by_id(db=db, return_id=return_id)


@admin_returns_router.post(
    "/{return_id}/review",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Review Return Request (Approve or Reject)",
)
async def review_return_endpoint(
    return_id: int,
    req: ReturnReviewRequest,
    current_user: User = Depends(require_permission("returns.review")),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestResponse:
    """Approve or reject customer return request based on store policy."""
    return await review_return_request(
        db=db,
        return_id=return_id,
        req=req,
        actor_user=current_user,
    )


@admin_returns_router.post(
    "/{return_id}/receive",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Mark Returned Parcel Received at Warehouse",
)
async def receive_return_endpoint(
    return_id: int,
    req: ReturnReceiveRequest,
    current_user: User = Depends(require_permission("returns.review")),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestResponse:
    """Log physical warehouse parcel delivery."""
    return await receive_returned_items(
        db=db,
        return_id=return_id,
        req=req,
        actor_user=current_user,
    )


@admin_returns_router.post(
    "/{return_id}/inspect",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Submit Warehouse Quality Inspection & Restock",
)
async def inspect_return_endpoint(
    return_id: int,
    req: ReturnInspectionRequest,
    current_user: User = Depends(require_permission("returns.review")),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestResponse:
    """Assess garment quality and trigger transactional inventory restock."""
    return await inspect_returned_items(
        db=db,
        return_id=return_id,
        req=req,
        actor_user=current_user,
    )


@admin_returns_router.post(
    "/{return_id}/resolve-refund",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Execute Payment Refund Resolution",
)
async def resolve_refund_endpoint(
    return_id: int,
    req: ReturnRefundResolveRequest,
    current_user: User = Depends(require_permission("refunds.create")),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestResponse:
    """Execute online payment adapter refund or record authorized COD manual payout."""
    return await resolve_return_refund(
        db=db,
        return_id=return_id,
        req=req,
        actor_user=current_user,
    )


@admin_returns_router.post(
    "/{return_id}/resolve-exchange",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Execute Doorstep Exchange Resolution",
)
async def resolve_exchange_endpoint(
    return_id: int,
    req: ReturnExchangeResolveRequest,
    current_user: User = Depends(require_permission("returns.resolve")),
    db: AsyncSession = Depends(get_db),
) -> ReturnRequestResponse:
    """Dispatch replacement garment parcel for doorstep exchange."""
    return await resolve_return_exchange(
        db=db,
        return_id=return_id,
        req=req,
        actor_user=current_user,
    )
