"""
Fulfillment and Shipment Tracking Tests (Module M15)
Validates parcel shipment records, item allocation and split shipments,
tracking references and courier provider adapters, fulfillment status transitions,
order state synchronization, manual tracking checkpoints, and staff RBAC authorization.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.fulfillment.models import Shipment, ShipmentEvent, ShipmentItem
from app.modules.fulfillment.provider import (
    BaseCourierTrackingProvider,
    ManualCourierProvider,
    MockCourierProvider,
    UnconfiguredCourierProvider,
    get_courier_provider,
)
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.service import get_or_create_default_location
from app.modules.orders.models import Order
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.shipping.service import ensure_default_shipping_configuration


@pytest.fixture
async def seeded_fulfillment_env():
    """Seeds roles, shipping, products, inventory, and users with differentiated roles."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await ensure_default_shipping_configuration(session)
        loc = await get_or_create_default_location(session)

        cat = Category(name="Outerwear", slug="outerwear", is_active=True)
        session.add(cat)
        await session.flush()

        prod1 = Product(
            name="Velvet Blazer",
            slug="velvet-blazer",
            category_id=cat.id,
            price=Decimal("28000.00"),
            status="active",
        )
        prod2 = Product(
            name="Embroidered Kurta",
            slug="embroidered-kurta",
            category_id=cat.id,
            price=Decimal("12000.00"),
            status="active",
        )
        session.add_all([prod1, prod2])
        await session.flush()

        v1 = ProductVariant(
            product_id=prod1.id,
            sku="BLAZER-VLT-38",
            size="38",
            color_name="Emerald Green",
            inventory_count=10,
            in_stock=True,
            is_active=True,
        )
        v2 = ProductVariant(
            product_id=prod2.id,
            sku="KURTA-EMB-M",
            size="M",
            color_name="Ivory White",
            inventory_count=10,
            in_stock=True,
            is_active=True,
        )
        session.add_all([v1, v2])
        await session.flush()

        inv1 = InventoryItem(
            variant_id=v1.id,
            location_id=loc.id,
            quantity_on_hand=10,
            quantity_reserved=0,
        )
        inv2 = InventoryItem(
            variant_id=v2.id,
            location_id=loc.id,
            quantity_on_hand=10,
            quantity_reserved=0,
        )
        session.add_all([inv1, inv2])

        # Users
        alice = User(
            email="alice_fulfillment@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        bob = User(
            email="bob_fulfillment@example.com",
            password_hash=hash_password("Password123!"),
            user_type="customer",
            status="active",
        )
        admin = User(
            email="admin_fulfillment@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        fulfillment_user = User(
            email="staff_fulfillment@example.com",
            password_hash=hash_password("Password123!"),
            user_type="staff",
            status="active",
        )
        session.add_all([alice, bob, admin, fulfillment_user])
        await session.flush()

        # Assign store_admin
        res = await session.execute(select(Role).where(Role.name == "store_admin"))
        store_admin_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=admin.id, role_id=store_admin_role.id))

        # Assign fulfillment_staff
        res = await session.execute(select(Role).where(Role.name == "fulfillment_staff"))
        fulfillment_role = res.scalar_one()
        await session.execute(user_roles.insert().values(user_id=fulfillment_user.id, role_id=fulfillment_role.id))

        await session.commit()
        await session.refresh(alice)
        await session.refresh(bob)
        await session.refresh(admin)
        await session.refresh(fulfillment_user)
        await session.refresh(v1)
        await session.refresh(v2)

        return {
            "alice": alice,
            "bob": bob,
            "admin": admin,
            "fulfillment_user": fulfillment_user,
            "v1": v1,
            "v2": v2,
        }


def make_fulfillment_checkout_payload(
    customer_name: str = "Alice Fulfillment",
    customer_email: str = "alice_fulfillment@example.com",
    customer_phone: str = "03001122334",
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
            "address_line_1": "Flat 4B, Clifton Block 5",
            "city": "Karachi",
            "postal_code": "75600",
            "country_code": "PK",
        },
    }


# ==============================================================================
# 1. Courier Provider Interface Contract Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_courier_provider_factory_and_contracts():
    """Validates that courier factory resolves carrier implementations and adheres to interface."""
    manual = get_courier_provider("manual")
    assert isinstance(manual, ManualCourierProvider)
    assert manual.display_name == "Direct Logistics Partner"
    assert manual.generate_tracking_url("12345") is None

    tcs = get_courier_provider("tcs")
    assert isinstance(tcs, ManualCourierProvider)
    assert tcs.display_name == "TCS Express"
    assert tcs.generate_tracking_url("7788990011") == "https://www.tcsexpress.com/tracking?consignmentNo=7788990011"

    leopards = get_courier_provider("leopards")
    assert leopards.generate_tracking_url("LEO123") == "https://www.leopardscourier.com/tracking?track=LEO123"

    trax = get_courier_provider("trax")
    assert trax.generate_tracking_url("TRX999") == "https://trax.pk/tracking?cn=TRX999"

    mock = get_courier_provider("mock")
    assert isinstance(mock, MockCourierProvider)
    assert "mock-courier.local" in mock.generate_tracking_url("MOCK-CN-1")

    unconfigured = get_courier_provider("unsupported_3pl")
    assert isinstance(unconfigured, UnconfiguredCourierProvider)


# ==============================================================================
# 2. Shipment Creation & Consignment Assignment
# ==============================================================================


@pytest.mark.asyncio
async def test_shipment_creation_and_consignment_booking(async_client: AsyncClient, seeded_fulfillment_env):
    """
    Validates complete shipment creation flow:
    1. Order created with 2 line items.
    2. Fulfillment staff creates shipment parcel assigning carrier 'tcs'.
    3. Consignment tracking URL generated and audit event logged.
    4. Order fulfillment status transitions to 'fulfilled'.
    5. Order status history entry recorded.
    """
    env = seeded_fulfillment_env
    alice = env["alice"]
    staff = env["fulfillment_user"]
    v1 = env["v1"]
    v2 = env["v2"]

    alice_token = create_access_token(alice.id)
    staff_token = create_access_token(staff.id, user_type="staff")

    # Alice adds 2 items and checkouts
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v2.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_fulfillment_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert checkout_res.status_code == 201
    order_data = checkout_res.json()
    order_id = order_data["id"]
    order_num = order_data["order_number"]

    # Staff creates shipment assigning TCS
    create_shp_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={
            "courier_code": "tcs",
            "tracking_number": "TCS-KHI-998822",
            "total_weight_grams": 850,
            "package_count": 1,
            "dispatch_notes": "Handle with care - Luxury garments",
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert create_shp_res.status_code == 201
    shp = create_shp_res.json()

    assert shp["shipment_number"].startswith("SHP-")
    assert shp["order_id"] == order_id
    assert shp["courier_code"] == "tcs"
    assert shp["courier_name"] == "TCS Express"
    assert shp["tracking_number"] == "TCS-KHI-998822"
    assert shp["tracking_url"] == "https://www.tcsexpress.com/tracking?consignmentNo=TCS-KHI-998822"
    assert shp["status"] == "allocated"
    assert shp["destination_city"] == "Karachi"
    assert len(shp["items"]) == 2
    assert len(shp["events"]) == 1
    assert shp["events"][0]["status"] == "allocated"

    # Verify Order status updated
    order_chk = await async_client.get(
        f"/api/v1/admin/orders/{order_num}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert order_chk.status_code == 200
    assert order_chk.json()["fulfillment_status"] == "fulfilled"


# ==============================================================================
# 3. Split & Partial Fulfillment
# ==============================================================================


@pytest.mark.asyncio
async def test_split_and_partial_fulfillment(async_client: AsyncClient, seeded_fulfillment_env):
    """
    Validates partial fulfillment across multiple shipment parcels:
    1. Order has 2 line items.
    2. Staff creates Parcel 1 containing only Item 1 -> Order becomes 'partially_fulfilled'.
    3. Rejects allocating more than remaining quantity.
    4. Staff creates Parcel 2 containing Item 2 -> Order becomes 'fulfilled'.
    """
    env = seeded_fulfillment_env
    alice = env["alice"]
    staff = env["fulfillment_user"]
    v1 = env["v1"]
    v2 = env["v2"]

    alice_token = create_access_token(alice.id)
    staff_token = create_access_token(staff.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 2},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v2.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_fulfillment_checkout_payload(idempotency_key="split_fulfillment_1"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_id = order_data["id"]
    order_num = order_data["order_number"]
    items = order_data["items"]
    item1_id = items[0]["id"]
    item2_id = items[1]["id"]

    # 1. Allocate Parcel 1 with only 1 unit of Item 1
    shp1_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={
            "courier_code": "leopards",
            "items": [{"order_item_id": item1_id, "quantity": 1}],
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert shp1_res.status_code == 201

    # Order should now be partially_fulfilled
    order_chk1 = await async_client.get(
        f"/api/v1/admin/orders/{order_num}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert order_chk1.json()["fulfillment_status"] == "partially_fulfilled"

    # 2. Reject allocating more than remaining unfulfilled quantity
    excess_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={
            "courier_code": "leopards",
            "items": [{"order_item_id": item1_id, "quantity": 5}],  # only 1 remaining
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert excess_res.status_code == 400
    assert "exceeds remaining unfulfilled quantity" in excess_res.json()["error"]["message"]

    # 3. Allocate Parcel 2 with remaining units
    shp2_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={
            "courier_code": "trax",
            "items": [
                {"order_item_id": item1_id, "quantity": 1},
                {"order_item_id": item2_id, "quantity": 1},
            ],
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert shp2_res.status_code == 201

    # Order should now be fulfilled
    order_chk2 = await async_client.get(
        f"/api/v1/admin/orders/{order_num}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert order_chk2.json()["fulfillment_status"] == "fulfilled"

    # List order shipments
    list_res = await async_client.get(
        f"/api/v1/admin/orders/{order_id}/shipments",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2


# ==============================================================================
# 4. Fulfillment Status Progression & State Machine
# ==============================================================================


@pytest.mark.asyncio
async def test_fulfillment_status_progression_and_order_sync(async_client: AsyncClient, seeded_fulfillment_env):
    """
    Validates complete lifecycle state progression:
    allocated -> packing -> packed -> dispatched -> in_transit -> out_for_delivery -> delivered.
    Verifies timestamps, order status synchronization, and terminal transition rejection.
    """
    env = seeded_fulfillment_env
    alice = env["alice"]
    staff = env["fulfillment_user"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    staff_token = create_access_token(staff.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_fulfillment_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_id = checkout_res.json()["id"]
    order_num = checkout_res.json()["order_number"]

    # 1. Create Shipment
    create_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={"courier_code": "tcs", "tracking_number": "TCS-STATUS-001"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    shipment_id = create_res.json()["id"]

    # 2. Advance to 'packing'
    pack_res = await async_client.patch(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "packing", "description": "Order being picked from warehouse racks"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert pack_res.status_code == 200
    assert pack_res.json()["status"] == "packing"

    # 3. Advance to 'packed' -> Order status becomes 'packed'
    packed_res = await async_client.patch(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "packed", "description": "Parcel boxed and poly-bagged"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert packed_res.status_code == 200
    assert packed_res.json()["status"] == "packed"
    assert packed_res.json()["packed_at"] is not None

    chk_order = await async_client.get(f"/api/v1/admin/orders/{order_num}", headers={"Authorization": f"Bearer {staff_token}"})
    assert chk_order.json()["status"] == "packed"

    # 4. Advance to 'dispatched' -> Order status becomes 'shipped'
    dispatch_res = await async_client.patch(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "dispatched", "location": "Karachi Fulfillment Hub", "description": "Handed to TCS courier van"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert dispatch_res.status_code == 200
    assert dispatch_res.json()["status"] == "dispatched"
    assert dispatch_res.json()["dispatched_at"] is not None

    chk_order2 = await async_client.get(f"/api/v1/admin/orders/{order_num}", headers={"Authorization": f"Bearer {staff_token}"})
    assert chk_order2.json()["status"] == "shipped"

    # 5. Advance to 'in_transit'
    transit_res = await async_client.patch(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "in_transit", "location": "National Highway Transit Point", "description": "In transit to destination city"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert transit_res.status_code == 200
    assert transit_res.json()["status"] == "in_transit"

    # 6. Advance to 'out_for_delivery'
    ofd_res = await async_client.patch(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "out_for_delivery", "location": "Clifton Station", "description": "Out for delivery with rider"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert ofd_res.status_code == 200
    assert ofd_res.json()["status"] == "out_for_delivery"

    # 7. Advance to 'delivered' -> Order status becomes 'delivered'
    del_res = await async_client.patch(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "delivered", "location": "Customer Residence", "description": "Delivered and signed by recipient"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "delivered"
    assert del_res.json()["delivered_at"] is not None

    chk_order3 = await async_client.get(f"/api/v1/admin/orders/{order_num}", headers={"Authorization": f"Bearer {staff_token}"})
    assert chk_order3.json()["status"] == "delivered"

    # 8. Terminal transition rejection: Cannot re-open delivered shipment
    term_res = await async_client.patch(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "packing"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert term_res.status_code == 400
    assert "Cannot transition shipment from 'delivered' to 'packing'" in term_res.json()["error"]["message"]


# ==============================================================================
# 5. Manual Tracking Checkpoints & Airway Bill Updates
# ==============================================================================


@pytest.mark.asyncio
async def test_manual_tracking_updates_and_checkpoints(async_client: AsyncClient, seeded_fulfillment_env):
    """Validates updating tracking numbers and logging manual physical checkpoints."""
    env = seeded_fulfillment_env
    alice = env["alice"]
    staff = env["fulfillment_user"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    staff_token = create_access_token(staff.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_fulfillment_checkout_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_id = checkout_res.json()["id"]

    create_res = await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={"courier_code": "manual"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    shipment_id = create_res.json()["id"]

    # 1. Update tracking reference to TCS consignment
    track_upd = await async_client.patch(
        f"/api/v1/admin/shipments/{shipment_id}/tracking",
        json={"tracking_number": "TCS77889900", "courier_code": "tcs"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert track_upd.status_code == 200
    updated_shp = track_upd.json()
    assert updated_shp["tracking_number"] == "TCS77889900"
    assert updated_shp["courier_code"] == "tcs"
    assert updated_shp["tracking_url"] == "https://www.tcsexpress.com/tracking?consignmentNo=TCS77889900"

    # 2. Append an intermediate physical tracking event without advancing status
    event_res = await async_client.post(
        f"/api/v1/admin/shipments/{shipment_id}/events",
        json={
            "status": "allocated",
            "location": "Warehouse Loading Bay 3",
            "description": "Scanned onto transit cage",
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert event_res.status_code == 201
    assert event_res.json()["location"] == "Warehouse Loading Bay 3"


# ==============================================================================
# 6. Customer & Guest Order Tracking Views
# ==============================================================================


@pytest.mark.asyncio
async def test_customer_and_guest_tracking_views(async_client: AsyncClient, seeded_fulfillment_env):
    """
    Validates tracking views:
    1. Authenticated customer can track their own order.
    2. Cross-customer isolation (Bob cannot track Alice's order).
    3. Guest tracking requires verified phone number matching.
    """
    env = seeded_fulfillment_env
    alice = env["alice"]
    bob = env["bob"]
    staff = env["fulfillment_user"]
    v1 = env["v1"]

    alice_token = create_access_token(alice.id)
    bob_token = create_access_token(bob.id)
    staff_token = create_access_token(staff.id, user_type="staff")

    await async_client.post(
        "/api/v1/cart/items",
        json={"variant_id": v1.id, "quantity": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        json=make_fulfillment_checkout_payload(customer_phone="03009988776"),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    order_data = checkout_res.json()
    order_id = order_data["id"]
    order_num = order_data["order_number"]

    # Staff creates shipment
    await async_client.post(
        f"/api/v1/admin/orders/{order_id}/shipments",
        json={"courier_code": "tcs", "tracking_number": "TCS-TRACK-001"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    # 1. Alice tracks her order
    alice_track = await async_client.get(
        f"/api/v1/customer/orders/{order_num}/tracking",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert alice_track.status_code == 200
    timeline = alice_track.json()
    assert timeline["order_number"] == order_num
    assert len(timeline["shipments"]) == 1
    assert timeline["shipments"][0]["tracking_number"] == "TCS-TRACK-001"

    # 2. Bob tries to track Alice's order -> 404
    bob_track = await async_client.get(
        f"/api/v1/customer/orders/{order_num}/tracking",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_track.status_code == 404

    # 3. Guest tracking with valid phone
    guest_track_ok = await async_client.get(
        f"/api/v1/orders/{order_num}/tracking?phone=03009988776",
    )
    assert guest_track_ok.status_code == 200
    assert guest_track_ok.json()["order_number"] == order_num

    # 4. Guest tracking with wrong phone -> 403
    guest_track_fail = await async_client.get(
        f"/api/v1/orders/{order_num}/tracking?phone=03000000000",
    )
    assert guest_track_fail.status_code == 403


# ==============================================================================
# 7. Fulfillment RBAC Access Controls
# ==============================================================================


@pytest.mark.asyncio
async def test_fulfillment_rbac_restrictions(async_client: AsyncClient, seeded_fulfillment_env):
    """Validates that customer cannot manage shipments, while fulfillment staff and admin can."""
    env = seeded_fulfillment_env
    alice = env["alice"]
    staff = env["fulfillment_user"]
    admin = env["admin"]

    alice_token = create_access_token(alice.id)
    staff_token = create_access_token(staff.id, user_type="staff")
    admin_token = create_access_token(admin.id, user_type="staff")

    # Customer tries to access admin shipments work queue -> 403 Forbidden
    res_cust = await async_client.get(
        "/api/v1/admin/shipments",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_cust.status_code == 403

    # Fulfillment staff can access
    res_staff = await async_client.get(
        "/api/v1/admin/shipments",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert res_staff.status_code == 200

    # Store admin can access
    res_admin = await async_client.get(
        "/api/v1/admin/shipments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 200
