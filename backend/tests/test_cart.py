"""
Cart and Wishlist Tests (Module M10)
Tests server-side cart calculation, trusted price re-computation from catalogue,
availability validation, cross-customer ownership isolation, guest cart creation,
guest cart merging, and customer wishlist CRUD.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductImage, ProductVariant
from app.modules.cart.models import Cart, CartItem, Wishlist, WishlistItem
from app.modules.inventory.models import InventoryItem, InventoryLocation
from app.modules.inventory.service import get_or_create_default_location


@pytest.fixture
async def seeded_cart_env():
    """Seeds two catalog products with variants and inventory for cart tests."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        # Create category
        cat = Category(name="Apparel", slug="apparel", is_active=True)
        session.add(cat)
        await session.flush()

        # Create primary warehouse location
        loc = await get_or_create_default_location(session)

        # 1. Product 1: In-stock Blazer (PKR 48,000)
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

        # Seed inventory item for v1
        inv1 = InventoryItem(
            variant_id=v1.id,
            location_id=loc.id,
            quantity_on_hand=10,
            quantity_reserved=0,
        )
        session.add(inv1)

        # Primary image for p1
        img1 = ProductImage(
            product_id=p1.id,
            image_url="https://cdn.uninova.pk/products/blazer-front.webp",
            is_primary=True,
            sort_order=0,
        )
        session.add(img1)

        # 2. Product 2: Lower-price Kurta (PKR 8,500)
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

        # 3. Product 3: Out of Stock Silk Scarf (PKR 12,000)
        p3 = Product(
            name="Raw Silk Printed Scarf",
            slug="raw-silk-printed-scarf",
            category_id=cat.id,
            price=Decimal("12000.00"),
            status="active",
        )
        session.add(p3)
        await session.flush()

        v3 = ProductVariant(
            product_id=p3.id,
            sku="SILK-SCARF-OS",
            size="One Size",
            color_name="Burgundy Pattern",
            inventory_count=0,
            in_stock=False,
            is_active=True,
        )
        session.add(v3)
        await session.flush()

        # 4. Product 4: Inactive / Draft Trench Coat
        p4 = Product(
            name="Draft Trench Coat",
            slug="draft-trench-coat",
            category_id=cat.id,
            price=Decimal("35000.00"),
            status="draft",
        )
        session.add(p4)
        await session.flush()

        v4 = ProductVariant(
            product_id=p4.id,
            sku="TRENCH-DRAFT-L",
            size="L",
            color_name="Khaki",
            inventory_count=10,
            in_stock=True,
            is_active=False,
        )
        session.add(v4)

        # 5. Customer Users
        u1 = User(
            email="customer_alice@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        u2 = User(
            email="customer_bob@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        session.add_all([u1, u2])
        await session.commit()
        await session.refresh(v1)
        await session.refresh(v2)
        await session.refresh(v3)
        await session.refresh(v4)
        await session.refresh(u1)
        await session.refresh(u2)

        return {
            "p1_id": p1.id,
            "v1_id": v1.id,
            "p2_id": p2.id,
            "v2_id": v2.id,
            "p3_id": p3.id,
            "v3_id": v3.id,
            "p4_id": p4.id,
            "v4_id": v4.id,
            "u1": u1,
            "u2": u2,
        }


def auth_header_for(user: User) -> dict:
    """Helper to generate JWT bearer header."""
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Authenticated Customer Cart CRUD & Calculations
# ===========================================================================

@pytest.mark.asyncio
async def test_customer_cart_crud_and_pricing(async_client: AsyncClient, seeded_cart_env):
    """Verify customer cart item addition, recalculation, update, and deletion."""
    env = seeded_cart_env
    headers = auth_header_for(env["u1"])

    # 1. Initially empty cart
    get_res = await async_client.get("/api/v1/cart", headers=headers)
    assert get_res.status_code == 200
    cart_data = get_res.json()
    assert cart_data["total_items"] == 0
    assert cart_data["subtotal"] == "0.00"

    # 2. Add Kurta (PKR 8,500 x 1)
    add_res = await async_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"variant_id": env["v2_id"], "quantity": 1},
    )
    assert add_res.status_code == 200
    cart1 = add_res.json()
    assert cart1["total_items"] == 1
    assert Decimal(cart1["subtotal"]) == Decimal("8500.00")
    assert cart1["is_free_shipping"] is False
    assert Decimal(cart1["amount_needed_for_free_shipping"]) == Decimal("6500.00")  # 15000 - 8500

    item_id = cart1["items"][0]["id"]
    assert cart1["items"][0]["variant_sku"] == "EG-KURTA-M"
    assert cart1["items"][0]["unit_price"] == "8500.00"
    assert cart1["items"][0]["line_total"] == "8500.00"

    # 3. Add Blazer (PKR 48,000 x 1) -> Subtotal becomes 56,500 (qualifies for free shipping)
    add2_res = await async_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"variant_id": env["v1_id"], "quantity": 1},
    )
    assert add2_res.status_code == 200
    cart2 = add2_res.json()
    assert cart2["total_items"] == 2
    assert Decimal(cart2["subtotal"]) == Decimal("56500.00")
    assert cart2["is_free_shipping"] is True
    assert Decimal(cart2["amount_needed_for_free_shipping"]) == Decimal("0.00")

    # 4. Update quantity of Kurta to 2 (8,500 x 2 = 17,000)
    update_res = await async_client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=headers,
        json={"quantity": 2},
    )
    assert update_res.status_code == 200
    cart3 = update_res.json()
    assert cart3["total_items"] == 3
    assert Decimal(cart3["subtotal"]) == Decimal("65000.00")  # 17000 + 48000

    # 5. Setting quantity to 0 removes line item
    zero_res = await async_client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=headers,
        json={"quantity": 0},
    )
    assert zero_res.status_code == 200
    cart4 = zero_res.json()
    assert cart4["total_items"] == 1
    assert Decimal(cart4["subtotal"]) == Decimal("48000.00")

    # 6. Clear remaining cart
    clear_res = await async_client.delete("/api/v1/cart", headers=headers)
    assert clear_res.status_code == 200
    assert clear_res.json()["total_items"] == 0
    assert len(clear_res.json()["items"]) == 0


# ===========================================================================
# 2. Availability, Stock & Inactive Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_cart_availability_and_stock_validation(async_client: AsyncClient, seeded_cart_env):
    """Verify out-of-stock and inactive products are rejected or flagged."""
    env = seeded_cart_env
    headers = auth_header_for(env["u1"])

    # 1. Attempt adding out of stock variant (Product 3 has 0 stock)
    oos_res = await async_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"variant_id": env["v3_id"], "quantity": 1},
    )
    assert oos_res.status_code == 400
    assert "OUT_OF_STOCK" in oos_res.json()["error"]["message"]

    # 2. Attempt adding inactive draft product
    draft_res = await async_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"variant_id": env["v4_id"], "quantity": 1},
    )
    assert draft_res.status_code == 400
    assert "PRODUCT_UNAVAILABLE" in draft_res.json()["error"]["message"]


# ===========================================================================
# 3. Ownership Isolation (Cross-Customer Security)
# ===========================================================================

@pytest.mark.asyncio
async def test_cart_ownership_isolation(async_client: AsyncClient, seeded_cart_env):
    """Verify Customer B cannot modify or delete Customer A's cart items."""
    env = seeded_cart_env
    alice_headers = auth_header_for(env["u1"])
    bob_headers = auth_header_for(env["u2"])

    # Alice adds an item
    alice_add = await async_client.post(
        "/api/v1/cart/items",
        headers=alice_headers,
        json={"variant_id": env["v1_id"], "quantity": 1},
    )
    alice_cart = alice_add.json()
    alice_item_id = alice_cart["items"][0]["id"]

    # Bob attempts to update Alice's item
    bob_hack = await async_client.patch(
        f"/api/v1/cart/items/{alice_item_id}",
        headers=bob_headers,
        json={"quantity": 5},
    )
    assert bob_hack.status_code == 404

    # Bob attempts to delete Alice's item
    bob_del = await async_client.delete(
        f"/api/v1/cart/items/{alice_item_id}",
        headers=bob_headers,
    )
    assert bob_del.status_code == 404

    # Verify Alice's cart remains intact
    alice_check = await async_client.get("/api/v1/cart", headers=alice_headers)
    assert alice_check.status_code == 200
    assert alice_check.json()["items"][0]["quantity"] == 1


# ===========================================================================
# 4. Guest Shopping Cart & Merge Lifecycle
# ===========================================================================

@pytest.mark.asyncio
async def test_guest_cart_and_merge_into_account(async_client: AsyncClient, seeded_cart_env):
    """Verify anonymous guest cart creation and merging into customer account upon login."""
    env = seeded_cart_env

    # 1. Anonymous visitor requests cart -> gets token header
    guest_get = await async_client.get("/api/v1/cart")
    assert guest_get.status_code == 200
    guest_token = guest_get.headers.get("x-anonymous-cart-token")
    assert guest_token is not None
    assert len(guest_token) > 10

    guest_headers = {"X-Anonymous-Cart-Token": guest_token}

    # 2. Guest adds Kurta x2
    guest_add = await async_client.post(
        "/api/v1/cart/items",
        headers=guest_headers,
        json={"variant_id": env["v2_id"], "quantity": 2},
    )
    assert guest_add.status_code == 200
    assert guest_add.json()["total_items"] == 2

    # 3. Customer Alice already has Blazer x1 in her cart
    alice_headers = auth_header_for(env["u1"])
    await async_client.post(
        "/api/v1/cart/items",
        headers=alice_headers,
        json={"variant_id": env["v1_id"], "quantity": 1},
    )

    # 4. Alice logs in and merges guest cart
    merge_res = await async_client.post(
        "/api/v1/cart/merge",
        headers=alice_headers,
        json={"anonymous_token": guest_token},
    )
    assert merge_res.status_code == 200
    merged_cart = merge_res.json()
    assert merged_cart["total_items"] == 3
    # Check that both Blazer and Kurta are in Alice's cart
    skus = [i["variant_sku"] for i in merged_cart["items"]]
    assert "DB-BLAZER-40R" in skus
    assert "EG-KURTA-M" in skus

    # 5. Verify the guest cart is marked merged in database
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        gc_res = await session.execute(select(Cart).where(Cart.anonymous_token == guest_token))
        assert gc_res.scalar_one().status == "merged"


# ===========================================================================
# 5. Customer Wishlist Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_customer_wishlist_lifecycle(async_client: AsyncClient, seeded_cart_env):
    """Verify authenticated customer wishlist add, idempotency, list, and delete."""
    env = seeded_cart_env
    headers = auth_header_for(env["u1"])

    # 1. Unauthenticated request rejected
    anon_res = await async_client.get("/api/v1/wishlist")
    assert anon_res.status_code == 401

    # 2. Bookmark Product 1 (Blazer)
    add_w1 = await async_client.post(
        "/api/v1/wishlist/items",
        headers=headers,
        json={"product_id": env["p1_id"]},
    )
    assert add_w1.status_code == 200
    w_data = add_w1.json()
    assert w_data["total_items"] == 1
    assert w_data["items"][0]["product_id"] == env["p1_id"]
    assert w_data["items"][0]["product_name"] == "Double Breasted Wool Blazer"
    assert w_data["items"][0]["image_url"] == "https://cdn.uninova.pk/products/blazer-front.webp"

    # 3. Bookmark Product 2 (Kurta)
    add_w2 = await async_client.post(
        "/api/v1/wishlist/items",
        headers=headers,
        json={"product_id": env["p2_id"]},
    )
    assert add_w2.status_code == 200
    assert add_w2.json()["total_items"] == 2

    # 4. Adding duplicate is idempotent (count remains 2)
    add_dup = await async_client.post(
        "/api/v1/wishlist/items",
        headers=headers,
        json={"product_id": env["p1_id"]},
    )
    assert add_dup.status_code == 200
    assert add_dup.json()["total_items"] == 2

    # 5. Remove Product 1
    del_w1 = await async_client.delete(
        f"/api/v1/wishlist/items/{env['p1_id']}",
        headers=headers,
    )
    assert del_w1.status_code == 200
    assert del_w1.json()["total_items"] == 1
    assert del_w1.json()["items"][0]["product_id"] == env["p2_id"]

    # 6. Clear wishlist
    clear_w = await async_client.delete("/api/v1/wishlist", headers=headers)
    assert clear_w.status_code == 200
    assert clear_w.json()["total_items"] == 0
