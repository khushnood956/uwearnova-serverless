"""
Shipping Service Layer (M11)
Calculates server-verified delivery quotes, validates shipping addresses,
manages shipping zones and methods, and evaluates free-shipping qualification.
"""

from decimal import Decimal
import json
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.cart.service import build_cart_response, get_or_create_cart
from app.modules.shipping.models import ShippingMethod, ShippingZone
from app.modules.shipping.provider import (
    BaseCourierProvider,
    ConfiguredRateCourierProvider,
)
from app.modules.shipping.schemas import (
    DeliveryAddressValidationRequest,
    DeliveryAddressValidationResponse,
    ShippingMethodCreate,
    ShippingMethodQuoteItem,
    ShippingMethodResponse,
    ShippingMethodUpdate,
    ShippingQuoteRequest,
    ShippingQuoteResponse,
    ShippingZoneCreate,
    ShippingZoneResponse,
    ShippingZoneUpdate,
)

DEFAULT_MAJOR_METROS = ["Karachi", "Lahore", "Islamabad", "Rawalpindi"]
DEFAULT_NATIONWIDE_CITIES = [
  "Faisalabad",
  "Multan",
  "Peshawar",
  "Quetta",
  "Sialkot",
  "Gujranwala",
  "Hyderabad",
  "Abbottabad",
  "Bahawalpur",
  "Sargodha",
  "Sukkur",
  "Sahiwal",
]


async def ensure_default_shipping_configuration(db: AsyncSession) -> None:
    """Bootstrap baseline Pakistani shipping zones and delivery methods if none exist."""
    stmt = select(ShippingZone)
    res = await db.execute(stmt)
    existing_zone = res.scalars().first()

    if existing_zone is not None:
        return

    # 1. Major Metropolitan Hubs
    metro_zone = ShippingZone(
        name="Major Metropolitan Hubs",
        code="major_metro",
        description="Karachi, Lahore, Islamabad, and Rawalpindi primary transit areas",
        cities=json.dumps(DEFAULT_MAJOR_METROS),
        is_active=True,
    )
    # 2. Nationwide Standard Tier
    nationwide_zone = ShippingZone(
        name="Nationwide Outlying Cities",
        code="nationwide",
        description="All other provincial cities and postal districts across Pakistan",
        cities=json.dumps(DEFAULT_NATIONWIDE_CITIES),
        is_active=True,
    )
    db.add_all([metro_zone, nationwide_zone])
    await db.flush()

    # 3. Standard Nationwide Method (350 PKR base, free over 15k)
    std_method = ShippingMethod(
        zone_id=None,  # Nationwide applicable
        name="Standard Nationwide Delivery",
        code="standard_delivery",
        description="Nationwide white-glove courier delivery (2–4 business days)",
        base_fee=Decimal("350.00"),
        free_shipping_threshold=Decimal("15000.00"),
        estimated_days_min=2,
        estimated_days_max=4,
        is_cod_supported=True,
        is_active=True,
        sort_order=0,
    )
    # 4. Express Metro Courier (750 PKR, 1–2 days, major metros only)
    express_method = ShippingMethod(
        zone_id=metro_zone.id,
        name="Express Metro Courier",
        code="express_metro",
        description="Priority same-city and twin-city courier dispatch (1–2 business days)",
        base_fee=Decimal("750.00"),
        free_shipping_threshold=None,  # Express never receives free shipping override
        estimated_days_min=1,
        estimated_days_max=2,
        is_cod_supported=True,
        is_active=True,
        sort_order=1,
    )
    db.add_all([std_method, express_method])
    await db.flush()


async def resolve_zone_for_city(db: AsyncSession, city: str) -> Optional[ShippingZone]:
    """Match destination city name against active shipping zones."""
    city_normalized = city.strip().lower()
    stmt = select(ShippingZone).where(ShippingZone.is_active == True)
    res = await db.execute(stmt)
    zones = res.scalars().all()

    for zone in zones:
        try:
            city_list = [c.strip().lower() for c in json.loads(zone.cities)]
            if city_normalized in city_list:
                return zone
        except Exception:
            continue

    return None


async def validate_delivery_address(
    db: AsyncSession,
    req: DeliveryAddressValidationRequest,
) -> DeliveryAddressValidationResponse:
    """Validate customer shipping address fields and destination serviceability."""
    await ensure_default_shipping_configuration(db)

    city_clean = req.city.strip()
    zone = await resolve_zone_for_city(db, city_clean)
    zone_code = zone.code if zone else "nationwide"

    # Default Pakistan serviceability
    is_serviceable = req.country_code.upper() == "PK" and len(city_clean) > 1

    return DeliveryAddressValidationResponse(
        is_valid=True,
        city=city_clean,
        is_serviceable=is_serviceable,
        zone_code=zone_code,
        normalized_phone=req.phone,
        message="Delivery address verified for nationwide dispatch" if is_serviceable else "Destination country outside serviced network",
    )


async def calculate_shipping_quote(
    db: AsyncSession,
    req: ShippingQuoteRequest,
    current_user: Optional[User] = None,
    anonymous_token: Optional[str] = None,
) -> ShippingQuoteResponse:
    """
    Calculate server-authoritative shipping quote based on destination city,
    subtotal, COD requirement, and active shipping method rules.
    """
    await ensure_default_shipping_configuration(db)

    # 1. Determine subtotal
    subtotal = req.subtotal
    if subtotal is None:
        if current_user is not None or anonymous_token is not None:
            cart, _ = await get_or_create_cart(
                db,
                user=current_user,
                anonymous_token=anonymous_token,
            )
            cart_res = await build_cart_response(db, cart)
            subtotal = cart_res.subtotal
        else:
            subtotal = Decimal("0.00")

    # 2. Resolve destination zone
    matched_zone = await resolve_zone_for_city(db, req.city)
    matched_zone_id = matched_zone.id if matched_zone else None
    zone_code = matched_zone.code if matched_zone else "nationwide"

    # 3. Query eligible shipping methods
    stmt = (
        select(ShippingMethod)
        .where(
            ShippingMethod.is_active == True,
            (ShippingMethod.zone_id == None) | (ShippingMethod.zone_id == matched_zone_id),
        )
        .order_by(ShippingMethod.sort_order.asc(), ShippingMethod.base_fee.asc())
    )
    res = await db.execute(stmt)
    methods = res.scalars().all()

    quote_items: List[ShippingMethodQuoteItem] = []
    for method in methods:
        if req.is_cod and not method.is_cod_supported:
            continue

        base_fee = method.base_fee
        is_free = False
        discount = Decimal("0.00")
        final_fee = base_fee
        amount_needed: Optional[Decimal] = None

        if method.free_shipping_threshold is not None:
            threshold = method.free_shipping_threshold
            if subtotal >= threshold:
                is_free = True
                discount = base_fee
                final_fee = Decimal("0.00")
                amount_needed = Decimal("0.00")
            else:
                amount_needed = max(Decimal("0.00"), threshold - subtotal)

        quote_items.append(
            ShippingMethodQuoteItem(
                code=method.code,
                name=method.name,
                description=method.description,
                estimated_days_min=method.estimated_days_min,
                estimated_days_max=method.estimated_days_max,
                is_cod_supported=method.is_cod_supported,
                base_fee=base_fee,
                discount=discount,
                final_fee=final_fee,
                is_free=is_free,
                free_shipping_threshold=method.free_shipping_threshold,
                amount_needed_for_free_shipping=amount_needed,
            )
        )

    recommended = "standard_delivery"
    if quote_items and not any(q.code == recommended for q in quote_items):
        recommended = quote_items[0].code

    return ShippingQuoteResponse(
        destination_city=req.city,
        is_serviceable=len(quote_items) > 0,
        zone_code=zone_code,
        subtotal=subtotal,
        available_methods=quote_items,
        recommended_method_code=recommended,
    )


# ===========================================================================
# Admin Shipping Configuration Management
# ===========================================================================

async def list_shipping_zones(db: AsyncSession) -> List[ShippingZoneResponse]:
    """Retrieve all shipping zones with parsed city arrays."""
    await ensure_default_shipping_configuration(db)
    stmt = select(ShippingZone).order_by(ShippingZone.name.asc())
    res = await db.execute(stmt)
    zones = res.scalars().all()
    return [
        ShippingZoneResponse(
            id=z.id,
            name=z.name,
            code=z.code,
            description=z.description,
            cities=json.loads(z.cities) if z.cities else [],
            is_active=z.is_active,
            created_at=z.created_at,
            updated_at=z.updated_at,
        )
        for z in zones
    ]


async def create_shipping_zone(
    db: AsyncSession,
    req: ShippingZoneCreate,
    actor_user: User,
) -> ShippingZoneResponse:
    """Create a new shipping zone."""
    existing_stmt = select(ShippingZone).where(ShippingZone.code == req.code)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Shipping zone with code '{req.code}' already exists",
        )

    zone = ShippingZone(
        name=req.name,
        code=req.code,
        description=req.description,
        cities=json.dumps(req.cities),
        is_active=req.is_active,
    )
    db.add(zone)
    await db.flush()
    await db.refresh(zone)

    await log_audit_event(
        db=db,
        action="shipping_zone.created",
        entity_type="shipping_zone",
        entity_id=str(zone.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"code": zone.code, "name": zone.name},
    )

    return ShippingZoneResponse(
        id=zone.id,
        name=zone.name,
        code=zone.code,
        description=zone.description,
        cities=json.loads(zone.cities),
        is_active=zone.is_active,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


async def list_shipping_methods(
    db: AsyncSession,
    active_only: bool = False,
) -> List[ShippingMethodResponse]:
    """Retrieve all shipping delivery methods."""
    await ensure_default_shipping_configuration(db)
    stmt = select(ShippingMethod).order_by(ShippingMethod.sort_order.asc(), ShippingMethod.id.asc())
    if active_only:
        stmt = stmt.where(ShippingMethod.is_active == True)
    res = await db.execute(stmt)
    methods = res.scalars().all()
    return [ShippingMethodResponse.model_validate(m) for m in methods]


async def create_shipping_method(
    db: AsyncSession,
    req: ShippingMethodCreate,
    actor_user: User,
) -> ShippingMethodResponse:
    """Create a new delivery method with custom fee and free shipping threshold."""
    existing_stmt = select(ShippingMethod).where(ShippingMethod.code == req.code)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Shipping method with code '{req.code}' already exists",
        )

    method = ShippingMethod(**req.model_dump())
    db.add(method)
    await db.flush()
    await db.refresh(method)

    await log_audit_event(
        db=db,
        action="shipping_method.created",
        entity_type="shipping_method",
        entity_id=str(method.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"code": method.code, "base_fee": str(method.base_fee)},
    )
    return ShippingMethodResponse.model_validate(method)


async def update_shipping_method(
    db: AsyncSession,
    method_id: int,
    req: ShippingMethodUpdate,
    actor_user: User,
) -> ShippingMethodResponse:
    """Update delivery method fees, thresholds, and operational flags."""
    stmt = select(ShippingMethod).where(ShippingMethod.id == method_id)
    res = await db.execute(stmt)
    method = res.scalar_one_or_none()

    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping method not found",
        )

    for field, val in req.model_dump(exclude_unset=True).items():
        setattr(method, field, val)

    await db.flush()
    await db.refresh(method)

    await log_audit_event(
        db=db,
        action="shipping_method.updated",
        entity_type="shipping_method",
        entity_id=str(method.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details=req.model_dump(exclude_unset=True, mode="json"),
    )
    return ShippingMethodResponse.model_validate(method)
