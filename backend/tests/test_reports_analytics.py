"""
Reports & Analytics Tests (Module M22)
Tests store reporting APIs: sales summaries, order counts, financial metric distinctions,
revenue vs COD outstanding, time-series trends, best-selling products, inventory reports,
customer analytics, returns/refunds, and role-based access control.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.auth.models import User
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.inventory.models import InventoryItem, InventoryLocation
from app.modules.inventory.service import get_or_create_default_location
from app.modules.orders.models import Order, OrderItem
from app.modules.payments.models import Payment, Refund
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.returns.models import ReturnRequest
from tests.conftest import TestingSessionLocal


async def ensure_roles_seeded(session: AsyncSession) -> None:
    """Ensure system roles and permissions exist."""
    await seed_system_roles_and_permissions(session)
    await session.commit()


async def create_user_with_role(
    session: AsyncSession,
    email: str,
    role_name: str,
    user_type: str = "staff",
) -> User:
    """Helper to create a user and assign a system role."""
    await ensure_roles_seeded(session)

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


async def seed_reporting_test_data(session: AsyncSession):
    """Seed catalog, orders, payments, refunds, and returns for analytics verification."""
    # 1. Product & Variants
    category = Category(name=f"Prêt Formal {datetime.now(timezone.utc).timestamp()}", slug=f"pret-formal-{datetime.now(timezone.utc).timestamp()}", is_active=True)
    session.add(category)
    await session.flush()

    prod1 = Product(
        name="Embroidered Silk Kurti",
        slug=f"embroidered-silk-kurti-{datetime.now(timezone.utc).timestamp()}",
        price=Decimal("12000.00"),
        status="active",
        category_id=category.id,
    )
    prod2 = Product(
        name="Lawn Digital 3-Piece",
        slug=f"lawn-digital-3pc-{datetime.now(timezone.utc).timestamp()}",
        price=Decimal("8500.00"),
        status="active",
        category_id=category.id,
    )
    session.add_all([prod1, prod2])
    await session.flush()

    var1 = ProductVariant(
        product_id=prod1.id,
        sku=f"KURTI-SLK-S-{datetime.now(timezone.utc).timestamp()}",
        size="Small",
        color_name="Ivory",
        price=Decimal("12000.00"),
        is_active=True,
    )
    var2 = ProductVariant(
        product_id=prod2.id,
        sku=f"LAWN-3PC-M-{datetime.now(timezone.utc).timestamp()}",
        size="Medium",
        color_name="Cobalt Blue",
        price=Decimal("8500.00"),
        is_active=True,
    )
    session.add_all([var1, var2])
    await session.flush()

    # 2. Inventory Items
    loc = await get_or_create_default_location(session)
    inv1 = InventoryItem(
        variant_id=var1.id,
        location_id=loc.id,
        quantity_on_hand=3,  # Below reorder threshold 5 -> low stock!
        quantity_reserved=1,
        reorder_threshold=5,
    )
    inv2 = InventoryItem(
        variant_id=var2.id,
        location_id=loc.id,
        quantity_on_hand=50,
        quantity_reserved=2,
        reorder_threshold=5,
    )
    session.add_all([inv1, inv2])
    await session.flush()

    # 3. Customer User
    customer = User(
        email=f"client_{datetime.now(timezone.utc).timestamp()}@uwearnova.com",
        password_hash=hash_password("ClientPass123!"),
        status="active",
        user_type="customer",
    )
    session.add(customer)
    await session.flush()

    # 4. Orders
    # Order A: Delivered card order (recognized revenue)
    now = datetime.now(timezone.utc)
    order_a = Order(
        order_number=f"UNV-REP-A-{now.timestamp()}",
        user_id=customer.id,
        customer_email=customer.email,
        customer_phone="+923001234567",
        customer_name="Amina Khan",
        status="delivered",
        payment_status="paid",
        fulfillment_status="fulfilled",
        payment_method="card",
        currency_code="PKR",
        subtotal=Decimal("24000.00"),
        discount_total=Decimal("2000.00"),
        shipping_total=Decimal("500.00"),
        tax_total=Decimal("0.00"),
        grand_total=Decimal("22500.00"),
        shipping_method_code="express",
        shipping_method_name="Express Air",
        shipping_address_snapshot='{"city": "Karachi", "street": "Clifton Block 4"}',
    )
    session.add(order_a)
    await session.flush()

    item_a1 = OrderItem(
        order_id=order_a.id,
        product_id=prod1.id,
        variant_id=var1.id,
        product_name_snapshot="Embroidered Silk Kurti",
        product_slug_snapshot="embroidered-silk-kurti",
        sku_snapshot=var1.sku,
        size_snapshot="Small",
        color_snapshot="Ivory",
        unit_price=Decimal("12000.00"),
        quantity=2,
        line_discount=Decimal("2000.00"),
        line_total=Decimal("22000.00"),
    )
    session.add(item_a1)

    pay_a = Payment(
        order_id=order_a.id,
        payment_method="card",
        provider_code="paymob",
        status="reconciled",
        currency_code="PKR",
        amount=Decimal("22500.00"),
        amount_collected=Decimal("22500.00"),
        amount_outstanding=Decimal("0.00"),
    )
    session.add(pay_a)
    await session.flush()

    # Refund on Order A: PKR 4,000 completed refund
    refund_a = Refund(
        refund_number=f"RFD-{now.timestamp()}",
        order_id=order_a.id,
        payment_id=pay_a.id,
        amount=Decimal("4000.00"),
        currency_code="PKR",
        reason="Minor stitching variation",
        status="completed",
    )
    session.add(refund_a)

    # Order B: COD active processing order (outstanding COD)
    order_b = Order(
        order_number=f"UNV-REP-B-{now.timestamp()}",
        user_id=customer.id,  # Repeat customer!
        customer_email=customer.email,
        customer_phone="+923001234567",
        customer_name="Amina Khan",
        status="processing",
        payment_status="unpaid",
        fulfillment_status="unfulfilled",
        payment_method="cod",
        currency_code="PKR",
        subtotal=Decimal("8500.00"),
        discount_total=Decimal("0.00"),
        shipping_total=Decimal("300.00"),
        tax_total=Decimal("0.00"),
        grand_total=Decimal("8800.00"),
        shipping_method_code="standard",
        shipping_method_name="Standard Overland",
        shipping_address_snapshot='{"city": "Lahore", "street": "Gulberg III"}',
    )
    session.add(order_b)
    await session.flush()

    item_b1 = OrderItem(
        order_id=order_b.id,
        product_id=prod2.id,
        variant_id=var2.id,
        product_name_snapshot="Lawn Digital 3-Piece",
        product_slug_snapshot="lawn-digital-3pc",
        sku_snapshot=var2.sku,
        size_snapshot="Medium",
        color_snapshot="Cobalt Blue",
        unit_price=Decimal("8500.00"),
        quantity=1,
        line_discount=Decimal("0.00"),
        line_total=Decimal("8500.00"),
    )
    session.add(item_b1)

    pay_b = Payment(
        order_id=order_b.id,
        payment_method="cod",
        provider_code="cod",
        status="confirmed",
        currency_code="PKR",
        amount=Decimal("8800.00"),
        amount_collected=Decimal("0.00"),
        amount_outstanding=Decimal("8800.00"),
    )
    session.add(pay_b)

    # Order C: Cancelled Guest order
    order_c = Order(
        order_number=f"UNV-REP-C-{now.timestamp()}",
        user_id=None,  # Guest
        customer_email="guest_buyer@example.com",
        customer_phone="+923009999999",
        customer_name="Guest Shopper",
        status="cancelled",
        payment_status="failed",
        fulfillment_status="cancelled",
        payment_method="cod",
        currency_code="PKR",
        subtotal=Decimal("5000.00"),
        discount_total=Decimal("0.00"),
        shipping_total=Decimal("300.00"),
        tax_total=Decimal("0.00"),
        grand_total=Decimal("5300.00"),
        shipping_method_code="standard",
        shipping_method_name="Standard",
        shipping_address_snapshot='{"city": "Islamabad", "street": "F-7/2"}',
    )
    session.add(order_c)

    # Return request on Order A
    ret_req = ReturnRequest(
        request_number=f"RET-REP-{now.timestamp()}",
        order_id=order_a.id,
        user_id=customer.id,
        request_type="return",
        status="completed",
        resolution_type="refund",
        refund_id=refund_a.id,
        customer_notes="Return approved and completed",
    )
    session.add(ret_req)

    await session.commit()
    return {
        "customer": customer,
        "order_a": order_a,
        "order_b": order_b,
        "order_c": order_c,
        "prod1": prod1,
        "prod2": prod2,
        "var1": var1,
        "var2": var2,
    }


@pytest.fixture
async def reporting_context():
    """Fixture providing initialized data and admin auth headers."""
    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(
            session, f"admin_{datetime.now(timezone.utc).timestamp()}@uwearnova.com", "store_admin"
        )
        data = await seed_reporting_test_data(session)
        headers = {"Authorization": f"Bearer {create_access_token(user_id=admin.id, user_type='staff')}"}
        return {"admin": admin, "headers": headers, "data": data}


@pytest.mark.asyncio
async def test_reports_overview_financial_distinction_and_order_counts(
    async_client: AsyncClient, reporting_context: dict
):
    """
    Verify top-level reporting overview.
    Ensures clear distinction between:
    - Gross Order Value (excluding cancelled)
    - Recognized Revenue (delivered minus refunded)
    - Collected Payments
    - Outstanding COD
    """
    headers = reporting_context["headers"]
    response = await async_client.get("/api/v1/admin/reports/overview", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()

    fin = data["financials"]
    assert fin["currency_code"] == "PKR"
    # Gross Order Value: must include active orders A (22,500) and B (8,800) = 31,300 (excluding cancelled order C)
    assert Decimal(fin["gross_order_value"]) >= Decimal("31300.00")
    # Recognized Revenue: Order A delivered (22,500) minus refund (4,000) = 18,500
    assert Decimal(fin["recognized_revenue"]) >= Decimal("18500.00")
    # Collected Payments: Order A collected = 22,500
    assert Decimal(fin["collected_payments"]) >= Decimal("22500.00")
    # Outstanding COD: Order B outstanding = 8,800
    assert Decimal(fin["outstanding_cod"]) >= Decimal("8800.00")
    # Total Refunded: 4,000
    assert Decimal(fin["total_refunded"]) >= Decimal("4000.00")

    counts = data["order_counts"]
    assert counts["total_orders"] >= 3
    assert counts["completed_orders"] >= 1
    assert counts["cancelled_orders"] >= 1
    assert Decimal(counts["average_order_value"]) > 0

    inv = data["inventory_health"]
    assert inv["total_skus"] >= 2
    assert inv["low_stock_variant_count"] >= 1

    cust = data["customer_metrics"]
    assert cust["total_registered_customers"] >= 1
    assert cust["repeat_customers_count"] >= 1


@pytest.mark.asyncio
async def test_sales_trends_time_series(async_client: AsyncClient, reporting_context: dict):
    """Verify daily time-series sales trend endpoint with interval and date filters."""
    headers = reporting_context["headers"]
    response = await async_client.get("/api/v1/admin/reports/sales?interval=day", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["interval"] == "day"
    assert data["currency_code"] == "PKR"
    assert Decimal(data["total_gross_sales"]) > 0
    assert Decimal(data["total_net_sales"]) > 0
    assert len(data["points"]) > 0

    point = data["points"][0]
    assert "date" in point
    assert point["order_count"] > 0
    assert Decimal(point["gross_sales"]) > 0


@pytest.mark.asyncio
async def test_payment_breakdowns_and_cod_reconciliation(
    async_client: AsyncClient, reporting_context: dict
):
    """Verify payment methods breakdown and COD reconciliation health metrics."""
    headers = reporting_context["headers"]
    response = await async_client.get("/api/v1/admin/reports/payments", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["currency_code"] == "PKR"
    assert data["total_payments_count"] >= 2
    assert Decimal(data["total_amount"]) > 0
    assert Decimal(data["total_collected"]) > 0

    methods = {m["payment_method"]: m for m in data["by_method"]}
    assert "cod" in methods
    assert "card" in methods
    assert Decimal(methods["cod"]["outstanding_amount"]) > 0
    assert Decimal(methods["card"]["collected_amount"]) > 0

    cod_rec = data["cod_reconciliation"]
    assert cod_rec["total_cod_orders"] >= 1
    assert Decimal(cod_rec["cod_outstanding_amount"]) > 0


@pytest.mark.asyncio
async def test_best_selling_products_reporting(
    async_client: AsyncClient, reporting_context: dict
):
    """Verify top-selling catalog items ranked by units sold and revenue."""
    headers = reporting_context["headers"]
    response = await async_client.get(
        "/api/v1/admin/reports/products/best-sellers?limit=5", headers=headers
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data["items"]) >= 1
    top_item = data["items"][0]
    assert "product_title" in top_item
    assert "sku" in top_item
    assert top_item["units_sold"] >= 1
    assert Decimal(top_item["gross_revenue"]) > 0


@pytest.mark.asyncio
async def test_inventory_valuation_and_low_stock_alerts(
    async_client: AsyncClient, reporting_context: dict
):
    """Verify inventory report with valuation, unit aggregates, and low-stock filter."""
    headers = reporting_context["headers"]

    # 1. Full inventory report
    resp_all = await async_client.get("/api/v1/admin/reports/inventory", headers=headers)
    assert resp_all.status_code == 200, resp_all.text
    data_all = resp_all.json()

    assert data_all["total_skus"] >= 2
    assert data_all["total_units_on_hand"] > 0
    assert data_all["low_stock_count"] >= 1
    assert Decimal(data_all["estimated_inventory_value"]) > 0
    assert len(data_all["items"]) >= 2

    # 2. Filter for low-stock items only
    resp_low = await async_client.get(
        "/api/v1/admin/reports/inventory?low_stock_only=true", headers=headers
    )
    assert resp_low.status_code == 200, resp_low.text
    data_low = resp_low.json()

    assert len(data_low["items"]) >= 1
    for item in data_low["items"]:
        assert item["is_low_stock"] is True


@pytest.mark.asyncio
async def test_customer_statistics_and_top_spenders(
    async_client: AsyncClient, reporting_context: dict
):
    """Verify customer acquisition, registered vs guest purchasing, and top buyers."""
    headers = reporting_context["headers"]
    response = await async_client.get("/api/v1/admin/reports/customers", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["total_registered_customers"] >= 1
    assert data["registered_orders_count"] >= 1
    assert data["repeat_buyer_count"] >= 1
    assert len(data["top_customers"]) >= 1

    top_buyer = data["top_customers"][0]
    assert "customer_email" in top_buyer
    assert Decimal(top_buyer["total_spend"]) > 0


@pytest.mark.asyncio
async def test_returns_and_refunds_summary(
    async_client: AsyncClient, reporting_context: dict
):
    """Verify returns volume, return rate %, and processed refund totals."""
    headers = reporting_context["headers"]
    response = await async_client.get("/api/v1/admin/reports/returns-refunds", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["currency_code"] == "PKR"
    assert data["total_return_requests"] >= 1
    assert Decimal(data["return_rate_percentage"]) > 0
    assert data["total_refunds_processed_count"] >= 1
    assert Decimal(data["total_refunds_processed_amount"]) >= Decimal("4000.00")


@pytest.mark.asyncio
async def test_reports_rbac_isolation(async_client: AsyncClient):
    """Verify strict RBAC protection on analytics endpoints."""
    async with TestingSessionLocal() as session:
        # User lacking reports.read (customer_support role only has dashboard/orders/returns)
        unauth_staff = await create_user_with_role(
            session, f"support_rep_{datetime.now(timezone.utc).timestamp()}@uwearnova.com", "customer_support"
        )

    # 1. Unauthenticated request -> 401
    resp_unauth = await async_client.get("/api/v1/admin/reports/overview")
    assert resp_unauth.status_code == 401

    # 2. Staff without reports.read permission -> 403 Forbidden
    headers_forbidden = {
        "Authorization": f"Bearer {create_access_token(user_id=unauth_staff.id, user_type='staff')}"
    }
    resp_forbidden = await async_client.get("/api/v1/admin/reports/overview", headers=headers_forbidden)
    assert resp_forbidden.status_code == 403
