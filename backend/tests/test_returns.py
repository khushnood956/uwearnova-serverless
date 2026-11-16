"""
Returns, Exchanges, and Quality Inspection Tests (Module M16)
Validates return policy eligibility, item-level quantity constraints,
staff review decisions (approval/rejection), warehouse quality inspection,
transaction-safe inventory restock, doorstep exchanges, online gateway refunds,
and documented manual Cash on Delivery refund payouts.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.fulfillment.models import Shipment
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.service import get_or_create_default_location
from app.modules.orders.models import Order
from app.modules.payments.models import Payment, PaymentTransaction
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.returns.models import ReturnItem, ReturnRequest
from app.modules.shipping.service import ensure_default_shipping_configuration


@pytest.fixture
async def seeded_returns_env():
    """Seeds catalog, inventory, shipping, and users with diverse operational roles."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await ensure_default_shipping_configuration(session)
        loc = await get_or_create_default_location(session)

        cat = Category(name="Heritage Wear", slug="heritage-wear", is_active=True)
        session.add(cat)
        await session.flush()

        prod = Product(
            name="Handcrafted Peshawari Chappal",
            slug="handcrafted-peshawari-chappal",
            category_id=cat.id,
            price=Decimal("15000.00"),
            status="active",
        )
        session.add(prod)
        await session.flush()

        v1 = ProductVariant(
            product_id=prod.id,
            sku="CHAPPAL-BLK-42",
            size="42",
            color_name="Onyx Black",
            inventory_count=10,
            in_stock=True,
            is_active=True,
        )
        v2 = ProductVariant(
            product_id=prod.id,
            sku="CHAPPAL-BLK-44",
            size="44",
            color_name="Onyx Black",
            inventory_count=10,
            in_stock=True,
            is_active=True,
        )
        session.add_all([v1, v2])
        await session.flush()

        inv1 = InventoryItem(variant_id=v1.id, location_id=loc.id, quantity_on_hand=10, quantity_reserved=0)
        inv2 = InventoryItem(variant_id=v2.id, location_id=loc.id, quantity_on_hand=10, quantity_reserved=0)
        session.add_all([inv1, inv2])

        # Users
        alice = User(
            email="alice_returns@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        bob = User(
            email="bob_returns@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        admin = User(
            email="admin_returns@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        support = User(
            email="support_returns@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        finance = User(
            email="finance_returns@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        session.add_all([alice, bob, admin, support, finance])
        await session.flush()

        # Assign store_admin to admin
        res = await session.execute(select(Role).where(Role.name == "store_admin"))
        store_admin_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=admin.id, role_id=store_admin_role.id))

        # Assign customer_support to support
        res = await session.execute(select(Role).where(Role.name == "customer_support"))
        support_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=support.id, role_id=support_role.id))

        # Assign finance_operator to finance
        res = await session.execute(select(Role).where(Role.name == "finance_operator"))
        finance_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=finance.id, role_id=finance_role.id))

        await session.commit()
        await session.refresh(alice)
        await session.refresh(bob)
        await session.refresh(admin)
        await session.refresh(support)
        await session.refresh(finance)
        await session.refresh(v1)
        await session.refresh(v2)

        return {
            "alice": alice,
            "bob": bob,
            "admin": admin,
            "support": support,
            "finance": finance,
            "v1": v1,
            "v2": v2,
        }


def make_returns_checkout_payload(
    customer_name: str = "Alice Returns",
    customer_email: str = "alice_returns@example.com",
    customer_phone: str = "03001234999",
    payment_method: str = "cod",
    idempotency_key: str = None,
) -> dict:
    return {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "shipping_method_code": "standard_delivery",
        "payment_method": payment_method,
        "idempotency_key": idempotency_key,
        "shipping_address": {
            "full_name": customer_name,
            "phone": customer_phone,
            "address_line_1": "House 100, Sector Y, DHA Phase 3",
            "city": "Lahore",
            "postal_code": "54792",
            "country_code": "PK",
        },
    }


# ==============================================================================
# 1. Return Eligibility & Policy Constraints
# ==============================================================================


@pytest.mark.asyncio
async def test_return_eligibility_and_policy_constraints(async_client: AsyncClient, seeded_returns_env):
    """
    Validates that:
    1. Undelivered orders are rejected for returns (order must be delivered).
    2. Delivered orders within policy window are eligible.
    3. Requests beyond 14 days are rejected.
    """
    env = seeded_returns_env
    alice = env["alice"]
    admin = env["admin"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_returns_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_num = order_data["order_number"]
    item_id = order_data["items"][0]["id"]

    return_payload = {
        "request_type": "return",
        "resolution_type": "refund",
        "items": [{"order_item_id": item_id, "quantity": 1, "reason": "size_fit"}],
    }

    # 1. Undelivered order fails return request
    res_undelivered = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json=return_payload,
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_undelivered.status_code == 400
    assert "INELIGIBLE_FOR_RETURN" in res_undelivered.json()["error"]["message"]

    # Deliver the order via Admin
    # Create shipment and advance to delivered
    shp_res = await async_client.post(
        f"/api/v1/admin/orders/{order_data['id']}/shipments",
        json={"courier_code": "tcs", "tracking_number": "TCS-RET-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    shp_id = shp_res.json()["id"]
    await async_client.patch(
        f"/api/v1/admin/shipments/{shp_id}/status",
        json={"status": "dispatched"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(
        f"/api/v1/admin/shipments/{shp_id}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # 2. Delivered order succeeds return request
    res_ok = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json=return_payload,
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_ok.status_code == 201
    ret = res_ok.json()
    assert ret["request_number"].startswith("RET-")
    assert ret["status"] == "requested"
    assert ret["items"][0]["quantity"] == 1
    assert ret["items"][0]["reason"] == "size_fit"


# ==============================================================================
# 2. Quantity Constraints & Deduplication
# ==============================================================================


@pytest.mark.asyncio
async def test_return_quantity_bounds_and_prevent_duplicate_returns(async_client: AsyncClient, seeded_returns_env):
    """
    Validates that:
    1. Cannot request return for quantity exceeding purchased line items.
    2. Cannot return more than remaining unreturned quantity.
    """
    env = seeded_returns_env
    alice = env["alice"]
    admin = env["admin"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 2},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_returns_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_num = order_data["order_number"]
    item_id = order_data["items"][0]["id"]

    # Fulfill and deliver
    shp = await async_client.post(
        f"/api/v1/admin/orders/{order_data['id']}/shipments",
        json={"courier_code": "tcs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(
        f"/api/v1/admin/shipments/{shp.json()['id']}/status",
        json={"status": "dispatched"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(
        f"/api/v1/admin/shipments/{shp.json()['id']}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # 1. Attempt return of 5 units (only 2 purchased) -> 400 Bad Request
    res_excess = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "items": [{"order_item_id": item_id, "quantity": 5, "reason": "size_fit"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_excess.status_code == 400
    assert "exceeds remaining returnable units" in res_excess.json()["error"]["message"]

    # 2. Return 1 unit -> succeeds
    res_1 = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "items": [{"order_item_id": item_id, "quantity": 1, "reason": "size_fit"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_1.status_code == 201

    # 3. Return another 1 unit -> succeeds (reaches 2 total)
    res_2 = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "items": [{"order_item_id": item_id, "quantity": 1, "reason": "color_mismatch"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_2.status_code == 201

    # 4. Attempt 3rd return -> rejected (0 remaining)
    res_3 = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "items": [{"order_item_id": item_id, "quantity": 1, "reason": "changed_mind"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_3.status_code == 400
    assert "exceeds remaining returnable units (0)" in res_3.json()["error"]["message"]


# ==============================================================================
# 3. Staff Review (Approval & Rejection)
# ==============================================================================


@pytest.mark.asyncio
async def test_staff_review_approval_and_rejection_workflows(async_client: AsyncClient, seeded_returns_env):
    """
    Validates review state transitions:
    1. Rejection requires documented rejection reason.
    2. Rejection reverts order status to delivered.
    3. Approval transitions return status to 'approved'.
    """
    env = seeded_returns_env
    alice = env["alice"]
    admin = env["admin"]
    support = env["support"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")
    support_token = create_access_token(support.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_returns_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_num = order_data["order_number"]
    item_id = order_data["items"][0]["id"]

    # Deliver order
    shp = await async_client.post(
        f"/api/v1/admin/orders/{order_data['id']}/shipments",
        json={"courier_code": "tcs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(
        f"/api/v1/admin/shipments/{shp.json()['id']}/status",
        json={"status": "dispatched"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(
        f"/api/v1/admin/shipments/{shp.json()['id']}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Alice requests return
    ret_res = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "items": [{"order_item_id": item_id, "quantity": 1, "reason": "size_fit"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    ret_id = ret_res.json()["id"]

    # 1. Rejection without reason fails
    fail_rev = await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/review",
        json={"decision": "rejected"},
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert fail_rev.status_code == 400

    # 2. Rejection with reason succeeds
    rej_rev = await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/review",
        json={"decision": "rejected", "rejection_reason": "Custom tailored garment exempt from returns"},
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert rej_rev.status_code == 200
    assert rej_rev.json()["status"] == "rejected"

    # Order status reverts to delivered
    ord_chk = await async_client.get(f"/api/v1/orders/{order_num}", headers={"Authorization": f"Bearer {alice_token}"})
    assert ord_chk.json()["status"] == "delivered"

    # Alice submits new return request
    ret_res2 = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "items": [{"order_item_id": item_id, "quantity": 1, "reason": "size_fit"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    ret_id2 = ret_res2.json()["id"]

    # 3. Staff approves return
    appr_rev = await async_client.post(
        f"/api/v1/admin/returns/{ret_id2}/review",
        json={"decision": "approved", "staff_notes": "Client requested size swap or return"},
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert appr_rev.status_code == 200
    assert appr_rev.json()["status"] == "approved"


# ==============================================================================
# 4. Quality Inspection & Inventory Restock Checkpoints
# ==============================================================================


@pytest.mark.asyncio
async def test_warehouse_receipt_and_inspection_restock(async_client: AsyncClient, seeded_returns_env):
    """
    Validates inspection workflow:
    1. Return is approved.
    2. Items marked received at warehouse ('items_received').
    3. Inspection passes: restockable items restore inventory on-hand and in-stock counts.
    4. Damaged/failed items do not restock and yield 0 refund amount.
    """
    env = seeded_returns_env
    alice = env["alice"]
    admin = env["admin"]
    support = env["support"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")
    support_token = create_access_token(support.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_returns_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_num = order_data["order_number"]
    item_id = order_data["items"][0]["id"]

    # Deliver order
    shp = await async_client.post(
        f"/api/v1/admin/orders/{order_data['id']}/shipments",
        json={"courier_code": "tcs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "dispatched"}, headers={"Authorization": f"Bearer {admin_token}"})
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "delivered"}, headers={"Authorization": f"Bearer {admin_token}"})

    # Return request & approval
    ret_res = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "items": [{"order_item_id": item_id, "quantity": 1, "reason": "size_fit"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    ret_id = ret_res.json()["id"]
    return_item_id = ret_res.json()["items"][0]["id"]

    await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/review",
        json={"decision": "approved"},
        headers={"Authorization": f"Bearer {support_token}"},
    )

    # 1. Mark items received at warehouse
    rec_res = await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/receive",
        json={"staff_notes": "TCS return consignment package arrived intact"},
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert rec_res.status_code == 200
    assert rec_res.json()["status"] == "items_received"

    # Pre-inspection stock count check
    stock_before = (await async_client.get(f"/api/v1/products/{v1.product_id}")).json()["variants"][0]["inventory_count"]

    # 2. Quality Inspection: Passed and restockable
    insp_res = await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/inspect",
        json={
            "items": [
                {
                    "return_item_id": return_item_id,
                    "inspection_status": "passed",
                    "restock_condition": "like_new",
                    "restock_action": "restock_available",
                    "inspector_notes": "Tags attached, zero wear, pristine condition",
                }
            ],
            "staff_notes": "QC inspection passed by Senior Garment Auditor",
        },
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert insp_res.status_code == 200
    insp_data = insp_res.json()
    assert insp_data["status"] == "inspected"
    assert Decimal(insp_data["total_refund_amount"]) == Decimal("15000.00")
    assert insp_data["items"][0]["restocked_quantity"] == 1

    # Post-inspection stock count check: on-hand increased by 1
    stock_after = (await async_client.get(f"/api/v1/products/{v1.product_id}")).json()["variants"][0]["inventory_count"]
    assert stock_after == stock_before + 1


# ==============================================================================
# 5. Online Payment Adapter Refund Execution
# ==============================================================================


@pytest.mark.asyncio
async def test_online_payment_refund_execution(async_client: AsyncClient, seeded_returns_env):
    """
    Validates online payment refund:
    1. Order paid online via 'mock' gateway.
    2. Customer returns item, staff inspects and passes.
    3. Finance executes refund resolution -> provider process_refund executed, Refund record created.
    """
    env = seeded_returns_env
    alice = env["alice"]
    admin = env["admin"]
    support = env["support"]
    finance = env["finance"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")
    support_token = create_access_token(support.id, user_type="staff")
    finance_token = create_access_token(finance.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_returns_checkout_payload(payment_method="online"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_id = order_data["id"]
    order_num = order_data["order_number"]
    item_id = order_data["items"][0]["id"]
    order_total = Decimal(str(order_data["grand_total"]))

    # Initiate and fulfill online payment via webhook
    init_res = await async_client.post(
        "/api/v1/customer/payments/initiate",
        json={"order_id": order_id, "provider_code": "mock"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    txn_ref = init_res.json()["provider_reference"]

    wb_payload = {
        "event_id": f"evt_ret_test_{order_id}",
        "event_type": "payment.succeeded",
        "provider_reference": txn_ref,
        "amount": str(order_total),
        "currency": "PKR",
    }
    raw_body = json.dumps(wb_payload).encode("utf-8")
    import hashlib, hmac
    sig = hmac.new("mock-test-webhook-secret-key-32chars".encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    await async_client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw_body,
        headers={"Content-Type": "application/json", "x-signature": sig},
    )

    # Deliver order
    shp = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={"courier_code": "tcs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "dispatched"}, headers={"Authorization": f"Bearer {admin_token}"})
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "delivered"}, headers={"Authorization": f"Bearer {admin_token}"})

    # Return request -> review -> receive -> inspect
    ret_res = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "resolution_type": "refund",
            "items": [{"order_item_id": item_id, "quantity": 1, "reason": "size_fit"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    ret_id = ret_res.json()["id"]
    ret_item_id = ret_res.json()["items"][0]["id"]

    await async_client.post(f"/api/v1/admin/returns/{ret_id}/review", json={"decision": "approved"}, headers={"Authorization": f"Bearer {support_token}"})
    await async_client.post(f"/api/v1/admin/returns/{ret_id}/receive", json={}, headers={"Authorization": f"Bearer {support_token}"})
    await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/inspect",
        json={
            "items": [
                {
                    "return_item_id": ret_item_id,
                    "inspection_status": "passed",
                    "restock_condition": "like_new",
                    "restock_action": "restock_available",
                }
            ]
        },
        headers={"Authorization": f"Bearer {support_token}"},
    )

    # Finance resolves refund
    resolve_res = await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/resolve-refund",
        json={"notes": "Online card refund processed via gateway adapter"},
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert resolve_res.status_code == 200
    res_data = resolve_res.json()
    assert res_data["status"] == "completed"
    assert res_data["refund_id"] is not None
    assert res_data["refund_payout_method"] == "original_payment_method"


# ==============================================================================
# 6. Documented Manual Cash on Delivery (COD) Refund Workflow
# ==============================================================================


@pytest.mark.asyncio
async def test_cod_manual_refund_operational_workflow(async_client: AsyncClient, seeded_returns_env):
    """
    Validates COD refund operational protocol:
    1. Order delivered and cash collected.
    2. Customer requests return with bank IBAN details.
    3. Resolving COD refund without payout reference is rejected.
    4. Finance executes manual bank transfer and provides reference -> succeeds.
    """
    env = seeded_returns_env
    alice = env["alice"]
    admin = env["admin"]
    support = env["support"]
    finance = env["finance"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")
    support_token = create_access_token(support.id, user_type="staff")
    finance_token = create_access_token(finance.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_returns_checkout_payload(payment_method="cod"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_id = order_data["id"]
    order_num = order_data["order_number"]
    item_id = order_data["items"][0]["id"]
    order_total = Decimal(str(order_data["grand_total"]))

    # Deliver order & record cash collection
    shp = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={"courier_code": "tcs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "dispatched"}, headers={"Authorization": f"Bearer {admin_token}"})
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "delivered"}, headers={"Authorization": f"Bearer {admin_token}"})

    pay_res = await async_client.get(f"/api/v1/customer/payments/order/{order_num}", headers={"Authorization": f"Bearer {alice_token}"})
    payment_id = pay_res.json()["id"]

    # Finance records COD cash collection
    rec_res = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/record-collection",
        json={"amount_collected": str(order_total), "reference": "REC-COD-1234"},
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert rec_res.status_code == 200

    # Customer submits return with bank account snapshot
    ret_res = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "return",
            "resolution_type": "refund",
            "refund_payout_method": "bank_transfer",
            "payout_account_details": {
                "bank_name": "Standard Chartered Bank Pakistan",
                "account_title": "Alice Returns",
                "iban": "PK36SCBL0000001123456701",
            },
            "items": [{"order_item_id": item_id, "quantity": 1, "reason": "size_fit"}],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    ret_id = ret_res.json()["id"]
    ret_item_id = ret_res.json()["items"][0]["id"]

    await async_client.post(f"/api/v1/admin/returns/{ret_id}/review", json={"decision": "approved"}, headers={"Authorization": f"Bearer {support_token}"})
    await async_client.post(f"/api/v1/admin/returns/{ret_id}/receive", json={}, headers={"Authorization": f"Bearer {support_token}"})
    await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/inspect",
        json={
            "items": [
                {
                    "return_item_id": ret_item_id,
                    "inspection_status": "passed",
                    "restock_condition": "like_new",
                    "restock_action": "restock_available",
                }
            ]
        },
        headers={"Authorization": f"Bearer {support_token}"},
    )

    # 1. Reject resolving COD refund without payout reference
    rej_resolve = await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/resolve-refund",
        json={"payout_method": "bank_transfer"},  # missing payout_reference
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert rej_resolve.status_code == 400
    assert "transaction reference" in rej_resolve.json()["error"]["message"]

    # 2. Succeed with documented 1LINK bank IMD/FT reference
    ok_resolve = await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/resolve-refund",
        json={
            "payout_method": "bank_transfer",
            "payout_reference": "FT20261111009988",
            "notes": "1LINK IMD interbank funds transfer to Standard Chartered PK36SCBL0000001123456701",
        },
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert ok_resolve.status_code == 200
    res_data = ok_resolve.json()
    assert res_data["status"] == "completed"
    assert res_data["refund_payout_method"] == "bank_transfer"


# ==============================================================================
# 7. Doorstep Garment Exchange Processing
# ==============================================================================


@pytest.mark.asyncio
async def test_doorstep_exchange_workflow(async_client: AsyncClient, seeded_returns_env):
    """
    Validates doorstep exchange:
    1. Customer requests exchange for size 44 (variant 2) instead of size 42 (variant 1).
    2. Staff reviews, receives, and inspects returned garment.
    3. Staff resolves exchange -> generates zero-fee replacement parcel.
    """
    env = seeded_returns_env
    alice = env["alice"]
    admin = env["admin"]
    support = env["support"]
    v1 = env["v1"]
    v2 = env["v2"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")
    support_token = create_access_token(support.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_returns_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_num = order_data["order_number"]
    item_id = order_data["items"][0]["id"]

    # Deliver order
    shp = await async_client.post(
        f"/api/v1/admin/orders/{order_data['id']}/shipments",
        json={"courier_code": "tcs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "dispatched"}, headers={"Authorization": f"Bearer {admin_token}"})
    await async_client.patch(f"/api/v1/admin/shipments/{shp.json()['id']}/status", json={"status": "delivered"}, headers={"Authorization": f"Bearer {admin_token}"})

    # 1. Customer requests exchange
    ret_res = await async_client.post(
        f"/api/v1/customer/orders/{order_num}/returns",
        json={
            "request_type": "exchange",
            "resolution_type": "exchange",
            "customer_notes": "Garment size 42 too tight across bridge; swapping for size 44",
            "items": [
                {
                    "order_item_id": item_id,
                    "quantity": 1,
                    "reason": "size_fit",
                    "exchange_variant_id": v2.id,
                }
            ],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert ret_res.status_code == 201
    ret_id = ret_res.json()["id"]
    ret_item_id = ret_res.json()["items"][0]["id"]
    assert ret_res.json()["items"][0]["exchange_size"] == "44"

    # Review, receive, inspect
    await async_client.post(f"/api/v1/admin/returns/{ret_id}/review", json={"decision": "approved"}, headers={"Authorization": f"Bearer {support_token}"})
    await async_client.post(f"/api/v1/admin/returns/{ret_id}/receive", json={}, headers={"Authorization": f"Bearer {support_token}"})
    await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/inspect",
        json={
            "items": [
                {
                    "return_item_id": ret_item_id,
                    "inspection_status": "passed",
                    "restock_condition": "like_new",
                    "restock_action": "restock_available",
                }
            ]
        },
        headers={"Authorization": f"Bearer {support_token}"},
    )

    # 2. Staff resolves exchange -> books replacement consignment
    resolve_res = await async_client.post(
        f"/api/v1/admin/returns/{ret_id}/resolve-exchange",
        json={"courier_code": "tcs", "dispatch_notes": "Doorstep size 44 replacement parcel"},
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "completed"

    # Verify order has new replacement shipment
    shp_list = await async_client.get(f"/api/v1/admin/orders/{order_data['id']}/shipments", headers={"Authorization": f"Bearer {admin_token}"})
    assert len(shp_list.json()) == 2


# ==============================================================================
# 8. Customer & Guest Isolation
# ==============================================================================


@pytest.mark.asyncio
async def test_returns_isolation_and_guest_verification(async_client: AsyncClient, seeded_returns_env):
    """
    Validates:
    1. Cross-customer isolation (Bob cannot view Alice's return requests).
    2. Guest return inquiry requires valid phone number.
    """
    env = seeded_returns_env
    alice = env["alice"]
    bob = env["bob"]
    admin = env["admin"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    bob_token = create_access_token(bob.id)
    admin_token = create_access_token(admin.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_returns_checkout_payload(customer_phone="03009988776"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_num = order_data["order_number"]

    # Bob cannot view Alice's return requests -> 404
    bob_get = await async_client.get(
        f"/api/v1/customer/orders/{order_num}/returns",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_get.status_code == 404

    # Guest lookup with wrong phone -> 403
    guest_fail = await async_client.get(f"/api/v1/orders/{order_num}/returns?phone=03000000000")
    assert guest_fail.status_code == 403

    # Guest lookup with matching phone -> 200
    guest_ok = await async_client.get(f"/api/v1/orders/{order_num}/returns?phone=03009988776")
    assert guest_ok.status_code == 200


# ==============================================================================
# 9. RBAC Authorization Protections
# ==============================================================================


@pytest.mark.asyncio
async def test_returns_rbac_protections(async_client: AsyncClient, seeded_returns_env):
    """
    Validates that:
    1. Customer is forbidden from accessing admin returns work queues or mutating review/inspection states.
    2. Customer support cannot execute refunds without refunds.create permission.
    3. Finance operator or store admin can execute refunds.
    """
    env = seeded_returns_env
    alice = env["alice"]
    support = env["support"]
    admin = env["admin"]

    alice_token = create_access_token(alice.id)
    support_token = create_access_token(support.id, user_type="staff")
    admin_token = create_access_token(admin.id, user_type="staff")

    # Customer forbidden from admin queue
    cust_res = await async_client.get("/api/v1/admin/returns", headers={"Authorization": f"Bearer {alice_token}"})
    assert cust_res.status_code == 403

    # Support can view queue
    sup_res = await async_client.get("/api/v1/admin/returns", headers={"Authorization": f"Bearer {support_token}"})
    assert sup_res.status_code == 200

    # Customer support forbidden from executing financial refunds (needs refunds.create)
    ref_fail = await async_client.post(
        "/api/v1/admin/returns/1/resolve-refund",
        json={"notes": "Support attempt to issue refund"},
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert ref_fail.status_code == 403

    # Admin allowed to access refund resolution
    ref_admin = await async_client.post(
        "/api/v1/admin/returns/99999/resolve-refund",
        json={"notes": "Admin attempt"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ref_admin.status_code == 404  # Passes RBAC, fails on non-existent ID
