"""
Staff Operations & Work Queues Tests (Module M20)
Tests role-tailored dashboard summaries, role-specific work queues,
operational order processing, fulfillment packing/dispatch,
warehouse stock operations, customer support ticket management,
task assignments, and strict least-privilege RBAC isolation.
"""

from decimal import Decimal
import json
from typing import Optional
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.auth.models import User
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.fulfillment.models import Shipment, ShipmentItem
from app.modules.inventory.models import InventoryItem, InventoryLocation
from app.modules.inventory.service import get_or_create_default_location
from app.modules.orders.models import Order, OrderItem
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.returns.models import ReturnItem, ReturnRequest
from app.modules.shipping.models import ShippingMethod, ShippingZone
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


def auth_header_for(user: User) -> dict:
    """Generate Authorization header for user."""
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


async def seed_test_inventory(session: AsyncSession) -> ProductVariant:
    """Seed test category, product, variant and inventory location."""
    loc = await get_or_create_default_location(session)

    cat = Category(name="Menswear M20", slug="menswear-m20", is_active=True)
    session.add(cat)
    await session.flush()

    prod = Product(
        name="Oxford Cotton Shirt M20",
        slug="oxford-cotton-shirt-m20",
        description="Staff test shirt",
        category_id=cat.id,
        status="active",
        price=Decimal("4500.00"),
    )
    session.add(prod)
    await session.flush()

    var = ProductVariant(
        product_id=prod.id,
        sku="OXF-WHT-M-M20",
        size="M",
        color_name="White",
        price=Decimal("4500.00"),
        inventory_count=30,
        in_stock=True,
    )
    session.add(var)
    await session.flush()

    inv = InventoryItem(
        variant_id=var.id,
        location_id=loc.id,
        quantity_on_hand=30,
        quantity_reserved=0,
        reorder_threshold=10,
    )
    session.add(inv)
    await session.commit()
    await session.refresh(var)
    return var


# =========================================================================
# 1. Staff Dashboard Role-Tailored Summary Tests
# =========================================================================

@pytest.mark.asyncio
async def test_staff_dashboard_role_tailored_summary(async_client: AsyncClient):
    """
    Verify that staff dashboard returns work queue metrics strictly
    filtered by the calling staff member's assigned role and permissions.
    """
    async with TestingSessionLocal() as session:
        order_mgr = await create_user_with_role(session, "ordermgr_m20@uwearnova.com", "order_manager")
        fulfill_staff = await create_user_with_role(session, "fulfill_m20@uwearnova.com", "fulfillment_staff")
        inv_mgr = await create_user_with_role(session, "invmgr_m20@uwearnova.com", "inventory_manager")
        admin = await create_user_with_role(session, "admin_m20@uwearnova.com", "store_admin", user_type="admin")

    # Order Manager: sees orders_queue_count & returns_queue_count, but NOT fulfillment or inventory
    res = await async_client.get("/api/v1/staff/dashboard", headers=auth_header_for(order_mgr))
    assert res.status_code == 200
    data = res.json()
    assert data["staff_user_id"] == order_mgr.id
    assert "order_manager" in data["roles"]
    assert data["orders_queue_count"] is not None
    assert data["returns_queue_count"] is not None
    assert data["fulfillment_queue_count"] is None
    assert data["inventory_low_stock_count"] is None

    # Fulfillment Staff: sees fulfillment_queue_count, but NOT orders or inventory
    res = await async_client.get("/api/v1/staff/dashboard", headers=auth_header_for(fulfill_staff))
    assert res.status_code == 200
    data = res.json()
    assert data["fulfillment_queue_count"] is not None
    assert data["inventory_low_stock_count"] is None

    # Inventory Manager: sees inventory_low_stock_count, but NOT orders or fulfillment
    res = await async_client.get("/api/v1/staff/dashboard", headers=auth_header_for(inv_mgr))
    assert res.status_code == 200
    data = res.json()
    assert data["inventory_low_stock_count"] is not None
    assert data["fulfillment_queue_count"] is None
    assert data["orders_queue_count"] is None

    # Store Admin: full visibility
    res = await async_client.get("/api/v1/staff/dashboard", headers=auth_header_for(admin))
    assert res.status_code == 200
    data = res.json()
    assert data["orders_queue_count"] is not None
    assert data["fulfillment_queue_count"] is not None
    assert data["inventory_low_stock_count"] is not None
    assert data["returns_queue_count"] is not None


# =========================================================================
# 2. Role-Specific Work Queues Tests
# =========================================================================

@pytest.mark.asyncio
async def test_role_specific_work_queues(async_client: AsyncClient):
    """
    Verify access control and filtering on role-specific work queues:
    - Order Manager accesses /queues/orders
    - Fulfillment Staff accesses /queues/fulfillment
    - Inventory Manager accesses /queues/inventory
    - Customer Support accesses /queues/returns
    - Cross-role unauthorized access is rejected with 403 Forbidden.
    """
    async with TestingSessionLocal() as session:
        order_mgr = await create_user_with_role(session, "om_queues@uwearnova.com", "order_manager")
        fulfill_staff = await create_user_with_role(session, "fs_queues@uwearnova.com", "fulfillment_staff")
        inv_mgr = await create_user_with_role(session, "im_queues@uwearnova.com", "inventory_manager")
        cust_sup = await create_user_with_role(session, "cs_queues@uwearnova.com", "customer_support")

    # 1. Orders queue
    res = await async_client.get("/api/v1/staff/queues/orders", headers=auth_header_for(order_mgr))
    assert res.status_code == 200
    assert "items" in res.json()

    # Inventory manager cannot access orders queue (lacks orders.read)
    res_forbidden = await async_client.get("/api/v1/staff/queues/orders", headers=auth_header_for(inv_mgr))
    assert res_forbidden.status_code == 403

    # 2. Fulfillment queue
    res = await async_client.get("/api/v1/staff/queues/fulfillment", headers=auth_header_for(fulfill_staff))
    assert res.status_code == 200
    assert "items" in res.json()

    # Order manager cannot access fulfillment queue (lacks shipments.manage)
    res_forbidden = await async_client.get("/api/v1/staff/queues/fulfillment", headers=auth_header_for(order_mgr))
    assert res_forbidden.status_code == 403

    # 3. Inventory queue
    res = await async_client.get("/api/v1/staff/queues/inventory", headers=auth_header_for(inv_mgr))
    assert res.status_code == 200
    assert "items" in res.json()

    # Customer support cannot access inventory queue (lacks inventory.read)
    res_forbidden = await async_client.get("/api/v1/staff/queues/inventory", headers=auth_header_for(cust_sup))
    assert res_forbidden.status_code == 403

    # 4. Returns queue
    res = await async_client.get("/api/v1/staff/queues/returns", headers=auth_header_for(cust_sup))
    assert res.status_code == 200
    assert "items" in res.json()

    # Inventory manager cannot access returns queue (lacks returns.read)
    res_forbidden = await async_client.get("/api/v1/staff/queues/returns", headers=auth_header_for(inv_mgr))
    assert res_forbidden.status_code == 403


# =========================================================================
# 3. Operational Order Processing and Fulfillment Workflow
# =========================================================================

@pytest.mark.asyncio
async def test_operational_order_processing_and_fulfillment(async_client: AsyncClient):
    """
    Test end-to-end staff processing workflow:
    1. Order Manager confirms/processes order via /staff/orders/{id}/process.
    2. Fulfillment Staff packs parcel via /staff/fulfillment/{shipment_id}/pack.
    3. Fulfillment Staff dispatches parcel with courier tracking via /staff/fulfillment/{shipment_id}/dispatch.
    """
    async with TestingSessionLocal() as session:
        order_mgr = await create_user_with_role(session, "om_proc@uwearnova.com", "order_manager")
        fulfill_staff = await create_user_with_role(session, "fs_pack@uwearnova.com", "fulfillment_staff")

        # Create test order
        order = Order(
            order_number="UNV-20261111-TEST01",
            customer_email="buyer_proc@uwearnova.com",
            customer_phone="+923001234567",
            customer_name="Ahmad Buyer",
            status="pending_confirmation",
            payment_status="unpaid",
            payment_method="cod",
            fulfillment_status="unfulfilled",
            subtotal=Decimal("5000.00"),
            shipping_total=Decimal("200.00"),
            grand_total=Decimal("5200.00"),
            currency_code="PKR",
            shipping_method_code="standard_delivery",
            shipping_method_name="Standard Courier Delivery",
            shipping_address_snapshot=json.dumps({
                "full_name": "Ahmad Buyer",
                "phone": "+923001234567",
                "address_line_1": "Gulberg III",
                "city": "Lahore",
                "country_code": "PK",
            }),
        )
        session.add(order)
        await session.flush()

        # Create test shipment
        shipment = Shipment(
            shipment_number="SHP-20261111-TEST01",
            order_id=order.id,
            status="allocated",
            courier_code="trax",
            destination_city="Lahore",
            shipping_address_snapshot=json.dumps({"city": "Lahore"}),
        )
        session.add(shipment)
        await session.commit()
        order_id = order.id
        shipment_id = shipment.id

    # 1. Order Manager processes order
    res_proc = await async_client.post(
        f"/api/v1/staff/orders/{order_id}/process",
        headers=auth_header_for(order_mgr),
        json={"notes": "Order phone verification confirmed with customer"},
    )
    assert res_proc.status_code == 200
    assert res_proc.json()["status"] == "confirmed"

    # 2. Fulfillment Staff packs shipment
    res_pack = await async_client.post(
        f"/api/v1/staff/fulfillment/{shipment_id}/pack",
        headers=auth_header_for(fulfill_staff),
        json={"package_weight_kg": 0.85, "package_dimensions": "30x20x5", "notes": "Packed in UniNova gift box"},
    )
    assert res_pack.status_code == 200
    assert res_pack.json()["status"] == "packed"

    # 3. Fulfillment Staff dispatches shipment
    res_disp = await async_client.post(
        f"/api/v1/staff/fulfillment/{shipment_id}/dispatch",
        headers=auth_header_for(fulfill_staff),
        json={"tracking_number": "TRX-9988776655", "notes": "Handed over to Trax courier courier rider"},
    )
    assert res_disp.status_code == 200
    assert res_disp.json()["status"] == "dispatched"
    assert res_disp.json()["tracking_number"] == "TRX-9988776655"


# =========================================================================
# 4. Warehouse Stock Operations Tests
# =========================================================================

@pytest.mark.asyncio
async def test_staff_stock_intake_and_cycle_count(async_client: AsyncClient):
    """
    Test Inventory Controller operations:
    1. Stock intake receipt: /staff/inventory/receive
    2. Physical cycle count adjustment: /staff/inventory/cycle-count
    3. Unauthorized staff attempts rejected with 403.
    """
    async with TestingSessionLocal() as session:
        inv_mgr = await create_user_with_role(session, "im_stock@uwearnova.com", "inventory_manager")
        cust_sup = await create_user_with_role(session, "cs_stock@uwearnova.com", "customer_support")
        variant = await seed_test_inventory(session)
        location = await get_or_create_default_location(session)
        var_id = variant.id
        loc_id = location.id

    # 1. Stock intake (+15 units)
    res_rec = await async_client.post(
        "/api/v1/staff/inventory/receive",
        headers=auth_header_for(inv_mgr),
        json={
            "variant_id": var_id,
            "location_id": loc_id,
            "quantity": 15,
            "batch_reference": "BATCH-2026-NOV-A",
            "notes": "Incoming supplier delivery received",
        },
    )
    assert res_rec.status_code == 200
    data = res_rec.json()
    assert data["quantity_on_hand"] == 45  # 30 + 15

    # 2. Cycle count adjustment (physical count found 42)
    res_cycle = await async_client.post(
        "/api/v1/staff/inventory/cycle-count",
        headers=auth_header_for(inv_mgr),
        json={
            "variant_id": var_id,
            "location_id": loc_id,
            "actual_quantity": 42,
            "reason": "Weekly shelf audit variance (-3 units damaged)",
        },
    )
    assert res_cycle.status_code == 200
    data = res_cycle.json()
    assert data["prior_on_hand"] == 45
    assert data["new_on_hand"] == 42
    assert data["delta"] == -3

    # 3. Customer support cannot adjust inventory
    res_forbidden = await async_client.post(
        "/api/v1/staff/inventory/receive",
        headers=auth_header_for(cust_sup),
        json={"variant_id": var_id, "location_id": loc_id, "quantity": 10},
    )
    assert res_forbidden.status_code == 403


# =========================================================================
# 5. Customer Support Case Handling Tests
# =========================================================================

@pytest.mark.asyncio
async def test_customer_support_case_handling(async_client: AsyncClient):
    """
    Test Customer Support staff handling support tickets:
    1. Create ticket: /staff/support/tickets
    2. Assign ticket to staff: /staff/support/tickets/{id}/assign
    3. Add customer reply message & internal operational note
    4. Update ticket status to resolved
    """
    async with TestingSessionLocal() as session:
        cust_sup = await create_user_with_role(session, "cs_agent@uwearnova.com", "customer_support")
        cust_sup2 = await create_user_with_role(session, "cs_specialist@uwearnova.com", "customer_support")

    # 1. Create support ticket
    res_create = await async_client.post(
        "/api/v1/staff/support/tickets",
        headers=auth_header_for(cust_sup),
        json={
            "customer_email": "client_inquiry@example.com",
            "customer_name": "Fatima Noor",
            "subject": "Exchange request for size Small",
            "category": "sizing_styling",
            "priority": "high",
            "message": "Customer contacted on WhatsApp requesting size exchange.",
        },
    )
    assert res_create.status_code == 201
    ticket = res_create.json()
    assert ticket["ticket_number"].startswith("TKT-")
    assert ticket["status"] == "open"
    ticket_id = ticket["id"]

    # 2. Assign ticket to specialist
    res_assign = await async_client.post(
        f"/api/v1/staff/support/tickets/{ticket_id}/assign",
        headers=auth_header_for(cust_sup),
        json={"staff_user_id": cust_sup2.id},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["assigned_staff_id"] == cust_sup2.id
    assert res_assign.json()["status"] == "in_progress"

    # 3. Add internal note
    res_note = await async_client.post(
        f"/api/v1/staff/support/tickets/{ticket_id}/messages",
        headers=auth_header_for(cust_sup2),
        json={"message": "Checked warehouse stock; size Medium in stock.", "is_internal_note": True},
    )
    assert res_note.status_code == 201
    assert res_note.json()["is_internal_note"] is True

    # 4. Add response message to client
    res_reply = await async_client.post(
        f"/api/v1/staff/support/tickets/{ticket_id}/messages",
        headers=auth_header_for(cust_sup2),
        json={"message": "We have reserved size Medium for your doorstep exchange.", "is_internal_note": False},
    )
    assert res_reply.status_code == 201
    assert res_reply.json()["is_internal_note"] is False

    # 5. Resolve ticket
    res_resolve = await async_client.patch(
        f"/api/v1/staff/support/tickets/{ticket_id}/status",
        headers=auth_header_for(cust_sup2),
        json={"status": "resolved", "resolution_notes": "Doorstep exchange consignment dispatched"},
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "resolved"
    assert res_resolve.json()["resolved_at"] is not None


# =========================================================================
# 6. Staff Task Assignment Lifecycle Tests
# =========================================================================

@pytest.mark.asyncio
async def test_staff_task_assignment_lifecycle(async_client: AsyncClient):
    """
    Test task assignment and execution workflow:
    1. Create task: /staff/tasks
    2. Assign task to staff member: /staff/tasks/{id}/assign
    3. Filter tasks assigned to me: /staff/tasks?assigned_to_me=true
    4. Mark task completed with resolution notes: /staff/tasks/{id}/status
    """
    async with TestingSessionLocal() as session:
        om = await create_user_with_role(session, "om_tasks@uwearnova.com", "order_manager")
        fs = await create_user_with_role(session, "fs_tasks@uwearnova.com", "fulfillment_staff")

    # 1. OM creates task for fulfillment packing
    res_task = await async_client.post(
        "/api/v1/staff/tasks",
        headers=auth_header_for(om),
        json={
            "task_type": "fulfillment_pack",
            "title": "Pack Priority Bridal Order #UNV-991",
            "description": "Double check silk dupatta packaging before dispatch",
            "priority": "urgent",
        },
    )
    assert res_task.status_code == 201
    task_id = res_task.json()["id"]

    # 2. Assign task to fulfillment staff
    res_assign = await async_client.post(
        f"/api/v1/staff/tasks/{task_id}/assign",
        headers=auth_header_for(om),
        json={"staff_user_id": fs.id},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["assigned_staff_id"] == fs.id
    assert res_assign.json()["status"] == "in_progress"

    # 3. Fulfillment staff checks my assigned tasks
    res_my_tasks = await async_client.get(
        "/api/v1/staff/tasks?assigned_to_me=true",
        headers=auth_header_for(fs),
    )
    assert res_my_tasks.status_code == 200
    items = res_my_tasks.json()["items"]
    assert any(t["id"] == task_id for t in items)

    # 4. Fulfillment staff completes task
    res_done = await async_client.patch(
        f"/api/v1/staff/tasks/{task_id}/status",
        headers=auth_header_for(fs),
        json={"status": "completed", "resolution_notes": "Garment inspected, pressed, and sealed in box."},
    )
    assert res_done.status_code == 200
    assert res_done.json()["status"] == "completed"
    assert res_done.json()["completed_at"] is not None


# =========================================================================
# 7. Least-Privilege & No Admin Exposure Tests
# =========================================================================

@pytest.mark.asyncio
async def test_least_privilege_and_no_admin_exposure(async_client: AsyncClient):
    """
    Verify strict boundary isolation:
    1. Operational staff cannot access store admin endpoints (/admin/roles, /admin/audit-logs).
    2. Registered customer cannot access operational staff endpoints (/staff/dashboard).
    3. Anonymous request is rejected with 401 Unauthorized.
    """
    async with TestingSessionLocal() as session:
        staff_user = await create_user_with_role(session, "general_staff@uwearnova.com", "fulfillment_staff")
        customer_user = await create_user_with_role(session, "regular_client@uwearnova.com", "customer", user_type="customer")

    # 1. Staff accessing admin roles -> 403 Forbidden
    res_admin_roles = await async_client.get("/api/v1/admin/roles", headers=auth_header_for(staff_user))
    assert res_admin_roles.status_code == 403

    # 2. Staff accessing admin audit logs -> 403 Forbidden
    res_admin_audit = await async_client.get("/api/v1/admin/audit-logs", headers=auth_header_for(staff_user))
    assert res_admin_audit.status_code == 403

    # 3. Customer accessing staff dashboard -> 403 Forbidden (STAFF_REQUIRED)
    res_cust_staff = await async_client.get("/api/v1/staff/dashboard", headers=auth_header_for(customer_user))
    assert res_cust_staff.status_code == 403

    # 4. Anonymous accessing staff dashboard -> 401 Unauthorized
    res_anon = await async_client.get("/api/v1/staff/dashboard")
    assert res_anon.status_code == 401
