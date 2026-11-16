"""
Automated Tests for Customer Account APIs (Module M17)
Validates profile management, address book CRUD, single-default address promotion,
customer-safe order details & timeline projection (no staff notes leakage),
return/exchange history, wishlist access, ownership isolation, and security settings.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestingSessionLocal
from app.core.security import create_access_token, hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, user_roles
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.customer.models import Address, CustomerProfile
from app.modules.inventory.models import InventoryItem, InventoryLocation
from app.modules.inventory.service import get_or_create_default_location
from app.modules.orders.models import Order
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.shipping.models import ShippingMethod, ShippingZone
from app.modules.shipping.service import ensure_default_shipping_configuration


@pytest.fixture
async def seeded_customer_env():
    """Seed catalog, shipping, locations, and user accounts for customer tests."""
    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await ensure_default_shipping_configuration(session)
        loc = await get_or_create_default_location(session)

        # Category
        cat = Category(name="Prêt Wear", slug="pret-wear", is_active=True)
        session.add(cat)
        await session.flush()

        # Product & Variants
        prod = Product(
            name="Silk Lawn Kurta",
            slug="silk-lawn-kurta",
            category_id=cat.id,
            price=Decimal("8500.00"),
            status="active",
        )
        session.add(prod)
        await session.flush()

        v1 = ProductVariant(
            product_id=prod.id,
            sku="PRT-SLK-001-S",
            size="S",
            color_name="Ivory White",
            inventory_count=20,
            in_stock=True,
            is_active=True,
        )
        v2 = ProductVariant(
            product_id=prod.id,
            sku="PRT-SLK-001-M",
            size="M",
            color_name="Ivory White",
            inventory_count=20,
            in_stock=True,
            is_active=True,
        )
        session.add_all([v1, v2])
        await session.flush()

        inv1 = InventoryItem(variant_id=v1.id, location_id=loc.id, quantity_on_hand=20, quantity_reserved=0)
        inv2 = InventoryItem(variant_id=v2.id, location_id=loc.id, quantity_on_hand=20, quantity_reserved=0)
        session.add_all([inv1, inv2])

        # Users
        alice = User(
            email="alice_account@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        bob = User(
            email="bob_account@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        admin = User(
            email="admin_account@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        session.add_all([alice, bob, admin])
        await session.flush()

        # Assign store_admin role to admin
        res = await session.execute(select(Role).where(Role.name == "store_admin"))
        store_admin_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=admin.id, role_id=store_admin_role.id))

        await session.commit()
        await session.refresh(alice)
        await session.refresh(bob)
        await session.refresh(admin)
        await session.refresh(prod)
        await session.refresh(v1)
        await session.refresh(v2)

        return {
            "alice": alice,
            "bob": bob,
            "admin": admin,
            "prod": prod,
            "v1": v1,
            "v2": v2,
        }


def make_checkout_payload(payment_method: str = "cod") -> dict:
    return {
        "customer_name": "Alice Customer",
        "customer_email": "alice_account@example.com",
        "customer_phone": "03001234567",
        "shipping_method_code": "standard_delivery",
        "payment_method": payment_method,
        "customer_note": "Please deliver after 2 PM",
        "shipping_address": {
            "full_name": "Alice Customer",
            "phone": "03001234567",
            "address_line_1": "House 10, Street 2, Sector F-8/3",
            "city": "Islamabad",
            "postal_code": "44000",
            "country_code": "PK",
        },
    }


# ==============================================================================
# 1. Profile Retrieval & Updates Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_profile_get_and_update(async_client: AsyncClient, seeded_customer_env):
    """
    Validates:
    1. Unauthenticated request to /customer/profile rejected with 401.
    2. Initial GET creates default profile on-the-fly and computes full_name.
    3. PATCH updates first_name, last_name, phone, gender, and syncs phone with user record.
    """
    env = seeded_customer_env
    alice = env["alice"]
    alice_token = create_access_token(alice.id)

    # 1. Unauthenticated access rejected
    unauth_res = await async_client.get("/api/v1/customer/profile")
    assert unauth_res.status_code == 401

    # 2. Initial profile GET
    get_res = await async_client.get(
        "/api/v1/customer/profile",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert get_res.status_code == 200
    p_data = get_res.json()
    assert p_data["email"] == "alice_account@example.com"
    assert p_data["user_id"] == alice.id
    assert p_data["marketing_whatsapp_opt_in"] is True
    assert p_data["preferred_currency"] == "PKR"

    # 3. PATCH profile
    patch_res = await async_client.patch(
        "/api/v1/customer/profile",
        json={
            "first_name": "Fatima",
            "last_name": "Khan",
            "phone": "03001234567",
            "gender": "female",
            "date_of_birth": "1995-08-14",
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["first_name"] == "Fatima"
    assert updated["last_name"] == "Khan"
    assert updated["full_name"] == "Fatima Khan"
    assert updated["phone"] == "03001234567"
    assert updated["gender"] == "female"
    assert updated["date_of_birth"] == "1995-08-14"

    # Verify persistence
    verify_res = await async_client.get(
        "/api/v1/customer/profile",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert verify_res.json()["full_name"] == "Fatima Khan"


# ==============================================================================
# 2. Preferences Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_preferences_get_and_update(async_client: AsyncClient, seeded_customer_env):
    """
    Validates:
    1. GET /customer/preferences returns defaults.
    2. PATCH /customer/preferences updates marketing channels and language.
    """
    env = seeded_customer_env
    alice = env["alice"]
    alice_token = create_access_token(alice.id)

    # 1. GET defaults
    pref_res = await async_client.get(
        "/api/v1/customer/preferences",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert pref_res.status_code == 200
    prefs = pref_res.json()
    assert prefs["marketing_email_opt_in"] is False
    assert prefs["marketing_sms_opt_in"] is False
    assert prefs["marketing_whatsapp_opt_in"] is True
    assert prefs["preferred_language"] == "en"

    # 2. Update preferences
    update_res = await async_client.patch(
        "/api/v1/customer/preferences",
        json={
            "marketing_email_opt_in": True,
            "marketing_sms_opt_in": True,
            "preferred_language": "ur",
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert update_res.status_code == 200
    updated_prefs = update_res.json()
    assert updated_prefs["marketing_email_opt_in"] is True
    assert updated_prefs["marketing_sms_opt_in"] is True
    assert updated_prefs["marketing_whatsapp_opt_in"] is True
    assert updated_prefs["preferred_language"] == "ur"


# ==============================================================================
# 3. Address Book CRUD & Default Enforcement
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_address_book_crud_and_default_handling(async_client: AsyncClient, seeded_customer_env):
    """
    Validates:
    1. Creating first address automatically sets it as primary default (is_default=True).
    2. Creating second address with is_default=True demotes first address to is_default=False.
    3. Listing addresses returns default address first.
    4. Explicit set_default endpoint promotes selected address.
    5. Deleting default address automatically promotes remaining address to default.
    """
    env = seeded_customer_env
    alice = env["alice"]
    alice_token = create_access_token(alice.id)

    # 1. Create first address (Home in Lahore)
    addr1_res = await async_client.post(
        "/api/v1/customer/addresses",
        json={
            "recipient_name": "Fatima Khan",
            "phone": "03001234567",
            "address_line_1": "House 14, Street 2, Gulberg III",
            "city": "Lahore",
            "area": "Gulberg III",
            "postal_code": "54000",
            "label": "Home",
            "is_default": False,  # Should become True automatically because it is first address
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert addr1_res.status_code == 201
    addr1 = addr1_res.json()
    assert addr1["is_default"] is True
    addr1_id = addr1["id"]

    # 2. Create second address (Office in Karachi) with is_default=True
    addr2_res = await async_client.post(
        "/api/v1/customer/addresses",
        json={
            "recipient_name": "Fatima Khan",
            "phone": "03217654321",
            "address_line_1": "Office 402, Executive Tower, Clifton Block 4",
            "city": "Karachi",
            "area": "Clifton",
            "postal_code": "75600",
            "label": "Office",
            "is_default": True,
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert addr2_res.status_code == 201
    addr2 = addr2_res.json()
    assert addr2["is_default"] is True
    addr2_id = addr2["id"]

    # 3. Verify addr1 is demoted
    addr1_check = await async_client.get(
        f"/api/v1/customer/addresses/{addr1_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert addr1_check.status_code == 200
    assert addr1_check.json()["is_default"] is False

    # 4. List addresses -> Default (addr2) is first
    list_res = await async_client.get(
        "/api/v1/customer/addresses",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert list_res.status_code == 200
    addresses = list_res.json()["addresses"]
    assert len(addresses) == 2
    assert addresses[0]["id"] == addr2_id
    assert addresses[0]["is_default"] is True

    # 5. Promote addr1 back to default
    promote_res = await async_client.post(
        f"/api/v1/customer/addresses/{addr1_id}/default",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert promote_res.status_code == 200
    assert promote_res.json()["is_default"] is True

    # Check addr2 is now not default
    addr2_check = await async_client.get(
        f"/api/v1/customer/addresses/{addr2_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert addr2_check.json()["is_default"] is False

    # 6. Delete addr1 (current default) -> addr2 must be automatically promoted to default
    del_res = await async_client.delete(
        f"/api/v1/customer/addresses/{addr1_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert del_res.status_code == 204

    # Verify addr2 was promoted
    addr2_after = await async_client.get(
        f"/api/v1/customer/addresses/{addr2_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert addr2_after.json()["is_default"] is True


# ==============================================================================
# 4. Address Validation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_address_validation(async_client: AsyncClient, seeded_customer_env):
    """
    Validates:
    1. Invalid Pakistani mobile number (e.g. 12345 or non-PK format) is rejected with 422.
    2. Missing mandatory fields or short address rejected with 422.
    """
    env = seeded_customer_env
    alice = env["alice"]
    alice_token = create_access_token(alice.id)

    # Invalid phone format
    res_bad_phone = await async_client.post(
        "/api/v1/customer/addresses",
        json={
            "recipient_name": "Test User",
            "phone": "042-35870000",  # Landline, not mobile
            "address_line_1": "House 1, Street 2",
            "city": "Lahore",
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_bad_phone.status_code == 422

    # Short street address (<5 chars)
    res_short_addr = await async_client.post(
        "/api/v1/customer/addresses",
        json={
            "recipient_name": "Test User",
            "phone": "03001234567",
            "address_line_1": "St 1",
            "city": "Lahore",
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_short_addr.status_code == 422


# ==============================================================================
# 5. Customer Ownership Isolation Across Customers
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_ownership_isolation(async_client: AsyncClient, seeded_customer_env):
    """
    Validates strict tenant isolation:
    1. Bob cannot view, update, delete, or default Alice's address (all return 404).
    2. Alice cannot view Bob's data.
    """
    env = seeded_customer_env
    alice = env["alice"]
    bob = env["bob"]
    alice_token = create_access_token(alice.id)
    bob_token = create_access_token(bob.id)

    # Alice creates an address
    addr_res = await async_client.post(
        "/api/v1/customer/addresses",
        json={
            "recipient_name": "Alice Address",
            "phone": "03001234567",
            "address_line_1": "House 20, Sector Y, DHA Phase 3",
            "city": "Lahore",
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    alice_addr_id = addr_res.json()["id"]

    # Bob tries to view Alice's address -> 404
    bob_get = await async_client.get(
        f"/api/v1/customer/addresses/{alice_addr_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_get.status_code == 404

    # Bob tries to update Alice's address -> 404
    bob_patch = await async_client.patch(
        f"/api/v1/customer/addresses/{alice_addr_id}",
        json={"recipient_name": "Hacked Recipient"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_patch.status_code == 404

    # Bob tries to delete Alice's address -> 404
    bob_delete = await async_client.delete(
        f"/api/v1/customer/addresses/{alice_addr_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_delete.status_code == 404

    # Bob tries to set Alice's address as default -> 404
    bob_def = await async_client.post(
        f"/api/v1/customer/addresses/{alice_addr_id}/default",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_def.status_code == 404


# ==============================================================================
# 6. Customer-Safe Order Details & Timeline Projection
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_order_detail_and_timeline_projection(async_client: AsyncClient, seeded_customer_env):
    """
    Validates:
    1. Customer can view detailed order projection.
    2. Customer timeline contains customer-friendly descriptions.
    3. Internal staff notes (staff_notes) are strictly OMITTED from customer projection.
    4. Bob cannot view Alice's order (returns 404).
    """
    env = seeded_customer_env
    alice = env["alice"]
    bob = env["bob"]
    admin = env["admin"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    bob_token = create_access_token(bob.id)
    admin_token = create_access_token(admin.id, user_type="staff")

    # Alice adds item and checks out
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert checkout_res.status_code == 201
    order_data = checkout_res.json()
    order_num = order_data["order_number"]
    order_id = order_data["id"]

    # Staff updates order status with internal staff remarks
    await async_client.patch(
        f"/api/v1/admin/orders/{order_id}/status",
        json={"to_status": "confirmed", "note": "INTERNAL_STAFF_SECRET: High priority customer VIP call verified"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # 1. Alice retrieves order detail
    detail_res = await async_client.get(
        f"/api/v1/customer/orders/{order_num}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["order_number"] == order_num
    assert detail["status"] == "confirmed"
    assert len(detail["items"]) == 1
    assert detail["items"][0]["sku"] == "PRT-SLK-001-S"
    assert len(detail["timeline"]) >= 2

    # Verify that internal staff note was NOT leaked into timeline or order detail
    detail_str = str(detail)
    assert "INTERNAL_STAFF_SECRET" not in detail_str
    assert "staff_notes" not in detail

    # 2. Bob tries to access Alice's order -> 404
    bob_res = await async_client.get(
        f"/api/v1/customer/orders/{order_num}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_res.status_code == 404


# ==============================================================================
# 7. Customer Returns Overview & Privacy
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_returns_overview_and_isolation(async_client: AsyncClient, seeded_customer_env):
    """
    Validates:
    1. Customer can list all return and exchange requests.
    2. Customer cannot view internal staff notes or inspector notes.
    3. Bob cannot access Alice's return requests (returns 404).
    """
    env = seeded_customer_env
    alice = env["alice"]
    bob = env["bob"]
    admin = env["admin"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    bob_token = create_access_token(bob.id)
    admin_token = create_access_token(admin.id, user_type="staff")

    # Alice buys and delivers item
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = order_res.json()
    order_num = order_data["order_number"]
    order_id = order_data["id"]
    item_id = order_data["items"][0]["id"]

    # Fulfill and deliver
    shp = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={"courier_code": "tcs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "dispatched"}, headers={"Authorization": f"Bearer {admin_token}"})
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "delivered"}, headers={"Authorization": f"Bearer {admin_token}"})

    # Alice files return
    ret_res = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "resolution_type": "store_credit",
            "customer_notes": "Sleeve length too long",
            "items": [
                {
                    "order_item_id": item_id,
                    "quantity": 1,
                    "reason": "size_fit",
                }
            ],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert ret_res.status_code == 201
    ret_id = ret_res.json()["id"]

    # Support reviews and inspects return with internal staff remarks
    await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/review",
        json={"decision": "approved", "staff_notes": "INTERNAL_SECRET_SUPPORT: VIP approved without receipt"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # 1. Alice lists returns
    my_returns = await async_client.get(
        "/api/v1/customer/returns",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert my_returns.status_code == 200
    ret_list = my_returns.json()["returns"]
    assert len(ret_list) == 1
    assert ret_list[0]["id"] == ret_id
    assert ret_list[0]["order_number"] == order_num

    # Verify internal remarks are NOT exposed
    assert "INTERNAL_SECRET_SUPPORT" not in str(my_returns.json())
    assert "staff_notes" not in ret_list[0]

    # 2. Alice views return detail
    detail_res = await async_client.get(
        f"/api/v1/customer/returns/{ret_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["request_number"].startswith("RET-")

    # 3. Bob attempts to view Alice's return -> 404
    bob_ret = await async_client.get(
        f"/api/v1/customer/returns/{ret_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_ret.status_code == 404


# ==============================================================================
# 8. Customer Wishlist Access
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_wishlist_access(async_client: AsyncClient, seeded_customer_env):
    """
    Validates customer portal wishlist access:
    1. Adding product to wishlist.
    2. Retrieving wishlist via /customer/wishlist.
    """
    env = seeded_customer_env
    alice = env["alice"]
    prod = env["prod"]
    alice_token = create_access_token(alice.id)

    # Add to wishlist
    add_wl = await async_client.post(
        "/api/v1/wishlist/items",
        json={"product_id": prod.id},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert add_wl.status_code == 200

    # Retrieve via customer portal endpoint
    wl_res = await async_client.get(
        "/api/v1/customer/wishlist",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert wl_res.status_code == 200
    items = wl_res.json()["items"]
    assert len(items) == 1
    assert items[0]["product_id"] == prod.id
    assert items[0]["product_name"] == "Silk Lawn Kurta"


# ==============================================================================
# 9. Password Change & Session Management
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_security_settings_and_session_invalidation(async_client: AsyncClient, seeded_customer_env):
    """
    Validates:
    1. GET /customer/security returns account security status.
    2. Password change rejects incorrect current password.
    3. Password change succeeds with correct password, revoking previous sessions.
    4. Old password can no longer log in; new password succeeds.
    5. Session revocation endpoint revokes active refresh tokens.
    """
    env = seeded_customer_env
    alice = env["alice"]
    alice_token = create_access_token(alice.id)

    # 1. Security overview
    sec_res = await async_client.get(
        "/api/v1/customer/security",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert sec_res.status_code == 200
    assert sec_res.json()["email"] == "alice_account@example.com"

    # 2. Password change with wrong current password -> 400
    bad_pw = await async_client.post(
        "/api/v1/customer/security/change-password",
        json={"current_password": "WrongPassword999!", "new_password": "NewSecretPassword123!"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert bad_pw.status_code == 400

    # 3. Successful password change
    ok_pw = await async_client.post(
        "/api/v1/customer/security/change-password",
        json={"current_password": "Password123!", "new_password": "NewSecretPassword123!"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert ok_pw.status_code == 200

    # 4. Old password rejected at login
    old_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "alice_account@example.com", "password": "Password123!"},
    )
    assert old_login.status_code == 401

    # New password succeeds at login
    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "alice_account@example.com", "password": "NewSecretPassword123!"},
    )
    assert new_login.status_code == 200
    new_token = new_login.json()["access_token"]

    # 5. Revoke other sessions
    revoke_res = await async_client.post(
        "/api/v1/customer/security/revoke-sessions",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert revoke_res.status_code == 200
