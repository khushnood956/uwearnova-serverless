"""
Module M18 — Admin Catalogue & Inventory APIs Test Suite
Verifies administrative catalogue operations:
- Product creation, editing, publishing, archiving, and unarchiving
- Category and collection management with product assignment/removal
- Variant & SKU management with global SKU uniqueness and active variant safety
- Inventory adjustment, real-time sync with variant availability, and low-stock reporting
- Bulk status updates and bulk stock adjustments
- Strict RBAC enforcement and immutable audit trail logging
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Collection, Product, ProductVariant
from app.modules.catalog.seed_data import seed_catalog_products
from app.modules.inventory.models import InventoryItem, InventoryLocation, InventoryMovement
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions


@pytest.fixture
async def setup_catalog_data() -> None:
    """Fixture that initializes system roles and authentic catalogue data."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await seed_catalog_products(session)
        await session.commit()


async def create_user_with_role(
    session: AsyncSession,
    email: str,
    role_name: str,
    user_type: str = "staff",
) -> User:
    """Helper to create a user with a specific role."""
    user = User(
        email=email,
        password_hash=hash_password("SecureAdminPassword123!"),
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
    """Helper to generate JWT bearer header for testing."""
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Product Publishing, Archiving, and Public Catalogue Visibility
# ===========================================================================

@pytest.mark.asyncio
async def test_product_publishing_archiving_lifecycle(async_client: AsyncClient, setup_catalog_data):
    """
    Test draft product creation, publishing (requires variants), archiving,
    and unarchiving with authoritative public storefront reflection.
    """
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "superadmin_m18@uwearnova.com", "store_admin")
        cat = (await session.execute(select(Category))).scalars().first()
        cat_id = cat.id

    headers = auth_header_for(admin)

    # 1. Create a draft product without variants
    create_res = await async_client.post(
        "/api/v1/admin/products",
        headers=headers,
        json={
            "name": "Minimalist Trench Coat",
            "slug": "minimalist-trench-coat",
            "category_id": cat_id,
            "price": 28500.0,
            "status": "draft",
            "variants": [],
        },
    )
    assert create_res.status_code == 201
    prod_data = create_res.json()
    prod_id = prod_data["id"]
    assert prod_data["status"] == "draft"

    # 2. Attempting to publish without variants must fail with 400
    pub_fail_res = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/publish",
        headers=headers,
    )
    assert pub_fail_res.status_code == 400
    assert "active variant" in pub_fail_res.json()["error"]["message"].lower()

    # 3. Add variant to product
    var_res = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/variants",
        headers=headers,
        json={
            "sku": "TC-BEIGE-M",
            "size": "M",
            "color_name": "Beige",
            "color_hex": "#F5F5DC",
            "price": 28500.0,
            "is_active": True,
        },
    )
    assert var_res.status_code == 201
    var_id = var_res.json()["id"]

    # 4. Product should not yet be visible on public storefront
    pub_get = await async_client.get(f"/api/v1/products/{prod_data['slug']}")
    assert pub_get.status_code == 404

    # 5. Publish product successfully
    pub_ok_res = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/publish",
        headers=headers,
    )
    assert pub_ok_res.status_code == 200
    assert pub_ok_res.json()["status"] == "active"
    assert pub_ok_res.json()["published_at"] is not None

    # 6. Now immediately visible on public storefront
    pub_storefront = await async_client.get(f"/api/v1/products/{prod_data['slug']}")
    assert pub_storefront.status_code == 200
    assert pub_storefront.json()["name"] == "Minimalist Trench Coat"

    # 7. Archive the product
    archive_res = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/archive",
        headers=headers,
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "archived"

    # 8. Storefront must return 404 immediately
    pub_after_archive = await async_client.get(f"/api/v1/products/{prod_data['slug']}")
    assert pub_after_archive.status_code == 404

    # 9. Unarchive back to draft
    unarchive_res = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/unarchive",
        headers=headers,
    )
    assert unarchive_res.status_code == 200
    assert unarchive_res.json()["status"] == "draft"

    # 10. Audit log verification
    async with TestingSessionLocal() as session:
        logs = (
            await session.execute(
                select(AuditLog)
                .where(AuditLog.entity_type == "product", AuditLog.entity_id == str(prod_id))
                .order_by(AuditLog.id.asc())
            )
        ).scalars().all()
        actions = [log.action for log in logs]
        assert "product.created" in actions
        assert "product.published" in actions
        assert "product.archived" in actions
        assert "product.unarchived" in actions


# ===========================================================================
# 2. Bulk Product Status Transitions
# ===========================================================================

@pytest.mark.asyncio
async def test_bulk_product_status_operations(async_client: AsyncClient, setup_catalog_data):
    """Test bulk updating status across multiple products with audit logging."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_bulk@uwearnova.com", "store_admin")
        # Fetch first 3 products
        products = (await session.execute(select(Product).limit(3))).scalars().all()
        prod_ids = [p.id for p in products]

    headers = auth_header_for(admin)

    # Bulk archive 3 products
    bulk_res = await async_client.post(
        "/api/v1/admin/products/bulk-status",
        headers=headers,
        json={"product_ids": prod_ids, "status": "archived"},
    )
    assert bulk_res.status_code == 200
    data = bulk_res.json()
    assert data["updated_count"] == 3
    assert data["status"] == "archived"

    # Verify they are archived in DB
    async with TestingSessionLocal() as session:
        for pid in prod_ids:
            p = await session.get(Product, pid)
            assert p.status == "archived"


# ===========================================================================
# 3. Variant and SKU Management
# ===========================================================================

@pytest.mark.asyncio
async def test_variant_update_and_deletion_safety(async_client: AsyncClient, setup_catalog_data):
    """
    Test updating variant SKU/pricing, enforcing global SKU uniqueness,
    and preventing deletion of the sole active variant of a live product.
    """
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_variants@uwearnova.com", "store_admin")
        # Get an active product with variants
        stmt = (
            select(Product)
            .where(Product.status == "active")
            .limit(1)
        )
        product = (await session.execute(stmt)).scalars().first()
        prod_id = product.id
        variant_stmt = select(ProductVariant).where(ProductVariant.product_id == prod_id)
        variants = (await session.execute(variant_stmt)).scalars().all()
        v1_id = variants[0].id
        v2_sku = "GLOBAL-DUPLICATE-SKU"

        # Create another variant on a different product to test SKU collision
        other_prod = (
            await session.execute(
                select(Product).where(Product.id != prod_id, Product.status == "active").limit(1)
            )
        ).scalars().first()
        other_var = ProductVariant(
            product_id=other_prod.id,
            sku=v2_sku,
            size="L",
            color_name="Black",
            price=Decimal("15000.00"),
            is_active=True,
        )
        session.add(other_var)
        await session.commit()

    headers = auth_header_for(admin)

    # 1. Update variant details (price, color, size)
    update_res = await async_client.put(
        f"/api/v1/admin/products/{prod_id}/variants/{v1_id}",
        headers=headers,
        json={
            "sku": "NEW-UNIQUE-SKU-123",
            "price": 31999.0,
            "size": "XL",
            "color_name": "Charcoal Grey",
        },
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["sku"] == "NEW-UNIQUE-SKU-123"
    assert Decimal(str(updated_data["price"])) == Decimal("31999.00")
    assert updated_data["size"] == "XL"

    # 2. Update to conflicting SKU must raise 409 Conflict
    conflict_res = await async_client.put(
        f"/api/v1/admin/products/{prod_id}/variants/{v1_id}",
        headers=headers,
        json={"sku": v2_sku},
    )
    assert conflict_res.status_code == 409
    assert "already exists" in conflict_res.json()["error"]["message"].lower()

    # 3. Prevent deleting sole active variant of an active product
    # Set all other variants of this product to inactive
    async with TestingSessionLocal() as session:
        all_vars = (
            await session.execute(
                select(ProductVariant).where(
                    ProductVariant.product_id == prod_id,
                    ProductVariant.id != v1_id,
                )
            )
        ).scalars().all()
        for v in all_vars:
            v.is_active = False
        await session.commit()

    # Attempt to delete v1 (the sole active variant)
    del_res = await async_client.delete(
        f"/api/v1/admin/products/{prod_id}/variants/{v1_id}",
        headers=headers,
    )
    assert del_res.status_code == 400
    assert "sole active variant" in del_res.json()["error"]["message"].lower()


# ===========================================================================
# 4. Collection Product Assignment & Removal
# ===========================================================================

@pytest.mark.asyncio
async def test_collection_product_assignment(async_client: AsyncClient, setup_catalog_data):
    """Test assigning products to a collection and removing them with audit trail."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_col@uwearnova.com", "store_admin")
        col = (await session.execute(select(Collection))).scalars().first()
        prods = (await session.execute(select(Product).limit(2))).scalars().all()
        col_id = col.id
        p1_id = prods[0].id
        p2_id = prods[1].id

    headers = auth_header_for(admin)

    # 1. Assign products to collection
    assign_res = await async_client.post(
        f"/api/v1/admin/collections/{col_id}/products",
        headers=headers,
        json={"product_ids": [p1_id, p2_id]},
    )
    assert assign_res.status_code == 200

    # 2. Remove one product from collection
    remove_res = await async_client.delete(
        f"/api/v1/admin/collections/{col_id}/products/{p1_id}",
        headers=headers,
    )
    assert remove_res.status_code == 200

    # Verify audit log
    async with TestingSessionLocal() as session:
        logs = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "collection",
                    AuditLog.entity_id == str(col_id),
                )
            )
        ).scalars().all()
        actions = [log.action for log in logs]
        assert "collection.products_assigned" in actions
        assert "collection.product_removed" in actions


# ===========================================================================
# 5. Low-Stock Visibility & Deficit Report
# ===========================================================================

@pytest.mark.asyncio
async def test_low_stock_deficit_report(async_client: AsyncClient, setup_catalog_data):
    """Test low stock report returning actionable deficits against reorder thresholds."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_inventory@uwearnova.com", "store_admin")
        var = (await session.execute(select(ProductVariant).limit(1))).scalars().first()
        var_id = var.id

    headers = auth_header_for(admin)

    # Adjust stock to 3 units (threshold defaults to 5, so deficit is 2)
    adjust_res = await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=headers,
        json={"variant_id": var_id, "quantity_delta": 3, "reason": "receipt"},
    )
    assert adjust_res.status_code == 200

    # Request the low-stock actionable deficit report
    report_res = await async_client.get(
        "/api/v1/admin/inventory/low-stock-report",
        headers=headers,
    )
    assert report_res.status_code == 200
    report = report_res.json()
    assert "total_low_stock_items" in report
    assert "items" in report
    assert report["total_low_stock_items"] >= 1

    # Verify deficit calculation
    target_item = next((i for i in report["items"] if i["variant_id"] == var_id), None)
    assert target_item is not None
    assert target_item["quantity_available"] == 3
    assert target_item["reorder_threshold"] == 5
    assert target_item["deficit"] == 2


# ===========================================================================
# 6. Bulk Inventory Adjustment
# ===========================================================================

@pytest.mark.asyncio
async def test_bulk_inventory_adjustment(async_client: AsyncClient, setup_catalog_data):
    """Test bulk stock adjustment across multiple SKUs and sync with variant counters."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "admin_bulk_inv@uwearnova.com", "store_admin")
        variants = (await session.execute(select(ProductVariant).limit(2))).scalars().all()
        v1_id = variants[0].id
        v2_id = variants[1].id

    headers = auth_header_for(admin)

    # Bulk intake stock
    bulk_res = await async_client.post(
        "/api/v1/admin/inventory/bulk-adjust",
        headers=headers,
        json={
            "adjustments": [
                {"variant_id": v1_id, "quantity_delta": 25, "reason": "receipt", "notes": "Q4 Shipment Received"},
                {"variant_id": v2_id, "quantity_delta": 40, "reason": "receipt", "notes": "Q4 Shipment Received"},
            ],
        },
    )
    assert bulk_res.status_code == 200
    data = bulk_res.json()
    assert data["adjusted_count"] == 2
    assert data["total_delta"] == 65

    # Verify ProductVariant.inventory_count and in_stock updated
    async with TestingSessionLocal() as session:
        v1 = await session.get(ProductVariant, v1_id)
        v2 = await session.get(ProductVariant, v2_id)
        assert v1.inventory_count == 25
        assert v1.in_stock is True
        assert v2.inventory_count == 40
        assert v2.in_stock is True


# ===========================================================================
# 7. Customer & Non-Staff Authorization Security
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_catalog_security_isolation(async_client: AsyncClient, setup_catalog_data):
    """Non-staff customer accounts cannot access administrative catalogue or inventory APIs."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        customer = User(
            email="regular_customer_m18@example.com",
            password_hash=hash_password("Pass123!"),
            status="active",
            user_type="customer",
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

    cust_headers = auth_header_for(customer)

    # 1. Product creation forbidden for customer
    res1 = await async_client.post(
        "/api/v1/admin/products",
        headers=cust_headers,
        json={"title": "Unauthorized Coat", "base_price": 5000},
    )
    assert res1.status_code == 403

    # 2. Inventory adjustment forbidden for customer
    res2 = await async_client.post(
        "/api/v1/admin/inventory/adjust",
        headers=cust_headers,
        json={"variant_id": 1, "quantity_delta": 10, "reason": "hack"},
    )
    assert res2.status_code == 403

    # 3. Unauthenticated request rejected with 401
    res3 = await async_client.get("/api/v1/admin/inventory/low-stock-report")
    assert res3.status_code == 401
