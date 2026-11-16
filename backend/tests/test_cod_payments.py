"""
Cash on Delivery (COD) Workflow & Reconciliation Tests (Module M13)
Validates COD payment initialization, order payment status separation (orders remain unpaid),
customer self-confirmation, staff confirmation, courier dispatch tracking, cash collection
(full and partial), courier remittance reconciliation, cancellation restock, and RBAC protections.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductImage, ProductVariant
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.service import get_or_create_default_location
from app.modules.orders.models import Order
from app.modules.payments.models import Payment, PaymentTransaction
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.shipping.service import ensure_default_shipping_configuration


@pytest.fixture
async def seeded_cod_env():
    """Seeds roles, shipping, products, inventory, and users with differentiated roles."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await ensure_default_shipping_configuration(session)
        loc = await get_or_create_default_location(session)

        # Catalog setup
        cat = Category(name="Menswear", slug="menswear", is_active=True)
        session.add(cat)
        await session.flush()

        prod = Product(
            name="Classic Sherwani",
            slug="classic-sherwani",
            category_id=cat.id,
            price=Decimal("55000.00"),
            status="active",
        )
        session.add(prod)
        await session.flush()

        variant = ProductVariant(
            product_id=prod.id,
            sku="SHERWANI-BLK-40",
            size="40",
            color_name="Jet Black",
            inventory_count=5,
            in_stock=True,
            is_active=True,
        )
        session.add(variant)
        await session.flush()

        inv = InventoryItem(
            variant_id=variant.id,
            location_id=loc.id,
            quantity_on_hand=5,
            quantity_reserved=0,
        )
        session.add(inv)

        # Users
        alice = User(
            email="alice_cod@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        bob = User(
            email="bob_cod@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        admin = User(
            email="admin_cod@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        finance_user = User(
            email="finance_cod@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        fulfillment_user = User(
            email="fulfillment_cod@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        session.add_all([alice, bob, admin, finance_user, fulfillment_user])
        await session.flush()

        # Assign store_admin to admin
        res = await session.execute(select(Role).where(Role.name == "store_admin"))
        store_admin_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=admin.id, role_id=store_admin_role.id))

        # Assign finance_operator to finance_user
        res = await session.execute(select(Role).where(Role.name == "finance_operator"))
        finance_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=finance_user.id, role_id=finance_role.id))

        # Assign fulfillment_staff to fulfillment_user
        res = await session.execute(select(Role).where(Role.name == "fulfillment_staff"))
        fulfillment_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=fulfillment_user.id, role_id=fulfillment_role.id))

        await session.commit()
        await session.refresh(alice)
        await session.refresh(bob)
        await session.refresh(admin)
        await session.refresh(finance_user)
        await session.refresh(fulfillment_user)
        await session.refresh(variant)

        return {
            "alice": alice,
            "bob": bob,
            "admin": admin,
            "finance_user": finance_user,
            "fulfillment_user": fulfillment_user,
            "variant": variant,
        }


def make_cod_checkout_payload(
    customer_name: str = "Alice COD",
    customer_email: str = "alice_cod@example.com",
    customer_phone: str = "03001234567",
    idempotency_key: str = None,
) -> dict:
    return {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "shipping_method_code": "standard_delivery",
        "payment_method": "cod",
        "idempotency_key": idempotency_key,
        "shipping_address": {
            "full_name": customer_name,
            "phone": customer_phone,
            "address_line_1": "Apartment 101, Main Boulevard, Gulberg III",
            "city": "Lahore",
            "postal_code": "54000",
            "country_code": "PK",
        },
    }


@pytest.mark.asyncio
async def test_cod_order_placement_creates_unpaid_payment_record(async_client: AsyncClient, seeded_cod_env):
    """
    Validates that placing a COD order initializes:
    - Order with payment_status='unpaid' and status='pending_confirmation'
    - Payment with status='pending', amount_collected=0.00, amount_outstanding=grand_total
    - Initial 'initiated' payment transaction entry
    """
    env = seeded_cod_env
    alice = env["alice"]
    variant = env["variant"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Add item to cart
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers=headers,
    )

    # Checkout via COD
    checkout_payload = make_cod_checkout_payload(
        customer_name="Alice COD",
        customer_email=alice.email,
        customer_phone="03001234567",
        idempotency_key="cod-test-init-001",
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
        headers=headers,
    )
    assert res.status_code == 201
    order_data = res.json()
    order_num = order_data["order_number"]

    # Verify Order state: NEVER considered paid upon order creation!
    assert order_data["payment_method"] == "cod"
    assert order_data["payment_status"] == "unpaid"
    assert order_data["status"] == "pending_confirmation"

    # Customer retrieves payment record
    pay_res = await async_client.get(
        f"/api/v1/customer/payments/order/{order_num}",
        headers=headers,
    )
    assert pay_res.status_code == 200
    payment = pay_res.json()

    assert payment["payment_method"] == "cod"
    assert payment["status"] == "pending"
    assert Decimal(payment["amount"]) == Decimal("55000.00")
    assert Decimal(payment["amount_collected"]) == Decimal("0.00")
    assert Decimal(payment["amount_outstanding"]) == Decimal("55000.00")
    assert len(payment["transactions"]) == 1
    assert payment["transactions"][0]["action"] == "initiated"


@pytest.mark.asyncio
async def test_customer_payment_lookup_and_isolation(async_client: AsyncClient, seeded_cod_env):
    """Verifies that customers can only view payments for their own orders."""
    env = seeded_cod_env
    alice = env["alice"]
    bob = env["bob"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    bob_token = create_access_token(bob.id)

    # Alice places order
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    create_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_cod_checkout_payload(customer_email=alice.email, idempotency_key="cod-isol-001"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_num = create_res.json()["order_number"]

    # 1. Alice views her payment -> 200
    r_alice = await async_client.get(
        f"/api/v1/customer/payments/order/{order_num}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert r_alice.status_code == 200

    # 2. Bob attempts to view Alice's payment -> 404
    r_bob = await async_client.get(
        f"/api/v1/customer/payments/order/{order_num}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert r_bob.status_code == 404


@pytest.mark.asyncio
async def test_customer_self_confirmation_flow(async_client: AsyncClient, seeded_cod_env):
    """Customer self-confirms COD order, transitioning payment and order states while remaining unpaid."""
    env = seeded_cod_env
    alice = env["alice"]
    variant = env["variant"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers=headers,
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_cod_checkout_payload(customer_email=alice.email, idempotency_key="cod-self-conf-001"),
        headers=headers,
    )
    order_num = res.json()["order_number"]

    # Customer confirms COD
    conf_res = await async_client.post(
        f"/api/v1/customer/payments/order/{order_num}/confirm-cod",
        json={"notes": "Customer confirmed via online account verification"},
        headers=headers,
    )
    assert conf_res.status_code == 200
    payment = conf_res.json()
    assert payment["status"] == "confirmed"
    assert payment["confirmed_at"] is not None

    # Check order status updated to confirmed, but payment_status remains unpaid
    order_res = await async_client.get(f"/api/v1/orders/{order_num}", headers=headers)
    assert order_res.status_code == 200
    assert order_res.json()["status"] == "confirmed"
    assert order_res.json()["payment_status"] == "unpaid"


@pytest.mark.asyncio
async def test_admin_cod_dispatch_and_full_collection(async_client: AsyncClient, seeded_cod_env):
    """
    Validates administrative COD lifecycle:
    1. Confirmation
    2. Dispatch tracking with courier AWB
    3. Cash collection recording of full amount
    4. Order marked as paid and delivered
    """
    env = seeded_cod_env
    alice = env["alice"]
    admin = env["admin"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Place order
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_cod_checkout_payload(customer_email=alice.email, idempotency_key="cod-admin-flow-001"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = res.json()
    order_id = order_data["id"]

    # Retrieve payment ID
    pay_get = await async_client.get(f"/api/v1/admin/payments/order/{order_id}", headers=admin_headers)
    assert pay_get.status_code == 200
    payment_id = pay_get.json()["id"]

    # 1. Admin confirms COD
    c_res = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/confirm-cod",
        json={"notes": "Customer verified via phone call"},
        headers=admin_headers,
    )
    assert c_res.status_code == 200
    assert c_res.json()["status"] == "confirmed"

    # 2. Admin records dispatch
    d_res = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/dispatch",
        json={"courier_code": "blue_ex", "tracking_number": "BLUEX-99881122", "notes": "Handed to BlueEx rider"},
        headers=admin_headers,
    )
    assert d_res.status_code == 200
    assert d_res.json()["status"] == "dispatched"
    assert d_res.json()["provider_reference"] == "BLUEX-99881122"

    # Verify order is now shipped, but still unpaid
    order_chk1 = await async_client.get(f"/api/v1/orders/{order_data['order_number']}", headers=admin_headers)
    assert order_chk1.json()["status"] == "shipped"
    assert order_chk1.json()["payment_status"] == "unpaid"

    # 3. Admin records full cash collection upon delivery
    col_res = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/record-collection",
        json={
            "amount_collected": "55000.00",
            "collected_by": "BlueEx Courier",
            "reference": "POD-889900",
            "notes": "Full payment received by customer in cash at doorstep",
        },
        headers=admin_headers,
    )
    assert col_res.status_code == 200
    payment_done = col_res.json()
    assert payment_done["status"] == "collected"
    assert Decimal(payment_done["amount_collected"]) == Decimal("55000.00")
    assert Decimal(payment_done["amount_outstanding"]) == Decimal("0.00")

    # Verify order is now marked paid and delivered
    order_chk2 = await async_client.get(f"/api/v1/orders/{order_data['order_number']}", headers=admin_headers)
    assert order_chk2.json()["payment_status"] == "paid"
    assert order_chk2.json()["status"] == "delivered"


@pytest.mark.asyncio
async def test_admin_partial_cash_collection(async_client: AsyncClient, seeded_cod_env):
    """
    Validates partial collection tracking:
    - Order payment_status becomes 'partially_paid'
    - Outstanding balance correctly calculated
    - Over-collection rejected with 400
    """
    env = seeded_cod_env
    alice = env["alice"]
    admin = env["admin"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Place order
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_cod_checkout_payload(customer_email=alice.email, idempotency_key="cod-partial-001"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_id = res.json()["id"]

    pay_res = await async_client.get(f"/api/v1/admin/payments/order/{order_id}", headers=admin_headers)
    payment_id = pay_res.json()["id"]

    # Record partial collection of PKR 25,000 against PKR 55,000 total
    part_res = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/record-collection",
        json={"amount_collected": "25000.00", "collected_by": "Rider Tariq", "reference": "PART-01"},
        headers=admin_headers,
    )
    assert part_res.status_code == 200
    part_pay = part_res.json()
    assert part_pay["status"] == "partially_collected"
    assert Decimal(part_pay["amount_collected"]) == Decimal("25000.00")
    assert Decimal(part_pay["amount_outstanding"]) == Decimal("30000.00")

    # Order payment_status is partially_paid
    ord_chk = await async_client.get(f"/api/v1/orders/{res.json()['order_number']}", headers=admin_headers)
    assert ord_chk.json()["payment_status"] == "partially_paid"

    # Attempting to collect more than outstanding (e.g. 35,000 > 30,000) -> 400
    excess_res = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/record-collection",
        json={"amount_collected": "35000.00"},
        headers=admin_headers,
    )
    assert excess_res.status_code == 400


@pytest.mark.asyncio
async def test_courier_remittance_reconciliation(async_client: AsyncClient, seeded_cod_env):
    """
    Validates courier settlement reconciliation by finance staff:
    - Collected COD payment is reconciled with settlement batch voucher
    - Reconciling uncollected payment rejected with 400
    - Reconciled details and timestamps recorded
    """
    env = seeded_cod_env
    alice = env["alice"]
    admin = env["admin"]
    finance_user = env["finance_user"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)
    finance_token = create_access_token(finance_user.id)
    finance_headers = {"Authorization": f"Bearer {finance_token}"}

    # Place order
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_cod_checkout_payload(customer_email=alice.email, idempotency_key="cod-reconcile-001"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_id = res.json()["id"]

    pay_res = await async_client.get(f"/api/v1/admin/payments/order/{order_id}", headers={"Authorization": f"Bearer {admin_token}"})
    payment_id = pay_res.json()["id"]

    # 1. Attempting reconciliation before collection -> 400
    premature_rec = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/reconcile",
        json={"settlement_reference": "REMIT-PREMATURE"},
        headers=finance_headers,
    )
    assert premature_rec.status_code == 400

    # 2. Record full collection first
    await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/record-collection",
        json={"amount_collected": "55000.00", "collected_by": "BlueEx"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # 3. Finance operator reconciles settlement
    rec_res = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/reconcile",
        json={
            "settlement_reference": "BLUEEX-REMITTANCE-BATCH-9944",
            "notes": "Verified credited in HBL Corporate Account #0012345678",
        },
        headers=finance_headers,
    )
    assert rec_res.status_code == 200
    rec_pay = rec_res.json()
    assert rec_pay["status"] == "reconciled"
    assert rec_pay["settlement_reference"] == "BLUEEX-REMITTANCE-BATCH-9944"
    assert rec_pay["reconciled_by_user_id"] == finance_user.id
    assert rec_pay["reconciled_at"] is not None


@pytest.mark.asyncio
async def test_cod_cancellation_releases_stock(async_client: AsyncClient, seeded_cod_env):
    """
    Cancelling a COD order:
    - Sets payment status to 'cancelled'
    - Automatically updates order status to 'cancelled'
    - Releases reserved physical stock back to available pool
    """
    env = seeded_cod_env
    alice = env["alice"]
    admin = env["admin"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Place order
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_cod_checkout_payload(customer_email=alice.email, idempotency_key="cod-cancel-001"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_id = res.json()["id"]

    # Verify inventory was reserved (reserved=1)
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        inv_stmt = select(InventoryItem).where(InventoryItem.variant_id == variant.id)
        inv_res = await session.execute(inv_stmt)
        assert inv_res.scalar_one().quantity_reserved == 1

    pay_res = await async_client.get(f"/api/v1/admin/payments/order/{order_id}", headers=admin_headers)
    payment_id = pay_res.json()["id"]

    # Cancel COD order
    cancel_res = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/cancel",
        json={"reason": "Customer refused verification phone call", "notes": "No response after 3 attempts"},
        headers=admin_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Verify order is cancelled
    ord_chk = await async_client.get(f"/api/v1/orders/{res.json()['order_number']}", headers=admin_headers)
    assert ord_chk.json()["status"] == "cancelled"

    # Verify reserved stock was released back to 0
    async with TestingSessionLocal() as session:
        inv_stmt = select(InventoryItem).where(InventoryItem.variant_id == variant.id)
        inv_res = await session.execute(inv_stmt)
        assert inv_res.scalar_one().quantity_reserved == 0


@pytest.mark.asyncio
async def test_cod_payments_rbac_enforcement(async_client: AsyncClient, seeded_cod_env):
    """
    Validates RBAC protection:
    - Customer cannot access admin payments list (403)
    - Fulfillment staff without 'payments.reconcile' cannot record collection (403) or reconcile (403)
    - Unauthenticated user cannot access payments (401)
    """
    env = seeded_cod_env
    alice = env["alice"]
    admin = env["admin"]
    fulfillment_user = env["fulfillment_user"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)
    fulfill_token = create_access_token(fulfillment_user.id)

    # 1. Unauthenticated -> 401
    r_unauth = await async_client.get("/api/v1/admin/payments")
    assert r_unauth.status_code == 401

    # 2. Customer -> 403
    r_cust = await async_client.get(
        "/api/v1/admin/payments",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert r_cust.status_code == 403

    # Place order to test payment actions
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_cod_checkout_payload(customer_email=alice.email, idempotency_key="cod-rbac-001"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_id = res.json()["id"]
    pay_get = await async_client.get(f"/api/v1/admin/payments/order/{order_id}", headers={"Authorization": f"Bearer {admin_token}"})
    payment_id = pay_get.json()["id"]

    # 3. Fulfillment staff cannot record collection (requires 'payments.reconcile') -> 403
    r_fulfill_col = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/record-collection",
        json={"amount_collected": "55000.00"},
        headers={"Authorization": f"Bearer {fulfill_token}"},
    )
    assert r_fulfill_col.status_code == 403

    # 4. Fulfillment staff cannot reconcile -> 403
    r_fulfill_rec = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/reconcile",
        json={"settlement_reference": "TEST"},
        headers={"Authorization": f"Bearer {fulfill_token}"},
    )
    assert r_fulfill_rec.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_and_search_payments(async_client: AsyncClient, seeded_cod_env):
    """Administrative payment work queue filtering by status and search."""
    env = seeded_cod_env
    alice = env["alice"]
    admin = env["admin"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Place order
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_cod_checkout_payload(customer_email=alice.email, idempotency_key="cod-search-001"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_num = res.json()["order_number"]

    # Search by order number
    s_res = await async_client.get(f"/api/v1/admin/payments?search={order_num}", headers=admin_headers)
    assert s_res.status_code == 200
    assert s_res.json()["total"] >= 1
    assert any(p["order_number"] == order_num for p in s_res.json()["payments"])

    # Filter by status
    f_res = await async_client.get("/api/v1/admin/payments?status=pending", headers=admin_headers)
    assert f_res.status_code == 200
    assert f_res.json()["total"] >= 1
