"""
Inventory Management Tests (Module M09)
Tests warehouse location tracking, stock adjustments, reservations, releases,
non-negative stock prevention, concurrent updates, low-stock thresholds,
movement ledger history, and RBAC authorization.
"""

import asyncio
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.inventory.models import InventoryItem, InventoryLocation, InventoryMovement
from app.modules.inventory.service import get_or_create_default_location
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions


@pytest.fixture
async def seeded_inventory_env():
    """Fixture that seeds roles and creates a sample catalog product with a variant."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await get_or_create_default_location(session)

        # Create category
        cat = Category(name="Men", slug="men", is_active=True)
        session.add(cat)
        await session.flush()

        # Create product
        prod = Product(
            name="Tailored Double-Breasted Blazer",
            slug="tailored-double-breasted-blazer",
            category_id=cat.id,
            price=Decimal("48000.00"),
            status="active",
        )
        session.add(prod)
        await session.flush()

        # Create variant
        variant = ProductVariant(
            product_id=prod.id,
            sku="TDB-BLAZER-BLK-40R",
            size="40R",
            color_name="Obsidian Black",
            color_hex="#111111",
            inventory_count=0,
            in_stock=False,
            is_active=True,
        )
        session.add(variant)
        await session.flush()

        # Seed initial inventory item
        default_loc = await get_or_create_default_location(session)
        item = InventoryItem(
            variant_id=variant.id,
            location_id=default_loc.id,
            quantity_on_hand=0,
            quantity_reserved=0,
            reorder_threshold=5,
        )
        session.add(item)
        await session.commit()
        await session.refresh(variant)
        return variant.id


async def create_user_with_role(
    session: AsyncSession,
    email: str,
    role_name: str,
    user_type: str = "staff",
) -> User:
    """Helper to create a user with an assigned role."""
    user = User(
        email=email,
        password_hash=hash_password("SecurePass123!"),
        status="active",
        user_type=user_type,
    )
    session.add(user)
    await session.flush()

    role_res = await session.execute(select(Role).where(Role.name == role_name))
    role = role_res.scalar_one()

    await session.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))
    await session.commit()
    await session.refresh(user)
    return user


def auth_header_for(user: User) -> dict:
    """Generate authorization header with valid JWT token."""
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Location Management Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_location_management(async_client: AsyncClient, seeded_inventory_env):
    """Verify default location bootstrapping and secondary location creation."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_loc@example.com", "store_admin")

    headers = auth_header_for(admin)

    # 1. List locations (bootstraps primary warehouse)
    list_res = await async_client.get("/api/v1/admin/inventory/locations", headers=headers)
    assert list_res.status_code == 200
    locs = list_res.json()
    assert len(locs) >= 1
    assert any(l["code"] == "WH-PRIMARY" for l in locs)

    # 2. Create secondary fulfillment warehouse
    create_payload = {
        "name": "Lahore Regional Hub",
        "code": "LHE-WH-02",
        "address_line_1": "Gulberg III",
        "city": "Lahore",
        "postal_code": "54000",
        "country_code": "PK",
        "is_active": True,
    }
    create_res = await async_client.post(
        "/api/v1/admin/inventory/locations",
        headers=headers,
        json=create_payload,
    )
    assert create_res.status_code == 201
    created_loc = create_res.json()
    assert created_loc["code"] == "LHE-WH-02"
    assert created_loc["name"] == "Lahore Regional Hub"


# ===========================================================================
# 2. Stock Adjustment & Variant Synchronization Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_stock_adjustment_intake_and_catalog_sync(async_client: AsyncClient, seeded_inventory_env):
    """Verify stock receipt intake increments on-hand and syncs variant availability."""
    variant_id = seeded_inventory_env
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        manager = await create_user_with_role(session, "manager_intake@example.com", "inventory_manager")

    headers = auth_header_for(manager)

    # Intake +25 units
    adjust_payload = {
        "variant_id": variant_id,
        "quantity_delta": 25,
        "reason": "receipt",
        "notes": "Initial batch production intake from Karachi workshop",
        "reference_type": "purchase_order",
        "reference_id": "PO-2026-001",
    }
    res = await async_client.post("/api/v1/admin/inventory/adjust", headers=headers, json=adjust_payload)
    assert res.status_code == 200
    data = res.json()

    item = data["item"]
    movement = data["movement"]

    assert item["quantity_on_hand"] == 25
    assert item["quantity_reserved"] == 0
    assert item["quantity_available"] == 25
    assert item["variant_sku"] == "TDB-BLAZER-BLK-40R"

    assert movement["quantity_delta"] == 25
    assert movement["quantity_on_hand_before"] == 0
    assert movement["quantity_on_hand_after"] == 25
    assert movement["movement_type"] == "receipt"
    assert movement["reason_notes"] == "Initial batch production intake from Karachi workshop"

    # Verify ProductVariant in database is synchronized
    async with TestingSessionLocal() as session:
        v_res = await session.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
        variant = v_res.scalar_one()
        assert variant.inventory_count == 25
        assert variant.in_stock is True


@pytest.mark.asyncio
async def test_stock_adjustment_decrement_and_insufficient_stock(async_client: AsyncClient, seeded_inventory_env):
    """Verify stock decrement operations and prevention of negative inventory."""
    variant_id = seeded_inventory_env
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        manager = await create_user_with_role(session, "manager_dec@example.com", "inventory_manager")

    headers = auth_header_for(manager)

    # 1. Intake 10 units
    await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=headers,
        json={"variant_id": variant_id, "quantity_delta": 10, "reason": "receipt"},
    )

    # 2. Decrement 3 units (e.g. damaged during inspection)
    dec_res = await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=headers,
        json={
            "variant_id": variant_id,
            "quantity_delta": -3,
            "reason": "damaged",
            "notes": "Fabric snag identified during inspection",
        },
    )
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["item"]["quantity_on_hand"] == 7
    assert dec_data["item"]["quantity_available"] == 7
    assert dec_data["movement"]["quantity_on_hand_before"] == 10
    assert dec_data["movement"]["quantity_on_hand_after"] == 7

    # 3. Attempt negative adjustment exceeding on hand (e.g. -10 when on hand is 7)
    invalid_res = await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=headers,
        json={
            "variant_id": variant_id,
            "quantity_delta": -10,
            "reason": "adjustment",
            "notes": "Excess decrement test",
        },
    )
    assert invalid_res.status_code == 400
    assert "INSUFFICIENT_STOCK" in invalid_res.json()["error"]["message"]

    # Verify database state remained 7
    async with TestingSessionLocal() as session:
        v_res = await session.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
        variant = v_res.scalar_one()
        assert variant.inventory_count == 7


# ===========================================================================
# 3. Stock Reservation & Release Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_stock_reservation_and_release_lifecycle(async_client: AsyncClient, seeded_inventory_env):
    """Verify stock reservations reduce available stock and releases restore available pool."""
    variant_id = seeded_inventory_env
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        manager = await create_user_with_role(session, "manager_reserve@example.com", "inventory_manager")

    headers = auth_header_for(manager)

    # Initial stock: 10 units
    await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=headers,
        json={"variant_id": variant_id, "quantity_delta": 10, "reason": "receipt"},
    )

    # 1. Reserve 4 units for checkout hold
    res_res = await async_client.post(
        "/api/v1/admin/inventory/reserve",
        headers=headers,
        json={
            "variant_id": variant_id,
            "quantity": 4,
            "reference_type": "checkout_hold",
            "reference_id": "HOLD-98712",
        },
    )
    assert res_res.status_code == 200
    data = res_res.json()
    assert data["item"]["quantity_on_hand"] == 10
    assert data["item"]["quantity_reserved"] == 4
    assert data["item"]["quantity_available"] == 6

    # Verify variant available count dropped to 6
    async with TestingSessionLocal() as session:
        v_res = await session.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
        assert v_res.scalar_one().inventory_count == 6

    # 2. Attempt over-reservation (requesting 7 units when only 6 available)
    over_reserve = await async_client.post(
        "/api/v1/admin/inventory/reserve",
        headers=headers,
        json={"variant_id": variant_id, "quantity": 7},
    )
    assert over_reserve.status_code == 400
    assert "INSUFFICIENT_STOCK" in over_reserve.json()["error"]["message"]

    # 3. Attempt adjustment that would lower on-hand below reserved quantity
    invalid_adj = await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=headers,
        json={"variant_id": variant_id, "quantity_delta": -7},  # 10 - 7 = 3, but 4 reserved
    )
    assert invalid_adj.status_code == 400
    assert "INSUFFICIENT_STOCK" in invalid_adj.json()["error"]["message"]

    # 4. Release 3 reserved units
    release_res = await async_client.post(
        "/api/v1/admin/inventory/release",
        headers=headers,
        json={
            "variant_id": variant_id,
            "quantity": 3,
            "reference_type": "checkout_expired",
            "reference_id": "HOLD-98712",
        },
    )
    assert release_res.status_code == 200
    rel_data = release_res.json()
    assert rel_data["item"]["quantity_reserved"] == 1
    assert rel_data["item"]["quantity_available"] == 9

    # 5. Attempt invalid release (trying to release 5 units when only 1 is reserved)
    invalid_rel = await async_client.post(
        "/api/v1/admin/inventory/release",
        headers=headers,
        json={"variant_id": variant_id, "quantity": 5},
    )
    assert invalid_rel.status_code == 400
    assert "INVALID_RELEASE_QUANTITY" in invalid_rel.json()["error"]["message"]


# ===========================================================================
# 4. Low-Stock Threshold & Filtering Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_low_stock_threshold_and_endpoints(async_client: AsyncClient, seeded_inventory_env):
    """Verify threshold evaluation and dedicated low-stock filter endpoints."""
    variant_id = seeded_inventory_env
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_thresh@example.com", "store_admin")

    headers = auth_header_for(admin)

    # 1. Intake 4 units (default threshold is 5, so available 4 <= 5 should be low-stock)
    await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=headers,
        json={"variant_id": variant_id, "quantity_delta": 4, "reason": "receipt"},
    )

    # 2. Check low stock endpoint
    low_res = await async_client.get("/api/v1/admin/inventory/low-stock", headers=headers)
    assert low_res.status_code == 200
    low_items = low_res.json()["items"]
    assert len(low_items) == 1
    assert low_items[0]["is_low_stock"] is True
    location_id = low_items[0]["location_id"]

    # 3. Update reorder threshold to 2 via PATCH
    thresh_res = await async_client.patch(
        f"/api/v1/admin/inventory/variants/{variant_id}/locations/{location_id}/threshold",
        headers=headers,
        json={"reorder_threshold": 2},
    )
    assert thresh_res.status_code == 200
    assert thresh_res.json()["reorder_threshold"] == 2
    assert thresh_res.json()["is_low_stock"] is False  # available 4 > threshold 2

    # 4. Low stock endpoint now returns empty
    low_res2 = await async_client.get("/api/v1/admin/inventory/low-stock", headers=headers)
    assert low_res2.status_code == 200
    assert len(low_res2.json()["items"]) == 0


# ===========================================================================
# 5. Inventory Movement Ledger Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_inventory_movement_ledger(async_client: AsyncClient, seeded_inventory_env):
    """Verify chronological movement ledger and filtering capabilities."""
    variant_id = seeded_inventory_env
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        manager = await create_user_with_role(session, "manager_ledger@example.com", "inventory_manager")

    headers = auth_header_for(manager)

    # Execute a receipt and a reservation
    await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=headers,
        json={"variant_id": variant_id, "quantity_delta": 20, "reason": "receipt"},
    )
    await async_client.post(
        "/api/v1/admin/inventory/reserve",
        headers=headers,
        json={"variant_id": variant_id, "quantity": 5, "reference_type": "checkout_hold"},
    )

    # Query movements
    mov_res = await async_client.get(
        f"/api/v1/admin/inventory/movements?variant_id={variant_id}",
        headers=headers,
    )
    assert mov_res.status_code == 200
    movements = mov_res.json()["movements"]
    assert len(movements) == 2

    # Most recent first
    assert movements[0]["movement_type"] == "reservation"
    assert movements[0]["quantity_delta"] == -5
    assert movements[1]["movement_type"] == "receipt"
    assert movements[1]["quantity_delta"] == 20

    # Filter by movement_type
    filter_res = await async_client.get(
        "/api/v1/admin/inventory/movements?movement_type=reservation",
        headers=headers,
    )
    assert filter_res.status_code == 200
    assert all(m["movement_type"] == "reservation" for m in filter_res.json()["movements"])


# ===========================================================================
# 6. Concurrency & Integrity Safety Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_concurrent_inventory_adjustments(async_client: AsyncClient, seeded_inventory_env):
    """Verify concurrent stock adjustments execute without state corruption."""
    variant_id = seeded_inventory_env
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        manager = await create_user_with_role(session, "manager_concurrency@example.com", "inventory_manager")

    headers = auth_header_for(manager)

    # Launch 5 concurrent +5 stock increments
    tasks = [
        async_client.post(
            "/api/v1/admin/inventory/adjust",
            headers=headers,
            json={"variant_id": variant_id, "quantity_delta": 5, "reason": "adjustment", "notes": f"Batch {i}"},
        )
        for i in range(5)
    ]
    results = await asyncio.gather(*tasks)
    for r in results:
        assert r.status_code == 200

    # Verify final stock is exactly 25
    inv_res = await async_client.get(f"/api/v1/admin/inventory?search=TDB-BLAZER", headers=headers)
    assert inv_res.status_code == 200
    item = inv_res.json()["items"][0]
    assert item["quantity_on_hand"] == 25
    assert item["quantity_available"] == 25


# ===========================================================================
# 7. RBAC & Access Control Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_inventory_rbac_protection(async_client: AsyncClient, seeded_inventory_env):
    """Verify unauthorized actors and regular customers cannot read or adjust inventory."""
    variant_id = seeded_inventory_env
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        customer = await create_user_with_role(session, "cust_inv@example.com", "customer", user_type="customer")
        support = await create_user_with_role(session, "supp_inv@example.com", "customer_support", user_type="staff")

    cust_headers = auth_header_for(customer)
    supp_headers = auth_header_for(support)

    # 1. Anonymous request rejected
    anon_res = await async_client.get("/api/v1/admin/inventory")
    assert anon_res.status_code == 401

    # 2. Customer token rejected (403 Forbidden)
    cust_res = await async_client.get("/api/v1/admin/inventory", headers=cust_headers)
    assert cust_res.status_code == 403

    # 3. Customer support has no inventory.adjust permission
    support_adjust = await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=supp_headers,
        json={"variant_id": variant_id, "quantity_delta": 10, "reason": "adjustment"},
    )
    assert support_adjust.status_code == 403
