"""
Module M19 — Admin Orders, Customers, and Payments APIs Test Suite
Verifies administrative order management:
- Order listing with pagination, search, and faceted filtering (status, payment_status, payment_method)
- Comprehensive administrative order details, payments, shipments, and returns inspection
- Order confirmation (pending -> confirmed) and cancellation with inventory restock
- Internal operational notes visible only to authorized staff
- Cash on Delivery (COD) management and courier remittance reconciliation
- Customer lookup, account dossier inspection, and account status management (suspension/disabling)
- Strict RBAC enforcement and immutable audit trail logging
"""

from decimal import Decimal
from typing import Optional
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.audit.models import AuditLog
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Product, ProductVariant
from app.modules.catalog.seed_data import seed_catalog_products
from app.modules.customer.models import Address, CustomerProfile
from app.modules.inventory.schemas import StockAdjustmentRequest
from app.modules.inventory.service import adjust_stock
from app.modules.orders.models import Order
from app.modules.payments.models import Payment
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.shipping.service import ensure_default_shipping_configuration


@pytest.fixture
async def setup_order_admin_data() -> None:
    """Fixture that initializes RBAC roles, shipping configuration, and initial inventory."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await ensure_default_shipping_configuration(session)
        await seed_catalog_products(session)
        await session.commit()


async def create_user_with_role(
    session: AsyncSession,
    email: str,
    role_name: str,
    user_type: str = "staff",
) -> User:
    """Helper to create a user and assign a system role."""
    user = User(
        email=email,
        password_hash=hash_password("SecurePassword123!"),
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
    """Helper to generate Authorization header for user."""
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


async def create_test_order(
    async_client: AsyncClient,
    customer_user: Optional[User] = None,
    customer_email: str = "customer_test@example.com",
    payment_method: str = "cod",
) -> dict:
    """Helper to place an order via storefront checkout."""
    from tests.conftest import TestingSessionLocal

    if customer_user:
        headers = auth_header_for(customer_user)
    else:
        headers = {"X-Anonymous-Cart-Token": f"anon-{customer_email}"}

    # Stock a variant first
    async with TestingSessionLocal() as session:
        var = (await session.execute(select(ProductVariant).limit(1))).scalars().first()
        var_id = var.id
        await adjust_stock(
            session,
            StockAdjustmentRequest(variant_id=var_id, quantity_delta=50, reason="receipt"),
        )
        await session.commit()

    # Add item to cart
    add_cart = await async_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"variant_id": var_id, "quantity": 2},
    )
    assert add_cart.status_code == 200

    # Checkout
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json={
            "customer_name": "Hamza Abbasi",
            "customer_email": customer_email,
            "customer_phone": "03001234567",
            "shipping_address": {
                "full_name": "Hamza Abbasi",
                "phone": "03001234567",
                "address_line_1": "House 12, Street 4, F-7/2",
                "city": "Islamabad",
                "postal_code": "44000",
                "country_code": "PK",
            },
            "shipping_method_code": "standard_delivery",
            "payment_method": payment_method,
        },
    )
    assert checkout_res.status_code == 201
    return checkout_res.json()


# ===========================================================================
# 1. Order Listing, Pagination, and Faceted Filtering Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_order_listing_and_filtering(async_client: AsyncClient, setup_order_admin_data):
    """Admin can list orders with status, payment status, payment method, and search filters."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_orders_m19@uwearnova.com", "store_admin")

    admin_headers = auth_header_for(admin)

    # 1. Create two separate orders
    order1 = await create_test_order(async_client, customer_email="alice_m19@example.com", payment_method="cod")
    order2 = await create_test_order(async_client, customer_email="bob_m19@example.com", payment_method="card")

    # 2. List all orders
    list_res = await async_client.get("/api/v1/admin/orders", headers=admin_headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 2
    assert len(data["orders"]) >= 2

    # 3. Filter by status
    filter_status = await async_client.get(
        "/api/v1/admin/orders?status=pending_confirmation",
        headers=admin_headers,
    )
    assert filter_status.status_code == 200
    for o in filter_status.json()["orders"]:
        assert o["status"] == "pending_confirmation"

    # 4. Filter by payment method
    filter_card = await async_client.get(
        "/api/v1/admin/orders?payment_method=card",
        headers=admin_headers,
    )
    assert filter_card.status_code == 200
    card_orders = filter_card.json()["orders"]
    assert any(o["order_number"] == order2["order_number"] for o in card_orders)
    assert all(o["payment_method"] == "card" for o in card_orders)

    # 5. Search by customer email
    search_res = await async_client.get(
        "/api/v1/admin/orders?search=alice_m19",
        headers=admin_headers,
    )
    assert search_res.status_code == 200
    assert any(o["customer_email"] == "alice_m19@example.com" for o in search_res.json()["orders"])


# ===========================================================================
# 2. Comprehensive Admin Order Detail Inspection
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_order_detail_inspection(async_client: AsyncClient, setup_order_admin_data):
    """Admin detail endpoint returns full order dossier including payments, history, and snapshots."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_inspect_m19@uwearnova.com", "store_admin")

    admin_headers = auth_header_for(admin)
    order = await create_test_order(async_client, customer_email="inspect_m19@example.com")
    order_ref = order["order_number"]

    # Retrieve admin order dossier
    detail_res = await async_client.get(
        f"/api/v1/admin/orders/{order_ref}",
        headers=admin_headers,
    )
    assert detail_res.status_code == 200
    dossier = detail_res.json()
    assert dossier["order_number"] == order_ref
    assert "items" in dossier
    assert len(dossier["items"]) > 0
    assert "payments" in dossier
    assert len(dossier["payments"]) == 1
    assert dossier["payments"][0]["payment_method"] == "cod"
    assert "admin_history" in dossier
    assert len(dossier["admin_history"]) >= 1


# ===========================================================================
# 3. Order Confirmation and Cancellation Flows
# ===========================================================================

@pytest.mark.asyncio
async def test_order_confirmation_and_cancellation_workflow(async_client: AsyncClient, setup_order_admin_data):
    """Admin can confirm pending orders and cancel orders with automatic inventory restocking."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_lifecycle_m19@uwearnova.com", "store_admin")

    admin_headers = auth_header_for(admin)
    order = await create_test_order(async_client, customer_email="lifecycle_m19@example.com")
    order_id = order["id"]

    # 1. Confirm order
    confirm_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/confirm",
        headers=admin_headers,
        json={"note": "Customer verified via phone call"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "confirmed"

    # 2. Attempting to re-confirm confirmed order fails
    reconfirm_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/confirm",
        headers=admin_headers,
    )
    assert reconfirm_res.status_code == 400

    # 3. Cancel order with mandatory reason
    cancel_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/cancel",
        headers=admin_headers,
        json={"reason": "Customer requested cancellation before dispatch"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 4. Attempting to cancel already cancelled order fails
    recancel_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/cancel",
        headers=admin_headers,
        json={"reason": "Duplicate cancel attempt"},
    )
    assert recancel_res.status_code == 400

    # 5. Verify audit logs
    async with TestingSessionLocal() as session:
        logs = (
            await session.execute(
                select(AuditLog)
                .where(AuditLog.entity_type == "order", AuditLog.entity_id == str(order_id))
            )
        ).scalars().all()
        actions = [log.action for log in logs]
        assert "order.status_updated" in actions


# ===========================================================================
# 4. Operational Notes (Hidden from Storefront Customers)
# ===========================================================================

@pytest.mark.asyncio
async def test_order_operational_notes_and_privacy(async_client: AsyncClient, setup_order_admin_data):
    """Staff can append internal operational notes; customer order view must never expose them."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_notes_m19@uwearnova.com", "store_admin")
        customer = User(
            email="cust_privacy_m19@example.com",
            password_hash=hash_password("Pass123!"),
            status="active",
            user_type="customer",
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

    admin_headers = auth_header_for(admin)
    cust_headers = auth_header_for(customer)

    order = await create_test_order(async_client, customer_user=customer, customer_email="cust_privacy_m19@example.com")
    order_id = order["id"]
    order_num = order["order_number"]

    # 1. Admin adds internal operational note
    note_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/notes",
        headers=admin_headers,
        json={"note": "VIP customer: inspect stitching thoroughly before packaging"},
    )
    assert note_res.status_code == 201
    assert "VIP customer" in note_res.json()["note"]

    # 2. Admin retrieves operational notes
    notes_list_res = await async_client.get(
        f"/api/v1/admin/orders/{order_id}/notes",
        headers=admin_headers,
    )
    assert notes_list_res.status_code == 200
    assert any("VIP customer" in n["note"] for n in notes_list_res.json())

    # 3. Customer retrieves order detail: Internal note must NOT be exposed
    cust_view_res = await async_client.get(
        f"/api/v1/customer/orders/{order_num}",
        headers=cust_headers,
    )
    assert cust_view_res.status_code == 200
    cust_text = cust_view_res.text
    assert "VIP customer: inspect stitching thoroughly" not in cust_text


# ===========================================================================
# 5. COD Courier Remittance Reconciliation
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_cod_reconciliation(async_client: AsyncClient, setup_order_admin_data):
    """Admin can reconcile courier cash remittance and synchronize payment status."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_reconcile_m19@uwearnova.com", "store_admin")

    admin_headers = auth_header_for(admin)
    order = await create_test_order(async_client, customer_email="cod_rec_m19@example.com", payment_method="cod")
    order_id = order["id"]
    payable_amount = float(order["grand_total"])

    # Reconcile full cash amount
    reconcile_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/reconcile-cod",
        headers=admin_headers,
        json={
            "remittance_reference": "TCS-REMIT-98231",
            "amount_collected": payable_amount,
            "notes": "Full payment settled via TCS weekly manifest",
        },
    )
    assert reconcile_res.status_code == 200
    assert reconcile_res.json()["payment_status"] == "paid"

    # Check payments subresource
    payments_res = await async_client.get(
        f"/api/v1/admin/orders/{order_id}/payments",
        headers=admin_headers,
    )
    assert payments_res.status_code == 200
    payments = payments_res.json()
    assert len(payments) == 1
    assert payments[0]["settlement_reference"] == "TCS-REMIT-98231"
    assert payments[0]["status"] == "reconciled"
    assert payments[0]["reconciled_at"] is not None


# ===========================================================================
# 6. Customer Lookup & Account Status Management
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_customer_lookup_and_status_management(async_client: AsyncClient, setup_order_admin_data):
    """Admin can search customers, inspect dossiers, and suspend/disable customer accounts."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_cust_m19@uwearnova.com", "store_admin")
        cust_user = User(
            email="zain_malik_m19@example.com",
            phone="03009988776",
            password_hash=hash_password("Pass123!"),
            status="active",
            user_type="customer",
        )
        session.add(cust_user)
        await session.flush()

        profile = CustomerProfile(
            user_id=cust_user.id,
            first_name="Zain",
            last_name="Malik",
        )
        session.add(profile)
        await session.commit()
        cust_id = cust_user.id

    admin_headers = auth_header_for(admin)

    # 1. Search customer by name
    list_res = await async_client.get(
        "/api/v1/admin/customers?search=Zain",
        headers=admin_headers,
    )
    assert list_res.status_code == 200
    customers = list_res.json()["customers"]
    assert any(c["id"] == cust_id for c in customers)

    # 2. Get customer dossier
    dossier_res = await async_client.get(
        f"/api/v1/admin/customers/{cust_id}",
        headers=admin_headers,
    )
    assert dossier_res.status_code == 200
    dossier = dossier_res.json()
    assert dossier["email"] == "zain_malik_m19@example.com"
    assert dossier["profile"]["first_name"] == "Zain"

    # 3. Suspend customer account
    suspend_res = await async_client.patch(
        f"/api/v1/admin/customers/{cust_id}/status",
        headers=admin_headers,
        json={"status": "suspended", "reason": "Repeated fraudulent COD orders refused at door"},
    )
    assert suspend_res.status_code == 200
    assert suspend_res.json()["status"] == "suspended"

    # 4. Verify customer status updated in DB and audit log created
    async with TestingSessionLocal() as session:
        u = await session.get(User, cust_id)
        assert u.status == "suspended"

        log = (
            await session.execute(
                select(AuditLog)
                .where(AuditLog.entity_type == "user", AuditLog.entity_id == str(cust_id))
            )
        ).scalars().first()
        assert log is not None
        assert log.action == "customer.status_updated"


# ===========================================================================
# 7. RBAC & Security Isolation
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_orders_rbac_isolation(async_client: AsyncClient, setup_order_admin_data):
    """Customer accounts are forbidden from accessing admin order and customer endpoints."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        customer = User(
            email="unauth_cust_m19@example.com",
            password_hash=hash_password("Pass123!"),
            status="active",
            user_type="customer",
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

    cust_headers = auth_header_for(customer)

    # 1. Customer cannot list admin orders
    res1 = await async_client.get("/api/v1/admin/orders", headers=cust_headers)
    assert res1.status_code == 403

    # 2. Customer cannot access admin customer directory
    res2 = await async_client.get("/api/v1/admin/customers", headers=cust_headers)
    assert res2.status_code == 403

    # 3. Unauthenticated requests rejected with 401
    res3 = await async_client.get("/api/v1/admin/orders")
    assert res3.status_code == 401
