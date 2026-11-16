"""
Shipping Configuration & Quotes Tests (Module M11)
Tests delivery zone definitions, shipping quote calculation, free-shipping threshold
evaluation, delivery address validation, courier provider abstraction,
and administrative management with RBAC enforcement.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.cart.service import add_item_to_cart, get_or_create_cart
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.service import get_or_create_default_location
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.shipping.models import ShippingMethod, ShippingZone
from app.modules.shipping.provider import (
    ConfiguredRateCourierProvider,
    MockThirdPartyCourierProvider,
)
from app.modules.shipping.service import ensure_default_shipping_configuration


@pytest.fixture
async def seeded_shipping_env():
    """Seeds baseline RBAC, shipping zones/methods, and catalog items for quote tests."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await ensure_default_shipping_configuration(session)
        loc = await get_or_create_default_location(session)

        # Create category and product
        cat = Category(name="Outerwear", slug="outerwear", is_active=True)
        session.add(cat)
        await session.flush()

        prod = Product(
            name="Cashmere Overcoat",
            slug="cashmere-overcoat",
            category_id=cat.id,
            price=Decimal("65000.00"),
            status="active",
        )
        session.add(prod)
        await session.flush()

        var = ProductVariant(
            product_id=prod.id,
            sku="COAT-CSH-42",
            size="42",
            color_name="Camel",
            inventory_count=10,
            in_stock=True,
            is_active=True,
        )
        session.add(var)
        await session.flush()

        inv = InventoryItem(
            variant_id=var.id,
            location_id=loc.id,
            quantity_on_hand=10,
            quantity_reserved=0,
        )
        session.add(inv)

        # Users
        admin = User(
            email="admin_ship@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        customer = User(
            email="cust_ship@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        session.add_all([admin, customer])
        await session.flush()

        # Assign store_admin role to admin
        role_res = await session.execute(select(Role).where(Role.name == "store_admin"))
        role = role_res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=admin.id, role_id=role.id))

        await session.commit()
        await session.refresh(var)
        await session.refresh(admin)
        await session.refresh(customer)

        return {
            "variant_id": var.id,
            "admin": admin,
            "customer": customer,
        }


def auth_header_for(user: User) -> dict:
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Shipping Quote Calculation Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_shipping_quote_under_and_over_threshold(async_client: AsyncClient, seeded_shipping_env):
    """Verify standard shipping fee applies under 15k and free shipping applies over 15k."""
    # 1. Subtotal under 15k (PKR 8,500) -> Standard 350 applies
    quote_under = await async_client.post(
        "/api/v1/shipping/quote",
        json={"city": "Lahore", "subtotal": 8500.00},
    )
    assert quote_under.status_code == 200
    data_under = quote_under.json()
    assert data_under["destination_city"] == "Lahore"
    assert data_under["zone_code"] == "major_metro"

    std_method = next(m for m in data_under["available_methods"] if m["code"] == "standard_delivery")
    assert Decimal(std_method["base_fee"]) == Decimal("350.00")
    assert Decimal(std_method["final_fee"]) == Decimal("350.00")
    assert std_method["is_free"] is False
    assert Decimal(std_method["amount_needed_for_free_shipping"]) == Decimal("6500.00")

    # 2. Subtotal over 15k (PKR 25,000) -> Standard becomes free (PKR 0.00)
    quote_over = await async_client.post(
        "/api/v1/shipping/quote",
        json={"city": "Lahore", "subtotal": 25000.00},
    )
    assert quote_over.status_code == 200
    data_over = quote_over.json()

    std_over = next(m for m in data_over["available_methods"] if m["code"] == "standard_delivery")
    assert Decimal(std_over["base_fee"]) == Decimal("350.00")
    assert Decimal(std_over["discount"]) == Decimal("350.00")
    assert Decimal(std_over["final_fee"]) == Decimal("0.00")
    assert std_over["is_free"] is True
    assert Decimal(std_over["amount_needed_for_free_shipping"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_shipping_quote_dynamic_cart_resolution(async_client: AsyncClient, seeded_shipping_env):
    """Verify shipping quote automatically resolves subtotal from active customer cart."""
    env = seeded_shipping_env
    customer = env["customer"]
    headers = auth_header_for(customer)

    # 1. Add Cashmere Overcoat (PKR 65,000) to customer cart
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        cart, _ = await get_or_create_cart(session, user=customer)
        await add_item_to_cart(session, cart=cart, variant_id=env["variant_id"], quantity=1)
        await session.commit()

    # 2. Request quote without specifying subtotal in body
    quote_res = await async_client.post(
        "/api/v1/shipping/quote",
        headers=headers,
        json={"city": "Karachi"},
    )
    assert quote_res.status_code == 200
    q_data = quote_res.json()
    assert Decimal(q_data["subtotal"]) == Decimal("65000.00")

    std_method = next(m for m in q_data["available_methods"] if m["code"] == "standard_delivery")
    assert std_method["is_free"] is True
    assert Decimal(std_method["final_fee"]) == Decimal("0.00")


# ===========================================================================
# 2. Delivery Zone & Service Area Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_delivery_zone_method_filtering(async_client: AsyncClient, seeded_shipping_env):
    """Verify express courier is offered in major metros but excluded in outlying cities."""
    # 1. Major Metro (Karachi) receives both standard delivery and express metro courier
    metro_quote = await async_client.post(
        "/api/v1/shipping/quote",
        json={"city": "Karachi", "subtotal": 5000.00},
    )
    assert metro_quote.status_code == 200
    metro_codes = [m["code"] for m in metro_quote.json()["available_methods"]]
    assert "standard_delivery" in metro_codes
    assert "express_metro" in metro_codes

    # 2. Outlying City (Multan) receives standard nationwide delivery only
    outlying_quote = await async_client.post(
        "/api/v1/shipping/quote",
        json={"city": "Multan", "subtotal": 5000.00},
    )
    assert outlying_quote.status_code == 200
    outlying_codes = [m["code"] for m in outlying_quote.json()["available_methods"]]
    assert "standard_delivery" in outlying_codes
    assert "express_metro" not in outlying_codes


# ===========================================================================
# 3. Delivery Address Validation Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_delivery_address_validation(async_client: AsyncClient, seeded_shipping_env):
    """Verify Pakistani phone number normalization and destination serviceability checks."""
    # 1. Valid Lahore address with formatted mobile
    valid_res = await async_client.post(
        "/api/v1/shipping/validate-address",
        json={
            "full_name": "Ahmad Khan",
            "phone": "0300-1234567",
            "address_line_1": "House 14, Street 2, Gulberg III",
            "city": "Lahore",
            "postal_code": "54000",
            "country_code": "PK",
        },
    )
    assert valid_res.status_code == 200
    v_data = valid_res.json()
    assert v_data["is_valid"] is True
    assert v_data["is_serviceable"] is True
    assert v_data["zone_code"] == "major_metro"
    assert v_data["normalized_phone"] == "03001234567"

    # 2. Valid with international country code prefix +92
    intl_res = await async_client.post(
        "/api/v1/shipping/validate-address",
        json={
            "full_name": "Zainab Malik",
            "phone": "+92 321 9876543",
            "address_line_1": "Sector F-7/2, Street 10",
            "city": "Islamabad",
            "country_code": "PK",
        },
    )
    assert intl_res.status_code == 200
    assert intl_res.json()["is_valid"] is True
    assert intl_res.json()["normalized_phone"] == "+923219876543"

    # 3. Invalid phone format rejected by Pydantic validator
    invalid_phone = await async_client.post(
        "/api/v1/shipping/validate-address",
        json={
            "full_name": "Invalid Phone User",
            "phone": "12345",
            "address_line_1": "Street 1",
            "city": "Karachi",
        },
    )
    assert invalid_phone.status_code == 422


# ===========================================================================
# 4. Courier Provider Abstraction Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_courier_provider_interface():
    """Verify courier provider abstraction decouples rates and operates through interface."""
    # 1. ConfiguredRateCourierProvider
    configured_provider = ConfiguredRateCourierProvider()
    assert configured_provider.provider_code == "configured_rates"

    serviceable = await configured_provider.verify_serviceability(city="Karachi", country_code="PK")
    assert serviceable is True

    quote = await configured_provider.calculate_rate(
        origin_city="Lahore",
        destination_city="Karachi",
        weight_grams=1500,
        order_subtotal=Decimal("20000.00"),
    )
    assert quote.is_serviceable is True
    assert quote.total_rate == Decimal("0.00")  # Qualified for free shipping

    # 2. MockThirdPartyCourierProvider (TCS simulation)
    tcs_provider = MockThirdPartyCourierProvider(carrier_code="tcs", carrier_name="TCS Express")
    assert tcs_provider.provider_code == "tcs"

    tcs_quote = await tcs_provider.calculate_rate(
        origin_city="Lahore",
        destination_city="Multan",
        weight_grams=1500,
        order_subtotal=Decimal("5000.00"),
        is_cod=True,
    )
    assert tcs_quote.is_serviceable is True
    assert tcs_quote.total_rate == Decimal("500.00")  # 400 base + 100 COD


# ===========================================================================
# 5. Administrative Shipping Configuration & RBAC Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_shipping_crud_and_rbac(async_client: AsyncClient, seeded_shipping_env):
    """Verify admin shipping configuration endpoints and RBAC restrictions."""
    env = seeded_shipping_env
    admin_headers = auth_header_for(env["admin"])
    cust_headers = auth_header_for(env["customer"])

    # 1. Customer forbidden from admin endpoints
    cust_denied = await async_client.get("/api/v1/admin/shipping/methods", headers=cust_headers)
    assert cust_denied.status_code == 403

    # 2. Admin retrieves methods
    methods_res = await async_client.get("/api/v1/admin/shipping/methods", headers=admin_headers)
    assert methods_res.status_code == 200
    methods = methods_res.json()
    assert len(methods) >= 2

    # 3. Admin updates standard delivery base fee from 350 to 300
    std_id = next(m["id"] for m in methods if m["code"] == "standard_delivery")
    patch_res = await async_client.patch(
        f"/api/v1/admin/shipping/methods/{std_id}",
        headers=admin_headers,
        json={"base_fee": 300.00},
    )
    assert patch_res.status_code == 200
    assert Decimal(patch_res.json()["base_fee"]) == Decimal("300.00")

    # 4. Verify public quote reflects the updated fee
    quote_updated = await async_client.post(
        "/api/v1/shipping/quote",
        json={"city": "Karachi", "subtotal": 5000.00},
    )
    assert quote_updated.status_code == 200
    std_updated = next(m for m in quote_updated.json()["available_methods"] if m["code"] == "standard_delivery")
    assert Decimal(std_updated["final_fee"]) == Decimal("300.00")

    # 5. Admin creates a new regional zone
    new_zone_res = await async_client.post(
        "/api/v1/admin/shipping/zones",
        headers=admin_headers,
        json={
            "name": "Northern Territories",
            "code": "northern_territories",
            "description": "Gilgit, Skardu, and Hunza high-altitude regions",
            "cities": ["Gilgit", "Skardu", "Hunza"],
            "is_active": True,
        },
    )
    assert new_zone_res.status_code == 201
    assert new_zone_res.json()["code"] == "northern_territories"
