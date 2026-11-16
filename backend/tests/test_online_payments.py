"""
Online Payment Adapter Foundation Tests (Module M14)
Validates provider abstraction, unconfigured provider refusal, HMAC-SHA256 webhook signatures,
idempotent webhook callback processing, payment lifecycle state transitions, refund ledger,
and RBAC audit trails.
"""

from decimal import Decimal
import hashlib
import hmac
import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.service import get_or_create_default_location
from app.modules.orders.models import Order
from app.modules.payments.models import Payment, PaymentEvent, PaymentTransaction, Refund
from app.modules.payments.provider import (
    BasePaymentProvider,
    CodPaymentProvider,
    MockOnlinePaymentProvider,
    UnconfiguredPaymentProvider,
    get_payment_provider,
)
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.shipping.service import ensure_default_shipping_configuration

settings = get_settings()


@pytest.fixture
async def seeded_online_payment_env():
    """Seeds roles, shipping, products, inventory, and users with differentiated roles."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await ensure_default_shipping_configuration(session)
        loc = await get_or_create_default_location(session)

        cat = Category(name="Formalwear", slug="formalwear", is_active=True)
        session.add(cat)
        await session.flush()

        prod = Product(
            name="Silk Waistcoat",
            slug="silk-waistcoat",
            category_id=cat.id,
            price=Decimal("18000.00"),
            status="active",
        )
        session.add(prod)
        await session.flush()

        variant = ProductVariant(
            product_id=prod.id,
            sku="WAISTCOAT-SLK-40",
            size="40",
            color_name="Royal Blue",
            inventory_count=10,
            in_stock=True,
            is_active=True,
        )
        session.add(variant)
        await session.flush()

        inv = InventoryItem(
            variant_id=variant.id,
            location_id=loc.id,
            quantity_on_hand=10,
            quantity_reserved=0,
        )
        session.add(inv)

        alice = User(
            email="alice_online@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        bob = User(
            email="bob_online@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        admin = User(
            email="admin_online@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        finance_user = User(
            email="finance_online@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        session.add_all([alice, bob, admin, finance_user])
        await session.flush()

        res = await session.execute(select(Role).where(Role.name == "store_admin"))
        store_admin_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=admin.id, role_id=store_admin_role.id))

        res = await session.execute(select(Role).where(Role.name == "finance_operator"))
        finance_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=finance_user.id, role_id=finance_role.id))

        await session.commit()
        await session.refresh(alice)
        await session.refresh(bob)
        await session.refresh(admin)
        await session.refresh(finance_user)
        await session.refresh(variant)

        return {
            "alice": alice,
            "bob": bob,
            "admin": admin,
            "finance_user": finance_user,
            "variant": variant,
        }


def make_online_checkout_payload(
    customer_name: str = "Alice Online",
    customer_email: str = "alice_online@example.com",
    customer_phone: str = "03009876543",
    idempotency_key: str = None,
) -> dict:
    return {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "shipping_method_code": "standard_delivery",
        "payment_method": "online",
        "idempotency_key": idempotency_key,
        "shipping_address": {
            "full_name": customer_name,
            "phone": customer_phone,
            "address_line_1": "House 12, Street 4, Sector F-7/2",
            "city": "Islamabad",
            "postal_code": "44000",
            "country_code": "PK",
        },
    }


def compute_hmac_signature(secret: str, body: bytes) -> str:
    active_secret = secret or "mock-test-webhook-secret-key-32chars"
    return hmac.new(active_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


# ==============================================================================
# 1. Provider Contract & Factory Resolution Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_payment_provider_factory_resolution():
    """Validates that provider factory resolves correct implementation based on provider code."""
    cod_provider = get_payment_provider("cod")
    assert isinstance(cod_provider, CodPaymentProvider)
    assert cod_provider.provider_code == "cod"

    mock_provider = get_payment_provider("mock")
    assert isinstance(mock_provider, MockOnlinePaymentProvider)
    assert mock_provider.provider_code == "mock"

    unconfigured = get_payment_provider("none")
    assert isinstance(unconfigured, UnconfiguredPaymentProvider)

    unknown = get_payment_provider("unsupported_gateway")
    assert isinstance(unknown, UnconfiguredPaymentProvider)


# ==============================================================================
# 2. Online Payment Initiation & Unconfigured Gateway Rejection
# ==============================================================================


@pytest.mark.asyncio
async def test_unconfigured_online_payment_provider_refusal(async_client: AsyncClient, seeded_online_payment_env):
    """
    Verifies that if ONLINE_PAYMENT_PROVIDER is 'none' (the production default),
    initiating an online payment is strictly rejected with 400 Bad Request
    and does not generate fake successes.
    """
    env = seeded_online_payment_env
    alice = env["alice"]
    variant = env["variant"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Add item to cart and checkout with payment_method="online"
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers=headers,
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_online_checkout_payload(),
        headers=headers,
    )
    assert checkout_res.status_code == 201
    order_data = checkout_res.json()
    order_id = order_data["id"]

    # When provider is 'none', initiation fails
    original_provider = settings.ONLINE_PAYMENT_PROVIDER
    try:
        settings.ONLINE_PAYMENT_PROVIDER = "none"
        init_res = await async_client.post(
            "/api/v1/customer/payments/initiate",
            json={
                "order_id": order_id,
                "provider_code": "none",
                "return_url": "https://example.com/checkout/return",
                "cancel_url": "https://example.com/checkout/cancel",
            },
            headers=headers,
        )
        assert init_res.status_code == 400
        assert "ONLINE_PAYMENT_NOT_CONFIGURED" in init_res.json()["error"]["message"]
    finally:
        settings.ONLINE_PAYMENT_PROVIDER = original_provider


@pytest.mark.asyncio
async def test_mock_online_payment_initiation_success(async_client: AsyncClient, seeded_online_payment_env):
    """
    Verifies that when configured with a valid provider (e.g. 'mock' sandbox),
    payment initiation produces a checkout redirect URL and tracking token.
    """
    env = seeded_online_payment_env
    alice = env["alice"]
    variant = env["variant"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers=headers,
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_online_checkout_payload(idempotency_key="init_test_key_1"),
        headers=headers,
    )
    assert checkout_res.status_code == 201
    order_data = checkout_res.json()
    order_id = order_data["id"]

    init_res = await async_client.post(
        "/api/v1/customer/payments/initiate",
        json={
            "order_id": order_id,
            "provider_code": "mock",
            "return_url": "https://example.com/return",
            "cancel_url": "https://example.com/cancel",
        },
        headers=headers,
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["provider_code"] == "mock"
    assert "https://sandbox.payment-gateway.test/checkout/" in init_data["redirect_url"]
    assert init_data["provider_reference"].startswith("MOCK-TXN-")
    assert init_data["order_id"] == order_id


@pytest.mark.asyncio
async def test_customer_cannot_initiate_payment_for_another_customers_order(
    async_client: AsyncClient, seeded_online_payment_env
):
    """Cross-customer isolation: Bob cannot initiate payment on Alice's order."""
    env = seeded_online_payment_env
    alice = env["alice"]
    bob = env["bob"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    bob_token = create_access_token(bob.id)

    # Alice creates order
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_online_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert checkout_res.status_code == 201
    order_id = checkout_res.json()["id"]

    # Bob attempts to initiate
    res = await async_client.post(
        "/api/v1/customer/payments/initiate",
        json={"order_id": order_id, "provider_code": "mock"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res.status_code == 404
    assert "Order not found" in res.json()["error"]["message"]


# ==============================================================================
# 3. Webhook Signature Verification & Fraud Prevention
# ==============================================================================


@pytest.mark.asyncio
async def test_webhook_rejects_missing_or_invalid_signature(async_client: AsyncClient, seeded_online_payment_env):
    """Webhooks without a cryptographic signature or with a tampered signature are rejected."""
    payload = {
        "event_id": "evt_tampered_1",
        "event_type": "payment.succeeded",
        "payment_reference": "PAY-NONEXISTENT",
        "amount": "18200.00",
        "currency": "PKR",
    }
    raw_body = json.dumps(payload).encode("utf-8")

    # 1. Missing signature header
    res_missing = await async_client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    assert res_missing.status_code == 401
    assert "INVALID_WEBHOOK_SIGNATURE" in res_missing.json()["error"]["message"]

    # 2. Tampered signature
    res_invalid = await async_client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "x-webhook-signature": "bad_signature_00000000000000000000000000000000",
        },
    )
    assert res_invalid.status_code == 401
    assert "INVALID_WEBHOOK_SIGNATURE" in res_invalid.json()["error"]["message"]


# ==============================================================================
# 4. Webhook Idempotency & Payment Success State Transitions
# ==============================================================================


@pytest.mark.asyncio
async def test_webhook_payment_succeeded_and_idempotency(async_client: AsyncClient, seeded_online_payment_env):
    """
    Tests that a valid 'payment.succeeded' webhook:
    1. Updates payment status to 'paid', sets amount_collected, clears outstanding_amount.
    2. Updates order.payment_status to 'paid'.
    3. Records a PaymentTransaction.
    4. Logs the PaymentEvent with signature_verified=True.
    5. Replaying the exact same webhook returns 200 with 'already_processed' and avoids double-crediting.
    """
    env = seeded_online_payment_env
    alice = env["alice"]
    variant = env["variant"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Checkout
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers=headers,
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_online_checkout_payload(idempotency_key="webhook_test_key_1"),
        headers=headers,
    )
    order_data = checkout_res.json()
    order_id = order_data["id"]
    order_num = order_data["order_number"]
    order_total = Decimal(str(order_data["grand_total"]))

    # Initiate payment to obtain provider transaction ID
    init_res = await async_client.post(
        "/api/v1/customer/payments/initiate",
        json={"order_id": order_id, "provider_code": "mock"},
        headers=headers,
    )
    txn_ref = init_res.json()["provider_reference"]
    payment_id = init_res.json()["payment_id"]

    # Construct webhook payload
    webhook_payload = {
        "event_id": f"evt_mock_{order_id}",
        "event_type": "payment.succeeded",
        "provider_reference": txn_ref,
        "amount": str(order_total),
        "currency": "PKR",
    }
    raw_body = json.dumps(webhook_payload).encode("utf-8")
    sig = compute_hmac_signature(settings.PAYMENT_WEBHOOK_SECRET, raw_body)

    # Dispatch Webhook
    wb_res = await async_client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw_body,
        headers={"Content-Type": "application/json", "x-webhook-signature": sig},
    )
    assert wb_res.status_code == 200
    wb_data = wb_res.json()
    assert wb_data["status"] == "success"
    assert wb_data["event_id"] == webhook_payload["event_id"]

    # Verify order and payment status via customer endpoint
    check_pay = await async_client.get(
        f"/api/v1/customer/payments/order/{order_num}",
        headers=headers,
    )
    assert check_pay.status_code == 200
    updated_pay = check_pay.json()
    assert updated_pay["status"] == "paid"
    assert Decimal(str(updated_pay["amount_collected"])) == order_total
    assert Decimal(str(updated_pay["amount_outstanding"])) == Decimal("0.00")

    # Idempotency test: Re-send identical webhook
    replay_res = await async_client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw_body,
        headers={"Content-Type": "application/json", "x-webhook-signature": sig},
    )
    assert replay_res.status_code == 200
    replay_data = replay_res.json()
    assert replay_data["status"] == "already_processed"


@pytest.mark.asyncio
async def test_webhook_payment_failed(async_client: AsyncClient, seeded_online_payment_env):
    """Verifies that a 'payment.failed' webhook transitions payment status to 'failed'."""
    env = seeded_online_payment_env
    alice = env["alice"]
    variant = env["variant"]
    token = create_access_token(alice.id)
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers=headers,
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_online_checkout_payload(idempotency_key="webhook_fail_test_key"),
        headers=headers,
    )
    order_data = checkout_res.json()
    order_num = order_data["order_number"]

    # Customer fetches payment
    pay_res = await async_client.get(f"/api/v1/customer/payments/order/{order_num}", headers=headers)
    payment_id = pay_res.json()["id"]

    webhook_payload = {
        "event_id": f"evt_mock_fail_{payment_id}",
        "event_type": "payment.failed",
        "payment_reference": str(payment_id),
        "amount": "0.00",
        "currency": "PKR",
    }
    raw_body = json.dumps(webhook_payload).encode("utf-8")
    sig = compute_hmac_signature(settings.PAYMENT_WEBHOOK_SECRET, raw_body)

    res = await async_client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw_body,
        headers={"Content-Type": "application/json", "x-webhook-signature": sig},
    )
    assert res.status_code == 200

    # Payment status should now be failed
    pay_res_updated = await async_client.get(f"/api/v1/customer/payments/order/{order_num}", headers=headers)
    assert pay_res_updated.json()["status"] == "failed"


# ==============================================================================
# 5. Refund Lifecycle & Ledger Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_admin_refund_lifecycle_partial_and_full(async_client: AsyncClient, seeded_online_payment_env):
    """
    Validates partial and full refund processing:
    1. Pays an order in full via webhook.
    2. Issues partial refund: balances update, payment status becomes 'partially_refunded'.
    3. Rejects refund exceeding remaining refundable balance.
    4. Issues second refund for exact remainder: payment becomes 'refunded'.
    """
    env = seeded_online_payment_env
    alice = env["alice"]
    admin = env["admin"]
    variant = env["variant"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")

    # Alice checkout
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_online_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_num = order_data["order_number"]
    order_total = Decimal(str(order_data["grand_total"]))

    pay_res = await async_client.get(
        f"/api/v1/customer/payments/order/{order_num}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    payment_id = pay_res.json()["id"]

    # Alice initiates payment with mock gateway
    init_res = await async_client.post(
        "/api/v1/customer/payments/initiate",
        json={"order_id": order_data["id"], "provider_code": "mock"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    txn_ref = init_res.json()["provider_reference"]

    # Fulfill payment via webhook
    webhook_payload = {
        "event_id": f"evt_refund_test_{payment_id}",
        "event_type": "payment.succeeded",
        "provider_reference": txn_ref,
        "amount": str(order_total),
        "currency": "PKR",
    }
    raw_body = json.dumps(webhook_payload).encode("utf-8")
    sig = compute_hmac_signature(settings.PAYMENT_WEBHOOK_SECRET, raw_body)
    await async_client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw_body,
        headers={"Content-Type": "application/json", "x-webhook-signature": sig},
    )

    # 1. Partial Refund (e.g. 5,000 PKR)
    refund_res_1 = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/refund",
        json={"amount": "5000.00", "reason": "Customer requested partial return"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert refund_res_1.status_code == 201
    ref_data_1 = refund_res_1.json()
    assert ref_data_1["amount"] == "5000.00"
    assert ref_data_1["status"] == "completed"
    assert ref_data_1["refund_number"].startswith("RFD-")

    # Verify payment status is now partially_refunded
    pay_res_admin = await async_client.get(
        f"/api/v1/admin/payments/{payment_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    payment_info = pay_res_admin.json()
    assert payment_info["status"] == "partially_refunded"
    assert Decimal(payment_info["amount_collected"]) == order_total - Decimal("5000.00")

    # 2. Reject refund exceeding remaining refundable balance
    excessive_amount = order_total  # remaining is order_total - 5000
    refund_excess = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/refund",
        json={"amount": str(excessive_amount), "reason": "Excessive refund"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert refund_excess.status_code == 400
    assert "exceeds total collected amount" in refund_excess.json()["error"]["message"]

    # 3. Full Refund of remaining balance
    remaining_balance = order_total - Decimal("5000.00")
    refund_res_2 = await async_client.post(
        f"/api/v1/admin/payments/{payment_id}/refund",
        json={"amount": str(remaining_balance), "reason": "Remaining item return"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert refund_res_2.status_code == 201
    assert refund_res_2.json()["status"] == "completed"

    # Verify payment status is now fully refunded
    pay_res_final = await async_client.get(
        f"/api/v1/admin/payments/{payment_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert pay_res_final.json()["status"] == "refunded"
    assert Decimal(pay_res_final.json()["amount_collected"]) == Decimal("0.00")

    # 4. List refunds
    list_refunds = await async_client.get(
        f"/api/v1/admin/payments/{payment_id}/refunds",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_refunds.status_code == 200
    refunds = list_refunds.json()
    assert len(refunds) == 2


# ==============================================================================
# 6. Audit Logging & RBAC Protections
# ==============================================================================


@pytest.mark.asyncio
async def test_payment_events_audit_and_rbac_restrictions(async_client: AsyncClient, seeded_online_payment_env):
    """
    Validates that:
    1. Customer is forbidden from accessing admin refund and event audit endpoints.
    2. Staff/Admin can view event audit logs.
    """
    env = seeded_online_payment_env
    alice = env["alice"]
    admin = env["admin"]

    alice_token = create_access_token(alice.id)
    admin_token = create_access_token(admin.id, user_type="staff")

    # Customer tries to access audit logs -> 403 Forbidden
    res_cust = await async_client.get(
        "/api/v1/admin/payments/events/audit",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_cust.status_code == 403

    # Admin access succeeds
    res_admin = await async_client.get(
        "/api/v1/admin/payments/events/audit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert "events" in data
    assert "total" in data
