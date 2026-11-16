"""
Product Catalogue Tests (Module M07)
Verifies public storefront browsing, faceted filtering, pagination, sorting,
admin CRUD, SKU uniqueness, decimal precision, and authentic product seeding.
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
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions


@pytest.fixture
async def seeded_catalog() -> None:
    """Fixture that sets up RBAC permissions and seeds the full authentic UniNova catalogue."""
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
    """Helper to create a user and assign a role."""
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


# ===========================================================================
# 1. Authentic Product Seeding Verification
# ===========================================================================

@pytest.mark.asyncio
async def test_seed_products_from_source(seeded_catalog):
    """Verify that all 10 authentic products from src/data/products.ts are accurately seeded."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        products = (await session.execute(select(Product))).scalars().all()
        assert len(products) == 10

        # Verify Monolith Blazer
        blazer_res = await session.execute(
            select(Product).where(Product.slug == "monolith-oversized-wool-blazer")
        )
        blazer = blazer_res.scalar_one()
        assert blazer.name == "Monolith Oversized Blazer"
        assert blazer.price == Decimal("24500.00")
        assert blazer.original_price == Decimal("28000.00")
        assert blazer.is_new_arrival is True
        assert blazer.is_trending is True
        assert len(blazer.variants) == 4
        assert len(blazer.images) == 2

        # Verify exact SKU mapping
        skus = {v.sku for v in blazer.variants}
        assert "BLZ-BLK-38" in skus
        assert "BLZ-SND-40" in skus


# ===========================================================================
# 2. Public Storefront Browsing, Filtering, Sorting & Pagination
# ===========================================================================

@pytest.mark.asyncio
async def test_public_products_faceted_filtering(async_client: AsyncClient, seeded_catalog):
    """Test filtering by category, collection, price range, attributes, and search keywords."""
    # 1. Total products (all 10 active)
    resp = await async_client.get("/api/v1/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert len(data["items"]) == 10

    # 2. Filter by category_slug=men (3 men's items: blazer, shirt, trousers)
    resp_men = await async_client.get("/api/v1/products?category_slug=men")
    assert resp_men.status_code == 200
    men_data = resp_men.json()
    assert men_data["total"] == 3
    assert all(p["category"]["slug"] in ["men", "men-jackets", "men-t-shirts", "men-jeans-pants"] for p in men_data["items"])

    # 3. Filter by collection_slug=trending (7 trending items)
    resp_trending = await async_client.get("/api/v1/products?collection_slug=trending")
    assert resp_trending.status_code == 200
    assert resp_trending.json()["total"] == 7

    # 4. Filter by price bounds (PKR 10,000 to 20,000)
    resp_price = await async_client.get("/api/v1/products?min_price=10000&max_price=20000")
    assert resp_price.status_code == 200
    for p in resp_price.json()["items"]:
        price = Decimal(str(p["price"]))
        assert Decimal("10000.00") <= price <= Decimal("20000.00")

    # 5. Faceted size and color filter
    resp_variant = await async_client.get("/api/v1/products?sizes=38R&colors=Obsidian+Black")
    assert resp_variant.status_code == 200
    var_data = resp_variant.json()
    assert var_data["total"] == 1
    assert var_data["items"][0]["slug"] == "monolith-oversized-wool-blazer"

    # 6. Search keyword
    resp_search = await async_client.get("/api/v1/products?search=Egyptian")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["slug"] == "relaxed-egyptian-cotton-kurta-shirt"

    # 7. Sorting: price_asc and price_desc
    resp_asc = await async_client.get("/api/v1/products?sort_by=price_asc")
    assert resp_asc.status_code == 200
    prices_asc = [Decimal(str(p["price"])) for p in resp_asc.json()["items"]]
    assert prices_asc == sorted(prices_asc)

    resp_desc = await async_client.get("/api/v1/products?sort_by=price_desc")
    assert resp_desc.status_code == 200
    prices_desc = [Decimal(str(p["price"])) for p in resp_desc.json()["items"]]
    assert prices_desc == sorted(prices_desc, reverse=True)

    # 8. Pagination (limit 4, offset 0, then offset 4)
    page1 = await async_client.get("/api/v1/products?limit=4&offset=0")
    assert page1.status_code == 200
    p1_data = page1.json()
    assert len(p1_data["items"]) == 4
    assert p1_data["total"] == 10

    page2 = await async_client.get("/api/v1/products?limit=4&offset=4")
    assert page2.status_code == 200
    p2_data = page2.json()
    assert len(p2_data["items"]) == 4
    # Ensure no overlap between page 1 and page 2
    p1_ids = {p["id"] for p in p1_data["items"]}
    p2_ids = {p["id"] for p in p2_data["items"]}
    assert p1_ids.isdisjoint(p2_ids)


@pytest.mark.asyncio
async def test_public_product_detail(async_client: AsyncClient, seeded_catalog):
    """Retrieve full product detail with variants, swatches, images, and fabric care."""
    resp = await async_client.get("/api/v1/products/sculptural-wrap-midi-dress")
    assert resp.status_code == 200
    product = resp.json()
    assert product["name"] == "Sculptural Wrap Midi Dress"
    assert product["price"] == "21900.00"
    assert product["original_price"] == "25500.00"
    assert len(product["variants"]) == 4
    assert len(product["images"]) == 2
    assert isinstance(product["fabric_care"], list)
    assert len(product["fabric_care"]) == 3
    assert product["category"]["slug"] in ["women", "women-jackets"]

    # Non-existent slug returns 404
    missing_resp = await async_client.get("/api/v1/products/non-existent-product")
    assert missing_resp.status_code == 404
    assert missing_resp.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


# ===========================================================================
# 3. Protected Administrative Product CRUD & Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_product_access_control(async_client: AsyncClient, seeded_catalog):
    """Endpoints enforce granular RBAC permissions."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "prod_boss@uwearnova.com", "store_admin", "admin")
        customer = User(
            email="regular_shopper@uwearnova.com",
            password_hash=hash_password("Pass123!"),
            status="active",
            user_type="customer",
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

    # 1. Unauthenticated -> 401
    resp = await async_client.get("/api/v1/admin/products")
    assert resp.status_code == 401

    # 2. Customer -> 403
    cust_headers = auth_header_for(customer)
    resp = await async_client.get("/api/v1/admin/products", headers=cust_headers)
    assert resp.status_code == 403

    # 3. Admin -> 200
    admin_headers = auth_header_for(admin)
    resp = await async_client.get("/api/v1/admin/products", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 10


@pytest.mark.asyncio
async def test_admin_product_create_and_validation(async_client: AsyncClient, seeded_catalog):
    """Admin can create new product with unique slug, SKU uniqueness, and Decimal pricing."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "creator@uwearnova.com", "store_admin", "admin")
        cat_res = await session.execute(select(Category).where(Category.slug == "men"))
        category = cat_res.scalar_one()

    admin_headers = auth_header_for(admin)

    product_payload = {
        "name": "Cashmere Double-Breasted Coat",
        "slug": "cashmere-double-breasted-coat",
        "subtitle": "100% Inner Mongolian Cashmere",
        "description": "Exquisitely tailored double-breasted overcoat.",
        "category_id": category.id,
        "brand_label": "UniNova Atelier",
        "status": "active",
        "price": "45000.00",
        "original_price": "52000.00",
        "is_new_arrival": True,
        "is_trending": True,
        "is_featured": True,
        "fabric_care": ["100% Pure Cashmere", "Specialist dry clean only"],
        "delivery_notes": "Complimentary insured delivery.",
        "images": [
            {"image_url": "https://example.com/coat1.jpg", "alt_text": "Front view", "sort_order": 0, "is_primary": True},
        ],
        "variants": [
            {"sku": "COT-BLK-40", "size": "40R", "color_name": "Obsidian Black", "color_hex": "#111111", "inventory_count": 4, "in_stock": True},
            {"sku": "COT-BLK-42", "size": "42R", "color_name": "Obsidian Black", "color_hex": "#111111", "inventory_count": 3, "in_stock": True},
        ],
    }

    # 1. Success creation
    resp = await async_client.post("/api/v1/admin/products", json=product_payload, headers=admin_headers)
    assert resp.status_code == 201
    created = resp.json()
    prod_id = created["id"]
    assert created["slug"] == "cashmere-double-breasted-coat"
    assert created["price"] == "45000.00"
    assert len(created["variants"]) == 2

    # 2. Duplicate slug returns 409
    dup_slug_payload = {**product_payload, "name": "Different Name"}
    resp_dup_slug = await async_client.post("/api/v1/admin/products", json=dup_slug_payload, headers=admin_headers)
    assert resp_dup_slug.status_code == 409
    assert resp_dup_slug.json()["error"]["code"] == "PRODUCT_SLUG_EXISTS"

    # 3. Duplicate variant SKU returns 409
    dup_sku_payload = {
        **product_payload,
        "slug": "brand-new-coat-slug",
        "variants": [
            {"sku": "COT-BLK-40", "size": "44R", "color_name": "Black", "inventory_count": 2, "in_stock": True},
        ],
    }
    resp_dup_sku = await async_client.post("/api/v1/admin/products", json=dup_sku_payload, headers=admin_headers)
    assert resp_dup_sku.status_code == 409
    assert resp_dup_sku.json()["error"]["code"] == "VARIANT_SKU_EXISTS"

    # 4. Add variant endpoint
    new_variant_payload = {
        "sku": "COT-CAM-40",
        "size": "40R",
        "color_name": "Classic Camel",
        "color_hex": "#C5AA82",
        "inventory_count": 5,
        "in_stock": True,
    }
    var_resp = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/variants",
        json=new_variant_payload,
        headers=admin_headers,
    )
    assert var_resp.status_code == 201
    assert var_resp.json()["sku"] == "COT-CAM-40"

    # 5. Update product
    update_payload = {"price": "42000.00", "subtitle": "Updated Subtitle"}
    up_resp = await async_client.put(f"/api/v1/admin/products/{prod_id}", json=update_payload, headers=admin_headers)
    assert up_resp.status_code == 200
    assert up_resp.json()["price"] == "42000.00"
    assert up_resp.json()["subtitle"] == "Updated Subtitle"

    # 6. Delete product
    del_resp = await async_client.delete(f"/api/v1/admin/products/{prod_id}", headers=admin_headers)
    assert del_resp.status_code == 200

    # 7. Verify audit logs
    async with TestingSessionLocal() as session:
        audit_logs = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "product",
                    AuditLog.entity_id == str(prod_id),
                )
            )
        ).scalars().all()
        actions = [log.action for log in audit_logs]
        assert "product.created" in actions
        assert "product.updated" in actions
        assert "product.deleted" in actions
