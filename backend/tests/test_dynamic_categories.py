"""
Dynamic Category & Department Architecture Tests (Phase 5 — M24)
Tests dynamic storefront department tree, subcategory hierarchy, coming-soon department states,
and recursive parent-child product filtering.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category, Product
from app.modules.catalog.seed_data import seed_catalog_products
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seeded_catalog():
    """Ensure catalog categories and authentic products are seeded."""
    async with TestingSessionLocal() as session:
        await seed_catalog_products(session)
        await session.commit()


@pytest.mark.asyncio
async def test_dynamic_department_tree_and_coming_soon(async_client: AsyncClient, seeded_catalog):
    """
    Verify /api/v1/categories/tree returns:
    - Active root departments: Men, Women, Kids
    - Future departments marked is_coming_soon: Footwear, Accessories, Perfumes
    - Subcategories nested under active departments without hardcoding
    """
    resp = await async_client.get("/api/v1/categories/tree")
    assert resp.status_code == 200, resp.text
    tree = resp.json()

    # Find root departments
    roots_by_slug = {c["slug"]: c for c in tree}

    # 1. Verify Active Departments
    assert "men" in roots_by_slug
    assert "women" in roots_by_slug
    assert "kids" in roots_by_slug

    assert roots_by_slug["men"]["is_coming_soon"] is False
    assert roots_by_slug["women"]["is_coming_soon"] is False
    assert roots_by_slug["kids"]["is_coming_soon"] is False

    # 2. Verify Men subcategories (Hoodies, Jackets, T-Shirts, Sweaters, Jeans & Pants)
    men_children = {c["slug"]: c for c in roots_by_slug["men"]["children"]}
    assert "men-hoodies" in men_children
    assert "men-jackets" in men_children
    assert "men-t-shirts" in men_children
    assert "men-sweaters" in men_children
    assert "men-jeans-pants" in men_children

    # 3. Verify Women subcategories
    women_children = {c["slug"]: c for c in roots_by_slug["women"]["children"]}
    assert "women-hoodies" in women_children
    assert "women-jackets" in women_children
    assert "women-t-shirts" in women_children
    assert "women-sweaters" in women_children

    # 4. Verify Kids subcategories
    kids_children = {c["slug"]: c for c in roots_by_slug["kids"]["children"]}
    assert "kids-hoodies" in kids_children
    assert "kids-jackets" in kids_children
    assert "kids-t-shirts" in kids_children
    assert "kids-sweaters" in kids_children

    # 5. Verify Future Departments have is_coming_soon == True
    assert "footwear" in roots_by_slug
    assert "accessories" in roots_by_slug
    assert "perfumes" in roots_by_slug

    assert roots_by_slug["footwear"]["is_coming_soon"] is True
    assert roots_by_slug["accessories"]["is_coming_soon"] is True
    assert roots_by_slug["perfumes"]["is_coming_soon"] is True


@pytest.mark.asyncio
async def test_parent_department_product_aggregation(async_client: AsyncClient, seeded_catalog):
    """
    Filtering by parent category_slug (e.g. 'men') recursively includes products
    assigned to its subcategories (men-jackets, men-t-shirts, men-jeans-pants).
    """
    # 1. Querying parent department 'men'
    resp_men = await async_client.get("/api/v1/products?category_slug=men")
    assert resp_men.status_code == 200
    men_data = resp_men.json()
    assert men_data["total"] >= 3
    men_slugs = {p["slug"] for p in men_data["items"]}
    assert "monolith-oversized-wool-blazer" in men_slugs
    assert "relaxed-egyptian-cotton-kurta-shirt" in men_slugs
    assert "pleated-wide-leg-trousers" in men_slugs

    # 2. Querying specific subcategory 'men-jackets'
    resp_jackets = await async_client.get("/api/v1/products?category_slug=men-jackets")
    assert resp_jackets.status_code == 200
    jackets_data = resp_jackets.json()
    assert jackets_data["total"] >= 1
    assert any(p["slug"] == "monolith-oversized-wool-blazer" for p in jackets_data["items"])
    # Should not include t-shirts
    assert not any(p["slug"] == "relaxed-egyptian-cotton-kurta-shirt" for p in jackets_data["items"])


@pytest.mark.asyncio
async def test_coming_soon_department_no_active_shopping_listings(async_client: AsyncClient, seeded_catalog):
    """
    Coming Soon departments (Footwear, Accessories, Perfumes) do not expose active
    shopping product listings via public catalog API.
    """
    resp_footwear = await async_client.get("/api/v1/products?category_slug=footwear")
    assert resp_footwear.status_code == 200
    assert resp_footwear.json()["total"] == 0
    assert len(resp_footwear.json()["items"]) == 0

    resp_perfumes = await async_client.get("/api/v1/products?category_slug=perfumes")
    assert resp_perfumes.status_code == 200
    assert resp_perfumes.json()["total"] == 0
