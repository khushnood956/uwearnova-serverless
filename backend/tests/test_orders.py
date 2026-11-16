"""
Order and Checkout Lifecycle Tests (Module M12)
Validates transactional checkout, cart empty/unavailable validation, authoritative
backend recalculation, stock reservation, idempotency replay/conflict handling,
immutable snapshots, customer isolation, and administrative order state transitions.
"""

from decimal import Decimal
import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductImage, ProductVariant
from app.modules.cart.service import add_item_to_cart, get_or_create_cart
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.service import get_or_create_default_location
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.shipping.service import ensure_default_shipping_configuration


@pytest.fixture
async def seeded_order_env():
    """Seeds RBAC, default shipping methods, products, variants, and test users."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        # Seed RBAC and Shipping
        await seed_system_roles_and_permissions(session)
        await ensure_default_shipping_configuration(session)
        loc = await get_or_create_default_location(session)

        # Seed Catalog Items
        cat = Category(name="Apparel", slug="apparel", is_active=True)
        session.add(cat)
        await session.flush()

        # Product 1: Blazer (PKR 48,000)
        p1 = Product(
            name="Double Breasted Wool Blazer",
            slug="double-breasted-wool-blazer",
            category_id=cat.id,
            price=Decimal("48000.00"),
            status="active",
        )
        session.add(p1)
        await session.flush()

        v1 = ProductVariant(
            product_id=p1.id,
            sku="DB-BLAZER-40R",
            size="40R",
            color_name="Charcoal Grey",
            inventory_count=10,
            in_stock=True,
            is_active=True,
        )
        session.add(v1)
        await session.flush()

        inv1 = InventoryItem(
            variant_id=v1.id,
            location_id=loc.id,
            quantity_on_hand=10,
            quantity_reserved=0,
        )
        session.add(inv1)

        img1 = ProductImage(
            product_id=p1.id,
            image_url="https://cdn.uninova.pk/products/blazer-front.webp",
            is_primary=True,
            sort_order=0,
        )
        session.add(img1)

        # Product 2: Kurta (PKR 8,500)
        p2 = Product(
            name="Egyptian Cotton Kurta",
            slug="egyptian-cotton-kurta",
            category_id=cat.id,
            price=Decimal("8500.00"),
            status="active",
        )
        session.add(p2)
        await session.flush()

        v2 = ProductVariant(
            product_id=p2.id,
            sku="EG-KURTA-M",
            size="M",
            color_name="Pristine White",
            inventory_count=5,
            in_stock=True,
            is_active=True,
        )
        session.add(v2)
        await session.flush()

        inv2 = InventoryItem(
            variant_id=v2.id,
            location_id=loc.id,
            quantity_on_hand=5,
            quantity_reserved=0,
        )
        session.add(inv2)

        # Product 3: Low stock Kurta (PKR 6,000, 1 in stock)
        p3 = Product(
            name="Linen Casual Shirt",
            slug="linen-casual-shirt",
            category_id=cat.id,
            price=Decimal("6000.00"),
            status="active",
        )
        session.add(p3)
        await session.flush()

        v3 = ProductVariant(
            product_id=p3.id,
            sku="LINEN-SHIRT-S",
            size="S",
            color_name="Sky Blue",
            inventory_count=1,
            in_stock=True,
            is_active=True,
        )
        session.add(v3)
        await session.flush()

        inv3 = InventoryItem(
            variant_id=v3.id,
            location_id=loc.id,
            quantity_on_hand=1,
            quantity_reserved=0,
        )
        session.add(inv3)

        # Users
        u1 = User(
            email="alice_orders@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        u2 = User(
            email="bob_orders@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        admin = User(
            email="admin_orders@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        session.add_all([u1, u2, admin])
        await session.flush()

        # Assign store_admin role to admin
        admin_role_stmt = select(Role).where(Role.name == "store_admin")
        res = await session.execute(admin_role_stmt)
        admin_role = res.scalar_one()
        await session.execute(
            user_roles.insert().values(user_id=admin.id, role_id=admin_role.id)
        )

        await session.commit()
        await session.refresh(u1)
        await session.refresh(u2)
        await session.refresh(admin)
        await session.refresh(v1)
        await session.refresh(v2)
        await session.refresh(v3)

        return {
            "alice": u1,
            "bob": u2,
            "admin": admin,
            "variant_blazer": v1,
            "variant_kurta": v2,
            "variant_linen": v3,
        }


def make_valid_checkout_payload(
    customer_name: str = "Alice Khan",
    customer_email: str = "alice_orders@example.com",
    customer_phone: str = "03001234567",
    shipping_method_code: str = "standard_delivery",
    payment_method: str = "cod",
    idempotency_key: str = None,
    city: str = "Lahore",
    note: str = None,
) -> dict:
    return {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "shipping_method_code": shipping_method_code,
        "payment_method": payment_method,
        "customer_note": note,
        "idempotency_key": idempotency_key,
        "shipping_address": {
            "full_name": customer_name,
            "phone": customer_phone,
            "address_line_1": "House 42, Street 8, Sector Y, DHA Phase 3",
            "city": city,
            "postal_code": "54000",
            "country_code": "PK",
        },
    }


@pytest.mark.asyncio
async def test_checkout_authenticated_customer_success(async_client: AsyncClient, seeded_order_env):
    """
    Validates full transactional checkout for an authenticated customer:
    - Authoritative price calculation
    - Free shipping threshold evaluation (Blazer PKR 48,000 >= PKR 15,000 -> PKR 0.00 shipping)
    - Safe inventory reservation
    - Unpaid initial payment status
    - Cart cleared post-checkout
    """
    env = seeded_order_env
    alice = env["alice"]
    v1 = env["variant_blazer"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Add Blazer (PKR 48,000) to Alice's cart
    add_res = await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers=headers,
    )
    assert add_res.status_code == 200

    # 2. Checkout
    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        shipping_method_code="standard_delivery",
        payment_method="cod",
        idempotency_key="alice-order-key-001",
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res.status_code == 201
    order = res.json()

    assert order["order_number"].startswith("UNV-")
    assert order["status"] == "pending_confirmation"
    assert order["payment_status"] == "unpaid"  # Never marked as paid upon order creation!
    assert order["fulfillment_status"] == "unfulfilled"
    assert order["payment_method"] == "cod"
    assert Decimal(order["subtotal"]) == Decimal("48000.00")
    assert Decimal(order["shipping_total"]) == Decimal("0.00")  # Free shipping threshold met
    assert Decimal(order["grand_total"]) == Decimal("48000.00")
    assert len(order["items"]) == 1
    assert order["items"][0]["sku"] == "DB-BLAZER-40R"
    assert order["items"][0]["product_name"] == "Double Breasted Wool Blazer"
    assert order["items"][0]["size"] == "40R"
    assert Decimal(order["items"][0]["unit_price"]) == Decimal("48000.00")

    # Verify status history initial record
    assert len(order["status_history"]) >= 1
    assert order["status_history"][0]["to_status"] == "pending_confirmation"

    # 3. Verify cart is now empty
    cart_res = await async_client.get("/api/v1/cart", headers=headers)
    assert cart_res.status_code == 200
    assert cart_res.json()["total_items"] == 0

    # 4. Verify inventory reservation in database
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        inv_stmt = select(InventoryItem).where(InventoryItem.variant_id == v1.id)
        inv_res = await session.execute(inv_stmt)
        inv_item = inv_res.scalar_one()
        assert inv_item.quantity_reserved == 1
        assert inv_item.quantity_on_hand == 10
        assert inv_item.quantity_available == 9


@pytest.mark.asyncio
async def test_checkout_guest_anonymous_success(async_client: AsyncClient, seeded_order_env):
    """
    Validates guest checkout with anonymous cart token:
    - Calculates standard delivery charge (PKR 350) since subtotal PKR 8,500 < PKR 15,000 threshold
    - Creates order without user_id
    - Empties anonymous cart
    """
    env = seeded_order_env
    v2 = env["variant_kurta"]
    anon_token = "guest-cart-tok-999"
    headers = {"X-Anonymous-Cart-Token": anon_token}

    # 1. Add Kurta (PKR 8,500)
    add_res = await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v2.id, "quantity": 1},
        headers=headers,
    )
    assert add_res.status_code == 200

    # 2. Checkout anonymously
    checkout_data = make_valid_checkout_payload(
        customer_name="Tariq Guest",
        customer_email="tariq@example.com",
        customer_phone="03219876543",
        shipping_method_code="standard_delivery",
        payment_method="cod",
        idempotency_key="anon-order-key-002",
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res.status_code == 201
    order = res.json()

    assert order["order_number"].startswith("UNV-")
    assert order["payment_status"] == "unpaid"
    assert Decimal(order["subtotal"]) == Decimal("8500.00")
    assert Decimal(order["shipping_total"]) == Decimal("350.00")
    assert Decimal(order["grand_total"]) == Decimal("8850.00")

    # Verify anonymous cart cleared
    cart_res = await async_client.get("/api/v1/cart", headers=headers)
    assert cart_res.status_code == 200
    assert cart_res.json()["total_items"] == 0


@pytest.mark.asyncio
async def test_checkout_empty_cart_fails(async_client: AsyncClient, seeded_order_env):
    """Attempting checkout with an empty cart must be rejected with 400 Bad Request."""
    env = seeded_order_env
    alice = env["alice"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key="empty-cart-key",
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res.status_code == 400
    assert "CART_EMPTY" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_checkout_idempotency_replay_identical_payload(async_client: AsyncClient, seeded_order_env):
    """
    Idempotent replay: Submitting identical checkout request with the same idempotency key
    returns the cached order response without double-booking inventory.
    """
    env = seeded_order_env
    alice = env["alice"]
    v1 = env["variant_blazer"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Add item
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers=headers,
    )

    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key="idemp-key-repeat-777",
    )

    # 1st call
    res1 = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res1.status_code == 201
    order1 = res1.json()

    # 2nd call with identical idempotency key and payload
    res2 = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res2.status_code == 200 or res2.status_code == 201
    order2 = res2.json()

    assert order1["order_number"] == order2["order_number"]
    assert order1["id"] == order2["id"]

    # Verify inventory was NOT reserved twice
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        inv_stmt = select(InventoryItem).where(InventoryItem.variant_id == v1.id)
        inv_res = await session.execute(inv_stmt)
        inv_item = inv_res.scalar_one()
        assert inv_item.quantity_reserved == 1  # only 1 reserved, not 2


@pytest.mark.asyncio
async def test_checkout_idempotency_conflict_different_payload(async_client: AsyncClient, seeded_order_env):
    """
    Reusing the same idempotency key with different order parameters returns 409 Conflict.
    """
    env = seeded_order_env
    alice = env["alice"]
    v1 = env["variant_blazer"]
    v2 = env["variant_kurta"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Add item
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers=headers,
    )

    shared_key = "idemp-key-conflict-888"
    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key=shared_key,
        note="First order notes",
    )

    res1 = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res1.status_code == 201

    # Second request with same idempotency key but altered customer note (triggers payload conflict)
    conflicting_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key=shared_key,
        note="Altered notes for conflicting request",
    )
    res2 = await async_client.post(
        "/api/v1/orders/checkout",
        json=conflicting_data,
        headers=headers,
    )
    assert res2.status_code == 409
    assert "IDEMPOTENCY_CONFLICT" in res2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_checkout_insufficient_stock_fails(async_client: AsyncClient, seeded_order_env):
    """
    When item inventory is exhausted between carting and checkout, checkout is aborted,
    returning 400 Bad Request and rolling back transactions.
    """
    env = seeded_order_env
    alice = env["alice"]
    v3 = env["variant_linen"]  # Only 1 in stock
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Alice adds the last 1 item
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v3.id, "quantity": 1},
        headers=headers,
    )

    # Simulate concurrent inventory drop to 0
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        inv_stmt = select(InventoryItem).where(InventoryItem.variant_id == v3.id)
        inv_res = await session.execute(inv_stmt)
        inv_item = inv_res.scalar_one()
        inv_item.quantity_on_hand = 0
        await session.commit()

    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key="insufficient-stock-key",
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_order_retrieval_and_customer_isolation(async_client: AsyncClient, seeded_order_env):
    """
    Validates customer ownership boundaries:
    - Alice can retrieve her own order
    - Bob cannot view Alice's order (returns 404)
    - Alice's account list returns only Alice's orders
    """
    env = seeded_order_env
    alice = env["alice"]
    bob = env["bob"]
    v1 = env["variant_blazer"]

    alice_token = create_access_token(alice.id)
    bob_token = create_access_token(bob.id)

    # Alice adds item and checks out
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key="alice-order-isolation-test",
    )
    create_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert create_res.status_code == 201
    order_num = create_res.json()["order_number"]

    # 1. Alice retrieves order -> 200 OK
    get_alice = await async_client.get(
        f"/api/v1/orders/{order_num}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert get_alice.status_code == 200
    assert get_alice.json()["order_number"] == order_num

    # 2. Bob attempts to retrieve Alice's order -> 404 Not Found
    get_bob = await async_client.get(
        f"/api/v1/orders/{order_num}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert get_bob.status_code == 404

    # 3. Customer account orders list
    alice_list = await async_client.get(
        "/api/v1/customer/orders",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert alice_list.status_code == 200
    assert alice_list.json()["total"] >= 1

    bob_list = await async_client.get(
        "/api/v1/customer/orders",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_list.status_code == 200
    assert bob_list.json()["total"] == 0


@pytest.mark.asyncio
async def test_order_lifecycle_transitions_and_cancellation_restock(async_client: AsyncClient, seeded_order_env):
    """
    Validates state machine transitions and stock restoration:
    - pending_confirmation -> confirmed (allowed)
    - confirmed -> processing (allowed)
    - processing -> delivered (invalid, rejected)
    - processing -> cancelled (allowed, releases reserved stock)
    - cancelled -> confirmed (terminal state, rejected)
    """
    env = seeded_order_env
    alice = env["alice"]
    admin = env["admin"]
    v2 = env["variant_kurta"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)

    # Place order for 2 Kurta items
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v2.id, "quantity": 2},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key="lifecycle-test-001",
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res.status_code == 201
    order_id = res.json()["id"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Transition 1: pending_confirmation -> confirmed
    t1 = await async_client.patch(
        f"/api/v1/admin/orders/{order_id}/status",
        json={"to_status": "confirmed", "note": "Customer verified via phone call"},
        headers=admin_headers,
    )
    assert t1.status_code == 200
    assert t1.json()["status"] == "confirmed"

    # Transition 2: confirmed -> processing
    t2 = await async_client.patch(
        f"/api/v1/admin/orders/{order_id}/status",
        json={"to_status": "processing", "note": "Moved to cutting room"},
        headers=admin_headers,
    )
    assert t2.status_code == 200
    assert t2.json()["status"] == "processing"

    # Transition 3: Invalid leap processing -> delivered (must be packed -> shipped first)
    t3 = await async_client.patch(
        f"/api/v1/admin/orders/{order_id}/status",
        json={"to_status": "delivered", "note": "Skipping packaging"},
        headers=admin_headers,
    )
    assert t3.status_code == 400
    assert "INVALID_STATUS_TRANSITION" in t3.json()["error"]["message"]

    # Transition 4: processing -> cancelled (releases held inventory)
    t4 = await async_client.patch(
        f"/api/v1/admin/orders/{order_id}/status",
        json={"to_status": "cancelled", "note": "Customer requested cancellation prior to packing"},
        headers=admin_headers,
    )
    assert t4.status_code == 200
    assert t4.json()["status"] == "cancelled"

    # Verify inventory reserved count was restored back to 0
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        inv_stmt = select(InventoryItem).where(InventoryItem.variant_id == v2.id)
        inv_res = await session.execute(inv_stmt)
        inv_item = inv_res.scalar_one()
        assert inv_item.quantity_reserved == 0

    # Transition 5: Attempting to revive cancelled order -> rejected
    t5 = await async_client.patch(
        f"/api/v1/admin/orders/{order_id}/status",
        json={"to_status": "confirmed", "note": "Attempt to revive"},
        headers=admin_headers,
    )
    assert t5.status_code == 400


@pytest.mark.asyncio
async def test_admin_orders_rbac_access_control(async_client: AsyncClient, seeded_order_env):
    """
    Validates RBAC protection on administrative order endpoints:
    - Customer cannot view administrative order queue (403)
    - Customer cannot update order status (403)
    - Unauthenticated user cannot access administrative queue (401)
    - Store admin can view queue and update status
    """
    env = seeded_order_env
    alice = env["alice"]
    admin = env["admin"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)

    # 1. Unauthenticated -> 401
    r_unauth = await async_client.get("/api/v1/admin/orders")
    assert r_unauth.status_code == 401

    # 2. Customer -> 403
    r_cust = await async_client.get(
        "/api/v1/admin/orders",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert r_cust.status_code == 403

    # 3. Admin -> 200
    r_admin = await async_client.get(
        "/api/v1/admin/orders",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r_admin.status_code == 200
    assert "orders" in r_admin.json()


@pytest.mark.asyncio
async def test_checkout_header_idempotency_key(async_client: AsyncClient, seeded_order_env):
    """Verifies that Idempotency-Key passed via HTTP request header is respected."""
    env = seeded_order_env
    alice = env["alice"]
    v1 = env["variant_blazer"]
    token = create_access_token(alice.id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "header-idemp-key-555",
    }

    # Add item
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers=headers,
    )

    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key=None,  # Not in body, sent in header
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res.status_code == 201
    order1 = res.json()

    # Repeat with same header
    res2 = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers=headers,
    )
    assert res2.status_code in (200, 201)
    order2 = res2.json()
    assert order1["order_number"] == order2["order_number"]


@pytest.mark.asyncio
async def test_checkout_validation_failures(async_client: AsyncClient, seeded_order_env):
    """Validates bad phone format and invalid shipping method rejections."""
    env = seeded_order_env
    alice = env["alice"]
    v2 = env["variant_kurta"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v2.id, "quantity": 1},
        headers=headers,
    )

    # 1. Invalid phone number format -> 422
    bad_phone_payload = make_valid_checkout_payload(
        customer_phone="invalid-phone-123",
    )
    r1 = await async_client.post(
        "/api/v1/orders/checkout",
        json=bad_phone_payload,
        headers=headers,
    )
    assert r1.status_code == 422

    # 2. Invalid shipping method code -> 400
    bad_shipping_payload = make_valid_checkout_payload(
        shipping_method_code="teleportation_express",
    )
    r2 = await async_client.post(
        "/api/v1/orders/checkout",
        json=bad_shipping_payload,
        headers=headers,
    )
    assert r2.status_code == 400
    assert "INVALID_SHIPPING_METHOD" in r2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_admin_order_search_and_lifecycle_completion(async_client: AsyncClient, seeded_order_env):
    """
    Tests administrative filtering and full delivery-to-refund lifecycle:
    pending_confirmation -> confirmed -> processing -> packed -> shipped -> delivered -> return_requested -> returned -> refunded
    """
    env = seeded_order_env
    alice = env["alice"]
    admin = env["admin"]
    v1 = env["variant_blazer"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Place order
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_data = make_valid_checkout_payload(
        customer_name="Alice Khan",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key="full-lifecycle-key-777",
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_data,
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res.status_code == 201
    order_id = res.json()["id"]
    order_num = res.json()["order_number"]

    # Filter by search
    search_res = await async_client.get(
        f"/api/v1/admin/orders?search={order_num}",
        headers=admin_headers,
    )
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert search_res.json()["orders"][0]["order_number"] == order_num

    # Filter by status
    pending_res = await async_client.get(
        "/api/v1/admin/orders?status=pending_confirmation",
        headers=admin_headers,
    )
    assert pending_res.status_code == 200
    assert pending_res.json()["total"] >= 1

    # Walk through lifecycle states
    steps = [
        ("confirmed", "Verified by phone"),
        ("processing", "Sent to fulfillment center"),
        ("packed", "Packed in UniNova gift box"),
        ("shipped", "Dispatched with BlueEx AWB# 123456"),
        ("delivered", "Signed by customer"),
        ("return_requested", "Customer requested size exchange"),
        ("returned", "Item received back at warehouse inspection"),
        ("refunded", "Store credit voucher issued"),
    ]

    for to_status, note in steps:
        patch_res = await async_client.patch(
            f"/api/v1/admin/orders/{order_id}/status",
            json={"to_status": to_status, "note": note},
            headers=admin_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == to_status

    # Verify final history count
    final_get = await async_client.get(
        f"/api/v1/orders/{order_num}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert final_get.status_code == 200
    assert final_get.json()["status"] == "refunded"
    # Initial status entry + 8 transitions = 9 history records
    assert len(final_get.json()["status_history"]) == 9
