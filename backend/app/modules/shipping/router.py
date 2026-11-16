"""
Shipping API Endpoints (M11)
Storefront endpoints for delivery quotes and address validation,
and administrative routes for shipping zones and method configuration.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_optional_current_user
from app.modules.auth.models import User
from app.modules.rbac.dependencies import require_permission
from app.modules.shipping.schemas import (
    DeliveryAddressValidationRequest,
    DeliveryAddressValidationResponse,
    ShippingMethodCreate,
    ShippingMethodResponse,
    ShippingMethodUpdate,
    ShippingQuoteRequest,
    ShippingQuoteResponse,
    ShippingZoneCreate,
    ShippingZoneResponse,
)
from app.modules.shipping.service import (
    calculate_shipping_quote,
    create_shipping_method,
    create_shipping_zone,
    list_shipping_methods,
    list_shipping_zones,
    update_shipping_method,
    validate_delivery_address,
)

public_shipping_router = APIRouter(prefix="/shipping", tags=["Storefront: Shipping & Quotes"])
admin_shipping_router = APIRouter(prefix="/admin/shipping", tags=["Admin: Shipping Configuration"])


# ===========================================================================
# Storefront Endpoints
# ===========================================================================

@public_shipping_router.post(
    "/quote",
    response_model=ShippingQuoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Delivery Quotes",
)
async def get_shipping_quote_endpoint(
    req: ShippingQuoteRequest,
    x_anonymous_cart_token: Optional[str] = Header(None, alias="X-Anonymous-Cart-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShippingQuoteResponse:
    """
    Calculate delivery quote for customer destination.
    Evaluates free shipping qualification against active cart or specified subtotal.
    Never trusts client prices or hardcoded courier tariffs.
    """
    return await calculate_shipping_quote(
        db,
        req=req,
        current_user=current_user,
        anonymous_token=x_anonymous_cart_token,
    )


@public_shipping_router.post(
    "/validate-address",
    response_model=DeliveryAddressValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Customer Delivery Address",
)
async def validate_address_endpoint(
    req: DeliveryAddressValidationRequest,
    db: AsyncSession = Depends(get_db),
) -> DeliveryAddressValidationResponse:
    """Validate customer shipping address, phone format, and destination delivery zone."""
    return await validate_delivery_address(db, req)


@public_shipping_router.get(
    "/methods",
    response_model=List[ShippingMethodResponse],
    status_code=status.HTTP_200_OK,
    summary="List Active Delivery Options",
)
async def list_active_methods_endpoint(
    db: AsyncSession = Depends(get_db),
) -> List[ShippingMethodResponse]:
    """Retrieve active delivery options available for customer checkout."""
    return await list_shipping_methods(db, active_only=True)


# ===========================================================================
# Administrative Configuration Endpoints
# ===========================================================================

@admin_shipping_router.get(
    "/zones",
    response_model=List[ShippingZoneResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List Shipping Zones",
)
async def admin_list_zones_endpoint(
    current_user: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> List[ShippingZoneResponse]:
    """Retrieve all delivery zones and serviced city configurations."""
    return await list_shipping_zones(db)


@admin_shipping_router.post(
    "/zones",
    response_model=ShippingZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create Shipping Zone",
)
async def admin_create_zone_endpoint(
    req: ShippingZoneCreate,
    current_user: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> ShippingZoneResponse:
    """Define a new regional logistics service area."""
    return await create_shipping_zone(db, req, actor_user=current_user)


@admin_shipping_router.get(
    "/methods",
    response_model=List[ShippingMethodResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List All Shipping Methods",
)
async def admin_list_methods_endpoint(
    current_user: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> List[ShippingMethodResponse]:
    """Retrieve all shipping delivery methods with active/inactive status."""
    return await list_shipping_methods(db, active_only=False)


@admin_shipping_router.post(
    "/methods",
    response_model=ShippingMethodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create Delivery Method",
)
async def admin_create_method_endpoint(
    req: ShippingMethodCreate,
    current_user: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> ShippingMethodResponse:
    """Create a new delivery method with base rate and free shipping threshold."""
    return await create_shipping_method(db, req, actor_user=current_user)


@admin_shipping_router.patch(
    "/methods/{method_id}",
    response_model=ShippingMethodResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Delivery Method",
)
async def admin_update_method_endpoint(
    method_id: int,
    req: ShippingMethodUpdate,
    current_user: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> ShippingMethodResponse:
    """Modify shipping method pricing, free threshold, or transit SLA days."""
    return await update_shipping_method(db, method_id, req, actor_user=current_user)
