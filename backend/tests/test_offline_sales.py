"""
Unit and Integration Tests for Offline Sales / POS Module
Verifies in-store sale recordings, stock decrements, validation, metrics, and void reversals.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.modules.auth.models import User
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.inventory.models import InventoryLocation, InventoryMovement
from app.modules.offline_sales.models import OfflineSale
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions


async def create_user_with_role(session, email: str, role_name: str, user_type: str = "admin") -> User:
    user = User(
        email=email,
        password_hash=hash_password("SecureAdmin123!"),
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
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seeded_pos_env() -> None:
    """Fixture that seeds roles, inventory location, and a sample product with stock."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)

        # Ensure default location
        loc = InventoryLocation(
            name="Lahore Flagship Store",
            code="LHR-STORE-01",
            country_code="PK",
            is_active=True,
        )
        session.add(loc)
        await session.flush()

        # Create category
        cat = Category(name="Men", slug="men", is_active=True)
        session.add(cat)
        await session.flush()

        # Create product with 2 variants
        prod = Product(
            name="Architectural Wool Blazer",
            slug="architectural-wool-blazer",
            category_id=cat.id,
            price=Decimal("28500.00"),
            brand_label="UWEARNOVA",
            status="active",
        )
        session.add(prod)
        await session.flush()

        v1 = ProductVariant(
            product_id=prod.id,
            sku="UWN-BLAZER-BLK-40R",
            size="40R",
            color_name="Obsidian Black",
            price=Decimal("28500.00"),
            inventory_count=10,
            in_stock=True,
        )
        v2 = ProductVariant(
            product_id=prod.id,
            sku="UWN-BLAZER-BLK-42R",
            size="42R",
            color_name="Obsidian Black",
            price=Decimal("28500.00"),
            inventory_count=2,
            in_stock=True,
        )
        session.add_all([v1, v2])
        await session.commit()


@pytest.mark.asyncio
async def test_record_offline_sale_and_inventory_decrement(async_client: AsyncClient, seeded_pos_env):
    """Verify offline walk-in sale creates receipt, deducts variant inventory, and creates movements."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "pos_admin@uwearnova.com", "store_admin", "admin")
        v1 = (await session.execute(select(ProductVariant).where(ProductVariant.sku == "UWN-BLAZER-BLK-40R"))).scalar_one()
        v1_id = v1.id

    admin_headers = auth_header_for(admin)

    # 1. Ring up offline sale: 3 units of v1 (initial count: 10)
    payload = {
        "customer_name": "Hamza Tariq",
        "customer_phone": "03001234567",
        "customer_email": "hamza@example.pk",
        "payment_method": "cash",
        "discount_amount": "500.00",
        "tax_amount": "0.00",
        "notes": "Walk-in cash sale at register 1",
        "items": [
            {
                "variant_id": v1_id,
                "quantity": 3,
            }
        ],
    }

    resp = await async_client.post("/api/v1/admin/offline-sales", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["receipt_number"].startswith("POS-")
    assert data["customer_name"] == "Hamza Tariq"
    assert data["payment_method"] == "cash"
    assert data["status"] == "completed"
    # Subtotal = 3 * 28500 = 85500. Total = 85500 - 500 = 85000.
    assert Decimal(data["subtotal"]) == Decimal("85500.00")
    assert Decimal(data["total_amount"]) == Decimal("85000.00")
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3
    assert data["items"][0]["sku"] == "UWN-BLAZER-BLK-40R"

    # 2. Verify variant stock count decreased from 10 to 7
    async with TestingSessionLocal() as session:
        v1_updated = await session.get(ProductVariant, v1_id)
        assert v1_updated.inventory_count == 7
        assert v1_updated.in_stock is True

        # Check inventory movement record
        mov = (
            await session.execute(
                select(InventoryMovement).where(InventoryMovement.variant_id == v1_id)
            )
        ).scalar_one_or_none()
        assert mov is not None
        assert mov.movement_type == "offline_sale"
        assert mov.quantity_delta == -3
        assert mov.reference_id == data["receipt_number"]


@pytest.mark.asyncio
async def test_record_offline_sale_insufficient_stock_rejection(async_client: AsyncClient, seeded_pos_env):
    """Verify attempting to sell more units than in stock triggers 400 INSUFFICIENT_STOCK."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "pos_admin2@uwearnova.com", "store_admin", "admin")
        v2 = (await session.execute(select(ProductVariant).where(ProductVariant.sku == "UWN-BLAZER-BLK-42R"))).scalar_one()
        v2_id = v2.id

    admin_headers = auth_header_for(admin)

    # v2 has only 2 units in stock; try to sell 5 units
    payload = {
        "payment_method": "pos_card",
        "items": [
            {
                "variant_id": v2_id,
                "quantity": 5,
            }
        ],
    }

    resp = await async_client.post("/api/v1/admin/offline-sales", json=payload, headers=admin_headers)
    assert resp.status_code == 400
    err = resp.json()
    assert err["error"]["code"] == "INSUFFICIENT_STOCK"


@pytest.mark.asyncio
async def test_list_offline_sales_and_summary_metrics(async_client: AsyncClient, seeded_pos_env):
    """Verify listing sales and aggregate metrics calculation."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "pos_admin3@uwearnova.com", "store_admin", "admin")
        v1 = (await session.execute(select(ProductVariant).where(ProductVariant.sku == "UWN-BLAZER-BLK-40R"))).scalar_one()
        v1_id = v1.id

    admin_headers = auth_header_for(admin)

    # Create 1 cash sale
    await async_client.post(
        "/api/v1/admin/offline-sales",
        json={
            "customer_name": "Ayesha Khan",
            "payment_method": "cash",
            "items": [{"variant_id": v1_id, "quantity": 1}],
        },
        headers=admin_headers,
    )

    # Create 1 card sale
    await async_client.post(
        "/api/v1/admin/offline-sales",
        json={
            "customer_name": "Bilal Ahmed",
            "payment_method": "pos_card",
            "items": [{"variant_id": v1_id, "quantity": 2}],
        },
        headers=admin_headers,
    )

    # Fetch list
    resp = await async_client.get("/api/v1/admin/offline-sales", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["summary"]["total_sales_count"] == 2
    assert data["summary"]["total_units_sold"] == 3
    assert Decimal(data["summary"]["total_revenue"]) == Decimal("85500.00")
    assert Decimal(data["summary"]["cash_revenue"]) == Decimal("28500.00")
    assert Decimal(data["summary"]["card_revenue"]) == Decimal("57000.00")


@pytest.mark.asyncio
async def test_void_offline_sale_restores_stock(async_client: AsyncClient, seeded_pos_env):
    """Verify voiding a sale restores stock counts and logs void movement."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "pos_admin4@uwearnova.com", "store_admin", "admin")
        v1 = (await session.execute(select(ProductVariant).where(ProductVariant.sku == "UWN-BLAZER-BLK-40R"))).scalar_one()
        v1_id = v1.id

    admin_headers = auth_header_for(admin)

    # Create sale: 4 units (leaves 6)
    sale_resp = await async_client.post(
        "/api/v1/admin/offline-sales",
        json={
            "customer_name": "Return Customer",
            "payment_method": "cash",
            "items": [{"variant_id": v1_id, "quantity": 4}],
        },
        headers=admin_headers,
    )
    sale_id = sale_resp.json()["id"]

    async with TestingSessionLocal() as session:
        v1_after_sale = await session.get(ProductVariant, v1_id)
        assert v1_after_sale.inventory_count == 6

    # Void the sale
    void_resp = await async_client.post(f"/api/v1/admin/offline-sales/{sale_id}/void", headers=admin_headers)
    assert void_resp.status_code == 200
    assert void_resp.json()["status"] == "voided"

    # Verify stock restored back to 10
    async with TestingSessionLocal() as session:
        v1_restored = await session.get(ProductVariant, v1_id)
        assert v1_restored.inventory_count == 10
        assert v1_restored.in_stock is True

    # Voiding again should be rejected with 400
    void_again_resp = await async_client.post(f"/api/v1/admin/offline-sales/{sale_id}/void", headers=admin_headers)
    assert void_again_resp.status_code == 400
