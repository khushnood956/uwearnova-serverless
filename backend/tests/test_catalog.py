"""
Catalog Domain Tests (Module M06 — Categories & Collections)
Tests public storefront browsing, hierarchy tree building, administrative CRUD,
duplicate name/slug collision handling, cycle prevention, safe deletion, and audit logging.
"""

import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Collection
from app.modules.rbac.models import Permission, Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions


@pytest.fixture
async def seeded_catalog_rbac() -> None:
    """Fixture that seeds roles and permissions."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
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


# ===========================================================================
# Public Categories Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_public_categories_listing_and_tree(async_client: AsyncClient):
    """Storefront can list active categories, filter by root/parent, and view taxonomy tree."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        # Create hierarchy: Women (root) -> Ready-to-Wear (child) -> Inactive Category
        root_women = Category(name="Women", slug="women", sort_order=1, is_active=True)
        root_men = Category(name="Men", slug="men", sort_order=2, is_active=True)
        session.add_all([root_women, root_men])
        await session.flush()

        child_rtw = Category(name="Ready-to-Wear", slug="ready-to-wear", parent_id=root_women.id, sort_order=1, is_active=True)
        inactive_cat = Category(name="Archived Seasonal", slug="archived-seasonal", parent_id=root_women.id, sort_order=2, is_active=False)
        session.add_all([child_rtw, inactive_cat])
        await session.commit()

    # 1. Public list excludes inactive category
    resp = await async_client.get("/api/v1/categories")
    assert resp.status_code == 200
    data = resp.json()
    slugs = [c["slug"] for c in data]
    assert "women" in slugs
    assert "men" in slugs
    assert "ready-to-wear" in slugs
    assert "archived-seasonal" not in slugs

    # 2. Filter roots only
    roots_resp = await async_client.get("/api/v1/categories?roots_only=true")
    assert roots_resp.status_code == 200
    roots_data = roots_resp.json()
    assert len(roots_data) == 2
    assert {c["slug"] for c in roots_data} == {"women", "men"}

    # 3. Filter by parent_id
    parent_resp = await async_client.get(f"/api/v1/categories?parent_id={root_women.id}")
    assert parent_resp.status_code == 200
    parent_data = parent_resp.json()
    assert len(parent_data) == 1
    assert parent_data[0]["slug"] == "ready-to-wear"

    # 4. Hierarchical tree endpoint
    tree_resp = await async_client.get("/api/v1/categories/tree")
    assert tree_resp.status_code == 200
    tree_data = tree_resp.json()
    assert len(tree_data) == 2  # Women and Men at top
    women_node = next(c for c in tree_data if c["slug"] == "women")
    assert len(women_node["children"]) == 1
    assert women_node["children"][0]["slug"] == "ready-to-wear"

    # 5. Retrieve single category by slug and ID
    single_slug_resp = await async_client.get("/api/v1/categories/women")
    assert single_slug_resp.status_code == 200
    assert single_slug_resp.json()["name"] == "Women"

    single_id_resp = await async_client.get(f"/api/v1/categories/{root_women.id}")
    assert single_id_resp.status_code == 200
    assert single_id_resp.json()["slug"] == "women"

    # Inactive category not found publicly
    inactive_resp = await async_client.get("/api/v1/categories/archived-seasonal")
    assert inactive_resp.status_code == 404


# ===========================================================================
# Public Collections Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_public_collections_listing(async_client: AsyncClient):
    """Storefront can list active curated collections; inactive collections are hidden."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        col1 = Collection(name="New Arrivals", slug="new-arrivals", sort_order=1, is_active=True)
        col2 = Collection(name="Signature Collection", slug="signature", sort_order=2, is_active=True)
        col3 = Collection(name="Hidden Draft", slug="hidden-draft", sort_order=3, is_active=False)
        session.add_all([col1, col2, col3])
        await session.commit()

    resp = await async_client.get("/api/v1/collections")
    assert resp.status_code == 200
    data = resp.json()
    slugs = [c["slug"] for c in data]
    assert "new-arrivals" in slugs
    assert "signature" in slugs
    assert "hidden-draft" not in slugs

    single_resp = await async_client.get("/api/v1/collections/new-arrivals")
    assert single_resp.status_code == 200
    assert single_resp.json()["name"] == "New Arrivals"

    # Inactive returns 404 on storefront
    hidden_resp = await async_client.get("/api/v1/collections/hidden-draft")
    assert hidden_resp.status_code == 404


# ===========================================================================
# Admin Categories CRUD & Access Control
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_category_access_control(async_client: AsyncClient, seeded_catalog_rbac):
    """Admin endpoints enforce authentication and granular category permissions."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "cat_admin@uwearnova.com", "store_admin", "admin")
        customer = User(
            email="cust_cat@uwearnova.com",
            password_hash=hash_password("Pass123!"),
            status="active",
            user_type="customer",
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

    # 1. Unauthenticated -> 401
    resp = await async_client.get("/api/v1/admin/categories")
    assert resp.status_code == 401

    # 2. Customer -> 403
    cust_headers = auth_header_for(customer)
    resp = await async_client.get("/api/v1/admin/categories", headers=cust_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # 3. Store Admin -> 200
    admin_headers = auth_header_for(admin)
    resp = await async_client.get("/api/v1/admin/categories", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_category_lifecycle_and_validation(async_client: AsyncClient, seeded_catalog_rbac):
    """Admin can create, update, and delete categories with uniqueness and cycle validation."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "supercat@uwearnova.com", "store_admin", "admin")

    admin_headers = auth_header_for(admin)

    # 1. Create root category
    create_payload = {
        "name": "Footwear",
        "slug": "footwear",
        "description": "Handcrafted calfskin and minimalist footwear.",
        "image_url": "https://example.com/shoes.jpg",
        "sort_order": 3,
        "is_active": True,
    }
    resp = await async_client.post("/api/v1/admin/categories", json=create_payload, headers=admin_headers)
    assert resp.status_code == 201
    footwear = resp.json()
    footwear_id = footwear["id"]
    assert footwear["slug"] == "footwear"

    # 2. Duplicate name error
    dup_name_payload = {**create_payload, "slug": "footwear-distinct"}
    resp = await async_client.post("/api/v1/admin/categories", json=dup_name_payload, headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CATEGORY_NAME_EXISTS"

    # 3. Duplicate slug error
    dup_slug_payload = {**create_payload, "name": "Footwear Distinct"}
    resp = await async_client.post("/api/v1/admin/categories", json=dup_slug_payload, headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CATEGORY_SLUG_EXISTS"

    # 4. Invalid slug format (uppercase, spaces)
    invalid_slug_payload = {**create_payload, "name": "New Cat", "slug": "Invalid Slug!"}
    resp = await async_client.post("/api/v1/admin/categories", json=invalid_slug_payload, headers=admin_headers)
    assert resp.status_code == 422

    # 5. Create child category
    child_payload = {
        "name": "Loafers",
        "slug": "loafers",
        "parent_id": footwear_id,
        "sort_order": 1,
        "is_active": True,
    }
    child_resp = await async_client.post("/api/v1/admin/categories", json=child_payload, headers=admin_headers)
    assert child_resp.status_code == 201
    loafers = child_resp.json()
    loafers_id = loafers["id"]
    assert loafers["parent_id"] == footwear_id

    # 6. Cycle prevention: Setting Footwear's parent to its child Loafers
    cycle_payload = {"parent_id": loafers_id}
    resp = await async_client.put(f"/api/v1/admin/categories/{footwear_id}", json=cycle_payload, headers=admin_headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "CYCLICAL_CATEGORY_HIERARCHY"

    # 7. Self-parenting prevention
    self_parent_payload = {"parent_id": footwear_id}
    resp = await async_client.put(f"/api/v1/admin/categories/{footwear_id}", json=self_parent_payload, headers=admin_headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_PARENT_CATEGORY"

    # 8. Safe deletion check: Cannot delete category that has subcategories
    resp = await async_client.delete(f"/api/v1/admin/categories/{footwear_id}", headers=admin_headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "CATEGORY_HAS_CHILDREN"

    # 9. Delete leaf child category succeeds
    del_child_resp = await async_client.delete(f"/api/v1/admin/categories/{loafers_id}", headers=admin_headers)
    assert del_child_resp.status_code == 200

    # 10. Delete parent now succeeds
    del_parent_resp = await async_client.delete(f"/api/v1/admin/categories/{footwear_id}", headers=admin_headers)
    assert del_parent_resp.status_code == 200

    # 11. Verify audit logs were written
    async with TestingSessionLocal() as session:
        logs = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "category",
                    AuditLog.action.in_(["category.created", "category.deleted"]),
                )
            )
        ).scalars().all()
        actions = [log.action for log in logs]
        assert "category.created" in actions
        assert "category.deleted" in actions


# ===========================================================================
# Admin Collections CRUD Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_collection_lifecycle(async_client: AsyncClient, seeded_catalog_rbac):
    """Admin can create, update, and delete curated collections with validation and audit trail."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "col_admin@uwearnova.com", "store_admin", "admin")

    admin_headers = auth_header_for(admin)

    # 1. Create collection
    payload = {
        "name": "Essentials",
        "slug": "essentials",
        "description": "Timeless luxury wardrobe staples.",
        "image_url": "https://example.com/essentials.jpg",
        "sort_order": 1,
        "is_active": True,
    }
    resp = await async_client.post("/api/v1/admin/collections", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    created_col = resp.json()
    col_id = created_col["id"]
    assert created_col["slug"] == "essentials"

    # 2. Duplicate slug error
    dup_payload = {**payload, "name": "Essentials Distinct"}
    resp = await async_client.post("/api/v1/admin/collections", json=dup_payload, headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "COLLECTION_SLUG_EXISTS"

    # 3. Update collection
    update_payload = {"name": "UniNova Essentials", "sort_order": 5}
    resp = await async_client.put(f"/api/v1/admin/collections/{col_id}", json=update_payload, headers=admin_headers)
    assert resp.status_code == 200
    updated_col = resp.json()
    assert updated_col["name"] == "UniNova Essentials"
    assert updated_col["sort_order"] == 5

    # 4. Admin inspect single collection
    resp = await async_client.get(f"/api/v1/admin/collections/{col_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "UniNova Essentials"

    # 5. Delete collection
    resp = await async_client.delete(f"/api/v1/admin/collections/{col_id}", headers=admin_headers)
    assert resp.status_code == 200

    # 6. Verify audit log entry
    async with TestingSessionLocal() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "collection",
                AuditLog.action == "collection.deleted",
                AuditLog.entity_id == str(col_id),
            )
        )
        entry = audit_res.scalar_one()
        assert entry.user_id == admin.id
        assert "UniNova Essentials" in entry.details
