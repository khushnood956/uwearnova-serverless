"""
Customer Account REST Router (Module M17)
Endpoints for profile management, address book CRUD, preferences,
customer-safe order details & timelines, return history, wishlist access, and security.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.cart.schemas import WishlistResponse
from app.modules.cart.service import get_or_create_wishlist
from app.modules.customer.schemas import (
    AddressCreateRequest,
    AddressListResponse,
    AddressResponse,
    AddressUpdateRequest,
    AdminCustomerDetailResponse,
    AdminCustomerListResponse,
    CustomerOrderDetailResponse,
    CustomerPasswordChangeRequest,
    CustomerPreferencesResponse,
    CustomerPreferencesUpdateRequest,
    CustomerProfileResponse,
    CustomerProfileUpdateRequest,
    CustomerReturnListResponse,
    CustomerReturnResponse,
    CustomerSecurityOverviewResponse,
    CustomerStatusUpdateRequest,
)
from app.modules.customer.service import (
    change_customer_password_workflow,
    create_customer_address,
    delete_customer_address,
    get_customer_address,
    get_customer_detail_admin,
    get_customer_order_detail,
    get_customer_preferences,
    get_customer_return_detail,
    get_customer_security_overview,
    get_or_create_customer_profile,
    list_customer_addresses,
    list_customer_returns,
    list_customers_admin,
    revoke_other_sessions,
    set_default_address,
    update_customer_address,
    update_customer_preferences,
    update_customer_profile,
    update_customer_status_admin,
)
from app.modules.rbac.dependencies import require_permission

customer_account_router = APIRouter(prefix="/customer", tags=["Customer: Account Portal"])


# ==============================================================================
# 1. Profile & Preferences Endpoints
# ==============================================================================

@customer_account_router.get(
    "/profile",
    response_model=CustomerProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Customer Profile",
)
async def get_profile_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerProfileResponse:
    """Retrieve personal profile details and contact information for the authenticated customer."""
    return await get_or_create_customer_profile(db=db, user=current_user)


@customer_account_router.patch(
    "/profile",
    response_model=CustomerProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Customer Profile",
)
async def update_profile_endpoint(
    req: CustomerProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerProfileResponse:
    """Update personal details and primary contact number."""
    return await update_customer_profile(db=db, user=current_user, req=req)


@customer_account_router.get(
    "/preferences",
    response_model=CustomerPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Account Preferences",
)
async def get_preferences_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerPreferencesResponse:
    """Retrieve communication channel and language preferences."""
    return await get_customer_preferences(db=db, user=current_user)


@customer_account_router.patch(
    "/preferences",
    response_model=CustomerPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Account Preferences",
)
async def update_preferences_endpoint(
    req: CustomerPreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerPreferencesResponse:
    """Update marketing channels (Email, SMS, WhatsApp) and language/currency settings."""
    return await update_customer_preferences(db=db, user=current_user, req=req)


# ==============================================================================
# 2. Address Book CRUD Endpoints
# ==============================================================================

@customer_account_router.get(
    "/addresses",
    response_model=AddressListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Saved Addresses",
)
async def list_addresses_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressListResponse:
    """Retrieve all saved shipping addresses for the customer, default address first."""
    return await list_customer_addresses(db=db, user_id=current_user.id)


@customer_account_router.post(
    "/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Saved Address",
)
async def create_address_endpoint(
    req: AddressCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    """Add a new delivery address to the customer's address book."""
    return await create_customer_address(db=db, user=current_user, req=req)


@customer_account_router.get(
    "/addresses/{address_id}",
    response_model=AddressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Single Address",
)
async def get_address_endpoint(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    """Retrieve a single address, strictly enforcing ownership."""
    return await get_customer_address(db=db, user_id=current_user.id, address_id=address_id)


@customer_account_router.patch(
    "/addresses/{address_id}",
    response_model=AddressResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Saved Address",
)
async def update_address_endpoint(
    address_id: int,
    req: AddressUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    """Update address fields, maintaining default address integrity."""
    return await update_customer_address(db=db, user=current_user, address_id=address_id, req=req)


@customer_account_router.delete(
    "/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Saved Address",
)
async def delete_address_endpoint(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete address with automatic fallback default promotion if default is deleted."""
    await delete_customer_address(db=db, user=current_user, address_id=address_id)


@customer_account_router.post(
    "/addresses/{address_id}/default",
    response_model=AddressResponse,
    status_code=status.HTTP_200_OK,
    summary="Set Primary Default Address",
)
async def set_default_address_endpoint(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    """Explicitly designate an address as primary default."""
    return await set_default_address(db=db, user=current_user, address_id=address_id)


# ==============================================================================
# 3. Customer-Safe Order Details & Timeline Endpoint
# ==============================================================================

@customer_account_router.get(
    "/orders/{order_number}",
    response_model=CustomerOrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Customer Order Details & Timeline",
)
async def get_order_detail_endpoint(
    order_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerOrderDetailResponse:
    """
    Retrieve customer-facing order detail with item snapshots, shipments,
    and sanitized status timeline. Internal staff notes are completely omitted.
    """
    return await get_customer_order_detail(db=db, user=current_user, order_number=order_number)


# ==============================================================================
# 4. Return & Exchange History Endpoints
# ==============================================================================

@customer_account_router.get(
    "/returns",
    response_model=CustomerReturnListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Customer Returns & Exchanges",
)
async def list_returns_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerReturnListResponse:
    """Retrieve full return and exchange history across all customer orders."""
    return await list_customer_returns(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
    )


@customer_account_router.get(
    "/returns/{return_id}",
    response_model=CustomerReturnResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Return Request Details",
)
async def get_return_detail_endpoint(
    return_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerReturnResponse:
    """Retrieve detailed return request state (omits internal staff/inspector notes)."""
    return await get_customer_return_detail(db=db, user=current_user, return_id=return_id)


# ==============================================================================
# 5. Customer Wishlist Access
# ==============================================================================

@customer_account_router.get(
    "/wishlist",
    response_model=WishlistResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Customer Wishlist",
)
async def get_customer_wishlist_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WishlistResponse:
    """Retrieve active customer saved items and product availability."""
    from app.modules.cart.service import build_wishlist_response
    wishlist = await get_or_create_wishlist(db=db, user=current_user)
    return await build_wishlist_response(db, wishlist)


# ==============================================================================
# 6. Password & Security Endpoints
# ==============================================================================

@customer_account_router.get(
    "/security",
    response_model=CustomerSecurityOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Security & Session Overview",
)
async def get_security_overview_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerSecurityOverviewResponse:
    """View active session count, email verification state, and recent login history."""
    return await get_customer_security_overview(db=db, user=current_user)


@customer_account_router.post(
    "/security/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change Password",
)
async def change_password_endpoint(
    req: CustomerPasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change account password after verifying current password.
    Automatically invalidates all active sessions.
    """
    await change_customer_password_workflow(
        db=db,
        user=current_user,
        current_password=req.current_password,
        new_password=req.new_password,
    )
    return {"message": "Password changed successfully. Existing sessions have been invalidated."}


@customer_account_router.post(
    "/security/revoke-sessions",
    status_code=status.HTTP_200_OK,
    summary="Revoke Other Active Sessions",
)
async def revoke_sessions_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke all active sessions for security."""
    count = await revoke_other_sessions(db=db, user=current_user)
    return {"message": f"Successfully revoked {count} active session(s)."}


# ==============================================================================
# 7. Administrative Customer Management Endpoints (Module M19)
# ==============================================================================

admin_customers_router = APIRouter(prefix="/admin/customers", tags=["Admin: Customer Accounts"])


@admin_customers_router.get(
    "",
    response_model=AdminCustomerListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: List Customer Accounts",
)
async def admin_list_customers_endpoint(
    search: Optional[str] = Query(None, description="Search by customer name, email, or phone"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, suspended, disabled)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("customers.read")),
    db: AsyncSession = Depends(get_db),
) -> AdminCustomerListResponse:
    """Search and list customer accounts with profile names, phone numbers, and spend statistics."""
    offset = (page - 1) * page_size
    customers, total = await list_customers_admin(
        db, search=search, status_filter=status_filter, limit=page_size, offset=offset
    )
    return AdminCustomerListResponse(
        customers=customers,
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_customers_router.get(
    "/{customer_id}",
    response_model=AdminCustomerDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Retrieve Customer Dossier",
)
async def admin_get_customer_endpoint(
    customer_id: int,
    current_user: User = Depends(require_permission("customers.read")),
    db: AsyncSession = Depends(get_db),
) -> AdminCustomerDetailResponse:
    """Retrieve complete customer details including profile, saved addresses, and order history."""
    return await get_customer_detail_admin(db, customer_id=customer_id)


@admin_customers_router.patch(
    "/{customer_id}/status",
    response_model=AdminCustomerDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Customer Account Status",
)
async def admin_update_customer_status_endpoint(
    customer_id: int,
    req: CustomerStatusUpdateRequest,
    current_user: User = Depends(require_permission("customers.update_status")),
    db: AsyncSession = Depends(get_db),
) -> AdminCustomerDetailResponse:
    """Modify customer account status (active, suspended, disabled). Invalidates sessions when suspending."""
    return await update_customer_status_admin(
        db, customer_id=customer_id, new_status=req.status, reason=req.reason, actor_user=current_user
    )
