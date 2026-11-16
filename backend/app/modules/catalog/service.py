"""
Catalog Service Layer
Business logic for Category and Collection lifecycle, hierarchy management, slug validation,
cyclical relationship prevention, safe deletion, and audit logging.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import AppException
from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.catalog.models import (
    Category,
    Collection,
    Product,
    ProductImage,
    ProductVariant,
    product_collections,
)
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryTreeResponse,
    CategoryUpdate,
    CollectionCreate,
    CollectionUpdate,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantUpdate,
)


# ===========================================================================
# Category Service Functions
# ===========================================================================

async def get_active_categories(
    db: AsyncSession,
    parent_id: Optional[int] = None,
    roots_only: bool = False,
) -> List[Category]:
    """Retrieve active categories visible on the customer storefront."""
    query = (
        select(Category)
        .where(Category.is_active == True)  # noqa: E712
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )

    if roots_only:
        query = query.where(Category.parent_id.is_(None))
    elif parent_id is not None:
        query = query.where(Category.parent_id == parent_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_category_tree(db: AsyncSession) -> List[CategoryTreeResponse]:
    """Build a nested hierarchical category tree of all active categories."""
    query = (
        select(Category)
        .where(Category.is_active == True)  # noqa: E712
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )
    result = await db.execute(query)
    all_categories = list(result.scalars().all())

    # Map category models to CategoryTreeResponse explicitly without triggering lazy relationship loading
    category_map: Dict[int, CategoryTreeResponse] = {
        c.id: CategoryTreeResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            image_url=c.image_url,
            sort_order=c.sort_order,
            is_active=c.is_active,
            is_coming_soon=c.is_coming_soon,
            parent_id=c.parent_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            children=[],
        )
        for c in all_categories
    }

    roots: List[CategoryTreeResponse] = []
    for c in all_categories:
        node = category_map[c.id]
        if c.parent_id is None:
            roots.append(node)
        elif c.parent_id in category_map:
            category_map[c.parent_id].children.append(node)

    return roots


async def get_category_by_slug_or_id(
    db: AsyncSession,
    identifier: str,
    active_only: bool = True,
) -> Category:
    """Retrieve category by numeric ID or slug with optional storefront active-only filter."""
    query = select(Category).options(selectinload(Category.children))

    if identifier.isdigit():
        query = query.where((Category.id == int(identifier)) | (Category.slug == identifier))
    else:
        query = query.where(Category.slug == identifier)

    if active_only:
        query = query.where(Category.is_active == True)  # noqa: E712

    result = await db.execute(query)
    category = result.scalar_one_or_none()

    if not category:
        raise AppException(
            message=f"Category '{identifier}' not found.",
            code="CATEGORY_NOT_FOUND",
            status_code=404,
        )

    return category


async def list_admin_categories(
    db: AsyncSession,
    parent_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> List[Category]:
    """Admin listing of all categories with optional filtering."""
    query = select(Category).order_by(Category.sort_order.asc(), Category.name.asc())

    if parent_id is not None:
        query = query.where(Category.parent_id == parent_id)
    if is_active is not None:
        query = query.where(Category.is_active == is_active)

    result = await db.execute(query)
    return list(result.scalars().all())


async def _check_cyclical_hierarchy(
    db: AsyncSession,
    category_id: int,
    candidate_parent_id: int,
) -> None:
    """
    Ensure candidate_parent_id is not category_id or a descendant of category_id.
    Walks up candidate_parent's ancestry to detect cycles.
    """
    current_parent_id: Optional[int] = candidate_parent_id
    visited = set()

    while current_parent_id is not None:
        if current_parent_id == category_id:
            raise AppException(
                message="Cyclical hierarchy detected: A category cannot be parented to its own descendant.",
                code="CYCLICAL_CATEGORY_HIERARCHY",
                status_code=400,
            )
        if current_parent_id in visited:
            break
        visited.add(current_parent_id)

        res = await db.execute(select(Category.parent_id).where(Category.id == current_parent_id))
        current_parent_id = res.scalar_one_or_none()


async def create_category(
    db: AsyncSession,
    data: CategoryCreate,
    actor_user: User,
) -> Category:
    """Create a new product category with name, slug, and parent verification."""
    # 1. Unique name check
    existing_name = await db.execute(select(Category).where(Category.name == data.name))
    if existing_name.scalar_one_or_none():
        raise AppException(
            message=f"Category with name '{data.name}' already exists.",
            code="CATEGORY_NAME_EXISTS",
            status_code=409,
        )

    # 2. Unique slug check
    existing_slug = await db.execute(select(Category).where(Category.slug == data.slug))
    if existing_slug.scalar_one_or_none():
        raise AppException(
            message=f"Category with slug '{data.slug}' already exists.",
            code="CATEGORY_SLUG_EXISTS",
            status_code=409,
        )

    # 3. Parent verification
    if data.parent_id is not None:
        parent_res = await db.execute(select(Category).where(Category.id == data.parent_id))
        if not parent_res.scalar_one_or_none():
            raise AppException(
                message=f"Parent category ID {data.parent_id} does not exist.",
                code="PARENT_CATEGORY_NOT_FOUND",
                status_code=404,
            )

    # 4. Create and persist
    category = Category(
        name=data.name,
        slug=data.slug,
        description=data.description,
        image_url=data.image_url,
        sort_order=data.sort_order,
        is_active=data.is_active,
        is_coming_soon=data.is_coming_soon,
        parent_id=data.parent_id,
    )
    db.add(category)
    await db.flush()

    # 5. Audit log
    await log_audit_event(
        db,
        action="category.created",
        entity_type="category",
        entity_id=str(category.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "name": category.name,
            "slug": category.slug,
            "parent_id": category.parent_id,
            "is_active": category.is_active,
        },
    )
    await db.flush()

    return category


async def update_category(
    db: AsyncSession,
    category_id: int,
    data: CategoryUpdate,
    actor_user: User,
) -> Category:
    """Update category details with collision checks, cycle prevention, and audit recording."""
    category = await db.get(Category, category_id)
    if not category:
        raise AppException(
            message=f"Category with ID {category_id} not found.",
            code="CATEGORY_NOT_FOUND",
            status_code=404,
        )

    changes: Dict[str, Any] = {}

    # 1. Name uniqueness check
    if data.name is not None and data.name != category.name:
        existing_name = await db.execute(
            select(Category).where(Category.name == data.name, Category.id != category_id)
        )
        if existing_name.scalar_one_or_none():
            raise AppException(
                message=f"Category with name '{data.name}' already exists.",
                code="CATEGORY_NAME_EXISTS",
                status_code=409,
            )
        changes["name"] = {"old": category.name, "new": data.name}
        category.name = data.name

    # 2. Slug uniqueness check
    if data.slug is not None and data.slug != category.slug:
        existing_slug = await db.execute(
            select(Category).where(Category.slug == data.slug, Category.id != category_id)
        )
        if existing_slug.scalar_one_or_none():
            raise AppException(
                message=f"Category with slug '{data.slug}' already exists.",
                code="CATEGORY_SLUG_EXISTS",
                status_code=409,
            )
        changes["slug"] = {"old": category.slug, "new": data.slug}
        category.slug = data.slug

    # 3. Parent ID validation & Cycle Prevention
    if "parent_id" in data.model_fields_set:
        new_parent_id = data.parent_id
        if new_parent_id == category_id:
            raise AppException(
                message="A category cannot be its own parent.",
                code="INVALID_PARENT_CATEGORY",
                status_code=400,
            )
        if new_parent_id is not None and new_parent_id != category.parent_id:
            parent_res = await db.execute(select(Category).where(Category.id == new_parent_id))
            if not parent_res.scalar_one_or_none():
                raise AppException(
                    message=f"Parent category ID {new_parent_id} does not exist.",
                    code="PARENT_CATEGORY_NOT_FOUND",
                    status_code=404,
                )
            await _check_cyclical_hierarchy(db, category_id, new_parent_id)

        if new_parent_id != category.parent_id:
            changes["parent_id"] = {"old": category.parent_id, "new": new_parent_id}
            category.parent_id = new_parent_id

    # 4. Optional scalar fields
    if data.description is not None and data.description != category.description:
        changes["description"] = "updated"
        category.description = data.description
    if data.image_url is not None and data.image_url != category.image_url:
        changes["image_url"] = {"old": category.image_url, "new": data.image_url}
        category.image_url = data.image_url
    if data.sort_order is not None and data.sort_order != category.sort_order:
        changes["sort_order"] = {"old": category.sort_order, "new": data.sort_order}
        category.sort_order = data.sort_order
    if data.is_active is not None and data.is_active != category.is_active:
        changes["is_active"] = {"old": category.is_active, "new": data.is_active}
        category.is_active = data.is_active
    if data.is_coming_soon is not None and data.is_coming_soon != category.is_coming_soon:
        changes["is_coming_soon"] = {"old": category.is_coming_soon, "new": data.is_coming_soon}
        category.is_coming_soon = data.is_coming_soon

    await db.flush()

    # 5. Audit log
    if changes:
        await log_audit_event(
            db,
            action="category.updated",
            entity_type="category",
            entity_id=str(category.id),
            user_id=actor_user.id,
            actor_email=actor_user.email,
            details={"changes": changes},
        )
        await db.flush()

    return category


async def delete_category(
    db: AsyncSession,
    category_id: int,
    actor_user: User,
) -> None:
    """
    Safely delete a category.
    Prevents deletion if the category has existing subcategories.
    """
    category = await db.get(Category, category_id)
    if not category:
        raise AppException(
            message=f"Category with ID {category_id} not found.",
            code="CATEGORY_NOT_FOUND",
            status_code=404,
        )

    # Prevent deletion if subcategories exist
    child_count_res = await db.execute(
        select(func.count(Category.id)).where(Category.parent_id == category_id)
    )
    child_count = child_count_res.scalar() or 0
    if child_count > 0:
        raise AppException(
            message=f"Cannot delete category '{category.name}' because it contains {child_count} subcategory/subcategories. Reassign or delete subcategories first.",
            code="CATEGORY_HAS_CHILDREN",
            status_code=400,
        )

    # Record audit log before deletion
    await log_audit_event(
        db,
        action="category.deleted",
        entity_type="category",
        entity_id=str(category.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"name": category.name, "slug": category.slug},
    )

    await db.delete(category)
    await db.flush()


# ===========================================================================
# Collection Service Functions
# ===========================================================================

async def get_active_collections(db: AsyncSession) -> List[Collection]:
    """Retrieve active curated collections for storefront navigation."""
    query = (
        select(Collection)
        .where(Collection.is_active == True)  # noqa: E712
        .order_by(Collection.sort_order.asc(), Collection.name.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_collection_by_slug_or_id(
    db: AsyncSession,
    identifier: str,
    active_only: bool = True,
) -> Collection:
    """Retrieve collection by ID or slug."""
    query = select(Collection)

    if identifier.isdigit():
        query = query.where((Collection.id == int(identifier)) | (Collection.slug == identifier))
    else:
        query = query.where(Collection.slug == identifier)

    if active_only:
        query = query.where(Collection.is_active == True)  # noqa: E712

    result = await db.execute(query)
    collection = result.scalar_one_or_none()

    if not collection:
        raise AppException(
            message=f"Collection '{identifier}' not found.",
            code="COLLECTION_NOT_FOUND",
            status_code=404,
        )

    return collection


async def list_admin_collections(
    db: AsyncSession,
    is_active: Optional[bool] = None,
) -> List[Collection]:
    """Admin listing of all collections."""
    query = select(Collection).order_by(Collection.sort_order.asc(), Collection.name.asc())

    if is_active is not None:
        query = query.where(Collection.is_active == is_active)

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_collection(
    db: AsyncSession,
    data: CollectionCreate,
    actor_user: User,
) -> Collection:
    """Create a new collection with name and slug uniqueness checks."""
    # 1. Unique name check
    existing_name = await db.execute(select(Collection).where(Collection.name == data.name))
    if existing_name.scalar_one_or_none():
        raise AppException(
            message=f"Collection with name '{data.name}' already exists.",
            code="COLLECTION_NAME_EXISTS",
            status_code=409,
        )

    # 2. Unique slug check
    existing_slug = await db.execute(select(Collection).where(Collection.slug == data.slug))
    if existing_slug.scalar_one_or_none():
        raise AppException(
            message=f"Collection with slug '{data.slug}' already exists.",
            code="COLLECTION_SLUG_EXISTS",
            status_code=409,
        )

    # 3. Create and persist
    collection = Collection(
        name=data.name,
        slug=data.slug,
        description=data.description,
        image_url=data.image_url,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(collection)
    await db.flush()

    # 4. Audit log
    await log_audit_event(
        db,
        action="collection.created",
        entity_type="collection",
        entity_id=str(collection.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "name": collection.name,
            "slug": collection.slug,
            "is_active": collection.is_active,
        },
    )
    await db.flush()

    return collection


async def update_collection(
    db: AsyncSession,
    collection_id: int,
    data: CollectionUpdate,
    actor_user: User,
) -> Collection:
    """Update collection with name and slug collision checks and audit logging."""
    collection = await db.get(Collection, collection_id)
    if not collection:
        raise AppException(
            message=f"Collection with ID {collection_id} not found.",
            code="COLLECTION_NOT_FOUND",
            status_code=404,
        )

    changes: Dict[str, Any] = {}

    # 1. Name uniqueness check
    if data.name is not None and data.name != collection.name:
        existing_name = await db.execute(
            select(Collection).where(Collection.name == data.name, Collection.id != collection_id)
        )
        if existing_name.scalar_one_or_none():
            raise AppException(
                message=f"Collection with name '{data.name}' already exists.",
                code="COLLECTION_NAME_EXISTS",
                status_code=409,
            )
        changes["name"] = {"old": collection.name, "new": data.name}
        collection.name = data.name

    # 2. Slug uniqueness check
    if data.slug is not None and data.slug != collection.slug:
        existing_slug = await db.execute(
            select(Collection).where(Collection.slug == data.slug, Collection.id != collection_id)
        )
        if existing_slug.scalar_one_or_none():
            raise AppException(
                message=f"Collection with slug '{data.slug}' already exists.",
                code="COLLECTION_SLUG_EXISTS",
                status_code=409,
            )
        changes["slug"] = {"old": collection.slug, "new": data.slug}
        collection.slug = data.slug

    # 3. Optional scalar fields
    if data.description is not None and data.description != collection.description:
        changes["description"] = "updated"
        collection.description = data.description
    if data.image_url is not None and data.image_url != collection.image_url:
        changes["image_url"] = {"old": collection.image_url, "new": data.image_url}
        collection.image_url = data.image_url
    if data.sort_order is not None and data.sort_order != collection.sort_order:
        changes["sort_order"] = {"old": collection.sort_order, "new": data.sort_order}
        collection.sort_order = data.sort_order
    if data.is_active is not None and data.is_active != collection.is_active:
        changes["is_active"] = {"old": collection.is_active, "new": data.is_active}
        collection.is_active = data.is_active

    await db.flush()

    # 4. Audit log
    if changes:
        await log_audit_event(
            db,
            action="collection.updated",
            entity_type="collection",
            entity_id=str(collection.id),
            user_id=actor_user.id,
            actor_email=actor_user.email,
            details={"changes": changes},
        )
        await db.flush()

    return collection


async def delete_collection(
    db: AsyncSession,
    collection_id: int,
    actor_user: User,
) -> None:
    """Safely delete a collection with audit recording."""
    collection = await db.get(Collection, collection_id)
    if not collection:
        raise AppException(
            message=f"Collection with ID {collection_id} not found.",
            code="COLLECTION_NOT_FOUND",
            status_code=404,
        )

    # Record audit log before deletion
    await log_audit_event(
        db,
        action="collection.deleted",
        entity_type="collection",
        entity_id=str(collection.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"name": collection.name, "slug": collection.slug},
    )

    await db.delete(collection)
    await db.flush()


# ===========================================================================
# Product Catalogue Service Functions
# ===========================================================================

async def list_products(
    db: AsyncSession,
    category_id: Optional[int] = None,
    category_slug: Optional[str] = None,
    collection_id: Optional[int] = None,
    collection_slug: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    sizes: Optional[List[str]] = None,
    colors: Optional[List[str]] = None,
    in_stock_only: bool = False,
    is_new_arrival: Optional[bool] = None,
    is_trending: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    status: Optional[str] = "active",
    sort_by: str = "newest",
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Product], int]:
    """
    Search and filter products for storefront browsing or administrative inspection.
    Includes pagination, faceted filtering, and eager loading of relationships.
    """
    query = select(Product)
    count_query = select(func.count(Product.id.distinct()))

    # 1. Status Filter
    if status is not None:
        query = query.where(Product.status == status)
        count_query = count_query.where(Product.status == status)

    # 2. Category Filter (supports parent-child hierarchy & coming-soon protection)
    if category_id is not None or (category_slug is not None and category_slug != "all"):
        target_cat = None
        if category_id is not None:
            target_cat = await db.get(Category, category_id)
        elif category_slug is not None:
            cat_res = await db.execute(select(Category).where(Category.slug == category_slug))
            target_cat = cat_res.scalar_one_or_none()

        if target_cat:
            # If category/department is marked coming soon, do not expose active product listings
            if target_cat.is_coming_soon:
                return [], 0

            # Gather target category and all direct subcategory IDs
            cat_ids = [target_cat.id]
            child_res = await db.execute(select(Category.id).where(Category.parent_id == target_cat.id))
            cat_ids.extend(child_res.scalars().all())

            query = query.where(Product.category_id.in_(cat_ids))
            count_query = count_query.where(Product.category_id.in_(cat_ids))
        else:
            return [], 0

    # 3. Collection Filter
    if collection_id is not None:
        query = query.join(product_collections, Product.id == product_collections.c.product_id).where(
            product_collections.c.collection_id == collection_id
        )
        count_query = count_query.join(product_collections, Product.id == product_collections.c.product_id).where(
            product_collections.c.collection_id == collection_id
        )
    elif collection_slug is not None and collection_slug != "all":
        query = (
            query.join(product_collections, Product.id == product_collections.c.product_id)
            .join(Collection, product_collections.c.collection_id == Collection.id)
            .where(Collection.slug == collection_slug)
        )
        count_query = (
            count_query.join(product_collections, Product.id == product_collections.c.product_id)
            .join(Collection, product_collections.c.collection_id == Collection.id)
            .where(Collection.slug == collection_slug)
        )

    # 4. Price Bounds
    if min_price is not None:
        query = query.where(Product.price >= min_price)
        count_query = count_query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
        count_query = count_query.where(Product.price <= max_price)

    # 5. Editorial Flags
    if is_new_arrival is not None:
        query = query.where(Product.is_new_arrival == is_new_arrival)
        count_query = count_query.where(Product.is_new_arrival == is_new_arrival)
    if is_trending is not None:
        query = query.where(Product.is_trending == is_trending)
        count_query = count_query.where(Product.is_trending == is_trending)
    if is_featured is not None:
        query = query.where(Product.is_featured == is_featured)
        count_query = count_query.where(Product.is_featured == is_featured)

    # 6. Faceted Variant Filters (Sizes, Colors, In-Stock)
    if sizes or colors or in_stock_only:
        variant_subq = select(ProductVariant.product_id).distinct()
        if sizes:
            variant_subq = variant_subq.where(ProductVariant.size.in_(sizes))
        if colors:
            variant_subq = variant_subq.where(ProductVariant.color_name.in_(colors))
        if in_stock_only:
            variant_subq = variant_subq.where(ProductVariant.in_stock == True, ProductVariant.inventory_count > 0)  # noqa: E712

        query = query.where(Product.id.in_(variant_subq))
        count_query = count_query.where(Product.id.in_(variant_subq))

    # 7. Search Filter
    if search:
        search_term = f"%{search}%"
        search_filter = (
            Product.name.ilike(search_term)
            | Product.slug.ilike(search_term)
            | Product.subtitle.ilike(search_term)
            | Product.description.ilike(search_term)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # 8. Total Count
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # 9. Sorting
    if sort_by == "price_asc":
        query = query.order_by(Product.price.asc(), Product.id.desc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price.desc(), Product.id.desc())
    elif sort_by == "rating":
        query = query.order_by(Product.rating.desc(), Product.review_count.desc(), Product.id.desc())
    elif sort_by == "featured":
        query = query.order_by(Product.is_featured.desc(), Product.created_at.desc(), Product.id.desc())
    else:  # newest
        query = query.order_by(Product.created_at.desc(), Product.id.desc())

    # 10. Eager loading and pagination
    query = (
        query.options(
            selectinload(Product.category),
            selectinload(Product.collections),
            selectinload(Product.variants),
            selectinload(Product.images),
        )
        .offset(offset)
        .limit(limit)
    )

    items_res = await db.execute(query)
    items = list(items_res.scalars().all())

    return items, total


async def get_product_by_slug_or_id(
    db: AsyncSession,
    identifier: str,
    status: Optional[str] = "active",
) -> Product:
    """Retrieve full product detail with eager-loaded variants, images, category, and collections."""
    query = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.collections),
            selectinload(Product.variants),
            selectinload(Product.images),
        )
    )

    if identifier.isdigit():
        query = query.where((Product.id == int(identifier)) | (Product.slug == identifier))
    else:
        query = query.where(Product.slug == identifier)

    if status is not None:
        query = query.where(Product.status == status)

    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise AppException(
            message=f"Product '{identifier}' not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    return product


async def create_product(
    db: AsyncSession,
    data: ProductCreate,
    actor_user: User,
) -> Product:
    """Create a new product with category verification, unique slug, and variant SKUs."""
    # 1. Unique slug check
    existing_slug = await db.execute(select(Product).where(Product.slug == data.slug))
    if existing_slug.scalar_one_or_none():
        raise AppException(
            message=f"Product with slug '{data.slug}' already exists.",
            code="PRODUCT_SLUG_EXISTS",
            status_code=409,
        )

    # 2. Category verification
    category = await db.get(Category, data.category_id)
    if not category:
        raise AppException(
            message=f"Category with ID {data.category_id} not found.",
            code="CATEGORY_NOT_FOUND",
            status_code=404,
        )

    # 3. Unique SKU check across submitted variants and database
    variant_skus = [v.sku for v in data.variants]
    if len(variant_skus) != len(set(variant_skus)):
        raise AppException(
            message="Duplicate SKUs submitted in variant list.",
            code="DUPLICATE_SKU",
            status_code=409,
        )
    if variant_skus:
        existing_skus_res = await db.execute(
            select(ProductVariant.sku).where(ProductVariant.sku.in_(variant_skus))
        )
        existing_skus = existing_skus_res.scalars().all()
        if existing_skus:
            raise AppException(
                message=f"Variant SKU(s) already exist: {', '.join(existing_skus)}",
                code="VARIANT_SKU_EXISTS",
                status_code=409,
            )

    # 4. Resolve collections
    collections = []
    if data.collection_ids:
        col_res = await db.execute(select(Collection).where(Collection.id.in_(data.collection_ids)))
        collections = list(col_res.scalars().all())

    # 5. Build Product model
    fabric_care_str = json.dumps(data.fabric_care) if data.fabric_care else None

    product = Product(
        name=data.name,
        slug=data.slug,
        subtitle=data.subtitle,
        description=data.description,
        category_id=data.category_id,
        brand_label=data.brand_label,
        status=data.status,
        price=data.price,
        original_price=data.original_price,
        is_new_arrival=data.is_new_arrival,
        is_trending=data.is_trending,
        is_featured=data.is_featured,
        fabric_care=fabric_care_str,
        delivery_notes=data.delivery_notes,
        collections=collections,
        variants=[],
        images=[],
    )

    # 6. Add Images
    for img_data in data.images:
        product.images.append(
            ProductImage(
                image_url=img_data.image_url,
                alt_text=img_data.alt_text,
                sort_order=img_data.sort_order,
                is_primary=img_data.is_primary,
            )
        )

    # 7. Add Variants
    for var_data in data.variants:
        product.variants.append(
            ProductVariant(
                sku=var_data.sku,
                size=var_data.size,
                color_name=var_data.color_name,
                color_hex=var_data.color_hex,
                price=var_data.price,
                compare_at_price=var_data.compare_at_price,
                inventory_count=var_data.inventory_count,
                in_stock=var_data.in_stock,
                weight_grams=var_data.weight_grams,
                is_active=var_data.is_active,
            )
        )

    db.add(product)
    await db.flush()

    # 8. Record Audit Log
    await log_audit_event(
        db,
        action="product.created",
        entity_type="product",
        entity_id=str(product.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "name": product.name,
            "slug": product.slug,
            "price": str(product.price),
            "variant_count": len(product.variants),
        },
    )
    await db.flush()

    # Refresh to return populated relationships
    return await get_product_by_slug_or_id(db, str(product.id), status=None)


async def update_product(
    db: AsyncSession,
    product_id: int,
    data: ProductUpdate,
    actor_user: User,
) -> Product:
    """Update product editorial, category, collection, or status details."""
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    changes: Dict[str, Any] = {}

    # 1. Slug check
    if data.slug is not None and data.slug != product.slug:
        existing_slug = await db.execute(
            select(Product).where(Product.slug == data.slug, Product.id != product_id)
        )
        if existing_slug.scalar_one_or_none():
            raise AppException(
                message=f"Product with slug '{data.slug}' already exists.",
                code="PRODUCT_SLUG_EXISTS",
                status_code=409,
            )
        changes["slug"] = {"old": product.slug, "new": data.slug}
        product.slug = data.slug

    # 2. Category check
    if data.category_id is not None and data.category_id != product.category_id:
        category = await db.get(Category, data.category_id)
        if not category:
            raise AppException(
                message=f"Category with ID {data.category_id} not found.",
                code="CATEGORY_NOT_FOUND",
                status_code=404,
            )
        changes["category_id"] = {"old": product.category_id, "new": data.category_id}
        product.category_id = data.category_id

    # 3. Collection assignments
    if data.collection_ids is not None:
        col_res = await db.execute(select(Collection).where(Collection.id.in_(data.collection_ids)))
        product.collections = list(col_res.scalars().all())
        changes["collections"] = data.collection_ids

    # 4. Scalar fields
    if data.name is not None and data.name != product.name:
        changes["name"] = {"old": product.name, "new": data.name}
        product.name = data.name
    if data.subtitle is not None and data.subtitle != product.subtitle:
        product.subtitle = data.subtitle
    if data.description is not None and data.description != product.description:
        product.description = data.description
    if data.brand_label is not None and data.brand_label != product.brand_label:
        product.brand_label = data.brand_label
    if data.status is not None and data.status != product.status:
        changes["status"] = {"old": product.status, "new": data.status}
        product.status = data.status
    if data.price is not None and data.price != product.price:
        changes["price"] = {"old": str(product.price), "new": str(data.price)}
        product.price = data.price
    if data.original_price is not None and data.original_price != product.original_price:
        product.original_price = data.original_price
    if data.is_new_arrival is not None:
        product.is_new_arrival = data.is_new_arrival
    if data.is_trending is not None:
        product.is_trending = data.is_trending
    if data.is_featured is not None:
        product.is_featured = data.is_featured
    if data.fabric_care is not None:
        product.fabric_care = json.dumps(data.fabric_care)
    if data.delivery_notes is not None:
        product.delivery_notes = data.delivery_notes

    await db.flush()

    if changes:
        await log_audit_event(
            db,
            action="product.updated",
            entity_type="product",
            entity_id=str(product.id),
            user_id=actor_user.id,
            actor_email=actor_user.email,
            details={"changes": changes},
        )
        await db.flush()

    return await get_product_by_slug_or_id(db, str(product.id), status=None)


async def delete_product(
    db: AsyncSession,
    product_id: int,
    actor_user: User,
) -> None:
    """Delete a product and cascade to variants, imagery, and collection associations."""
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    await log_audit_event(
        db,
        action="product.deleted",
        entity_type="product",
        entity_id=str(product.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"name": product.name, "slug": product.slug},
    )

    await db.delete(product)
    await db.flush()


async def add_product_variant(
    db: AsyncSession,
    product_id: int,
    data: ProductVariantCreate,
    actor_user: User,
) -> ProductVariant:
    """Add a new variant SKU to an existing product."""
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    existing_sku = await db.execute(select(ProductVariant).where(ProductVariant.sku == data.sku))
    if existing_sku.scalar_one_or_none():
        raise AppException(
            message=f"Variant SKU '{data.sku}' already exists.",
            code="VARIANT_SKU_EXISTS",
            status_code=409,
        )

    variant = ProductVariant(
        product_id=product_id,
        sku=data.sku,
        size=data.size,
        color_name=data.color_name,
        color_hex=data.color_hex,
        price=data.price,
        compare_at_price=data.compare_at_price,
        inventory_count=data.inventory_count,
        in_stock=data.in_stock,
        weight_grams=data.weight_grams,
        is_active=data.is_active,
    )
    db.add(variant)
    await db.flush()

    await log_audit_event(
        db,
        action="product_variant.created",
        entity_type="product_variant",
        entity_id=str(variant.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"product_id": product_id, "sku": variant.sku},
    )
    await db.flush()

    return variant


async def publish_product(
    db: AsyncSession,
    product_id: int,
    actor_user: User,
) -> Product:
    """
    Publish a draft or archived product to the live public customer storefront.
    Validates that the product contains at least one active variant.
    """
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    # Check active variants
    var_stmt = select(func.count(ProductVariant.id)).where(
        ProductVariant.product_id == product_id,
        ProductVariant.is_active == True,  # noqa: E712
    )
    var_res = await db.execute(var_stmt)
    active_variants_count = var_res.scalar_one()

    if active_variants_count == 0:
        raise AppException(
            message="Cannot publish product: Product must have at least one active variant.",
            code="NO_ACTIVE_VARIANTS",
            status_code=400,
        )

    old_status = product.status
    product.status = "active"
    product.is_active = True
    if not product.published_at:
        product.published_at = datetime.now(timezone.utc)
    await db.flush()

    await log_audit_event(
        db,
        action="product.published",
        entity_type="product",
        entity_id=str(product.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"name": product.name, "from_status": old_status, "to_status": "active"},
    )
    await db.flush()

    return await get_product_by_slug_or_id(db, str(product.id), status=None)


async def archive_product(
    db: AsyncSession,
    product_id: int,
    actor_user: User,
) -> Product:
    """
    Archive a product, immediately unpublishing it from customer storefront browsing.
    """
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    old_status = product.status
    product.status = "archived"
    await db.flush()

    await log_audit_event(
        db,
        action="product.archived",
        entity_type="product",
        entity_id=str(product.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"name": product.name, "from_status": old_status, "to_status": "archived"},
    )
    await db.flush()

    return await get_product_by_slug_or_id(db, str(product.id), status=None)


async def unarchive_product(
    db: AsyncSession,
    product_id: int,
    actor_user: User,
) -> Product:
    """
    Restore an archived product back to draft status for editorial review.
    """
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    old_status = product.status
    product.status = "draft"
    await db.flush()

    await log_audit_event(
        db,
        action="product.unarchived",
        entity_type="product",
        entity_id=str(product.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"name": product.name, "from_status": old_status, "to_status": "draft"},
    )
    await db.flush()

    return await get_product_by_slug_or_id(db, str(product.id), status=None)


async def bulk_update_product_status(
    db: AsyncSession,
    product_ids: List[int],
    new_status: str,
    actor_user: User,
) -> Tuple[int, List[int]]:
    """
    Bulk update status across multiple products with validation and audit logging.
    """
    stmt = select(Product).options(selectinload(Product.variants)).where(Product.id.in_(product_ids))
    res = await db.execute(stmt)
    products = res.scalars().all()

    if not products:
        raise AppException(
            message="None of the specified products were found.",
            code="PRODUCTS_NOT_FOUND",
            status_code=404,
        )

    updated_ids = []
    for prod in products:
        if new_status == "active":
            has_active = any(v.is_active for v in prod.variants)
            if not has_active:
                raise AppException(
                    message=f"Cannot publish product '{prod.name}' (ID {prod.id}): Must have at least one active variant.",
                    code="NO_ACTIVE_VARIANTS",
                    status_code=400,
                )
            prod.is_active = True

        prod.status = new_status
        updated_ids.append(prod.id)

    await db.flush()

    await log_audit_event(
        db,
        action="products.bulk_status_updated",
        entity_type="product",
        entity_id="bulk",
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"product_ids": updated_ids, "new_status": new_status, "count": len(updated_ids)},
    )
    await db.flush()

    return len(updated_ids), updated_ids


async def update_product_variant(
    db: AsyncSession,
    product_id: int,
    variant_id: int,
    data: ProductVariantUpdate,
    actor_user: User,
) -> ProductVariant:
    """
    Update SKU variant fields, verifying product association and SKU uniqueness.
    """
    stmt = select(ProductVariant).where(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id,
    )
    res = await db.execute(stmt)
    variant = res.scalar_one_or_none()

    if not variant:
        raise AppException(
            message=f"Variant with ID {variant_id} not found on product {product_id}.",
            code="VARIANT_NOT_FOUND",
            status_code=404,
        )

    # SKU uniqueness check
    if data.sku is not None and data.sku != variant.sku:
        existing_sku = await db.execute(
            select(ProductVariant).where(
                ProductVariant.sku == data.sku,
                ProductVariant.id != variant_id,
            )
        )
        if existing_sku.scalar_one_or_none():
            raise AppException(
                message=f"Variant SKU '{data.sku}' already exists on another variant.",
                code="VARIANT_SKU_EXISTS",
                status_code=409,
            )
        variant.sku = data.sku

    if data.size is not None:
        variant.size = data.size
    if data.color_name is not None:
        variant.color_name = data.color_name
    if data.color_hex is not None:
        variant.color_hex = data.color_hex
    if data.price is not None:
        variant.price = data.price
    if data.compare_at_price is not None:
        variant.compare_at_price = data.compare_at_price
    if data.inventory_count is not None:
        variant.inventory_count = data.inventory_count
    if data.in_stock is not None:
        variant.in_stock = data.in_stock
    if data.weight_grams is not None:
        variant.weight_grams = data.weight_grams
    if data.is_active is not None:
        variant.is_active = data.is_active

    await db.flush()

    await log_audit_event(
        db,
        action="product_variant.updated",
        entity_type="product_variant",
        entity_id=str(variant.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"product_id": product_id, "sku": variant.sku},
    )
    await db.flush()

    return variant


async def delete_product_variant(
    db: AsyncSession,
    product_id: int,
    variant_id: int,
    actor_user: User,
) -> None:
    """
    Delete a variant SKU from a product.
    Prevents deleting the sole active variant of an active/published product.
    """
    stmt = select(ProductVariant).where(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id,
    )
    res = await db.execute(stmt)
    variant = res.scalar_one_or_none()

    if not variant:
        raise AppException(
            message=f"Variant with ID {variant_id} not found on product {product_id}.",
            code="VARIANT_NOT_FOUND",
            status_code=404,
        )

    product = await db.get(Product, product_id)
    if product and product.status == "active":
        active_stmt = select(func.count(ProductVariant.id)).where(
            ProductVariant.product_id == product_id,
            ProductVariant.is_active == True,  # noqa: E712
            ProductVariant.id != variant_id,
        )
        active_res = await db.execute(active_stmt)
        remaining_active = active_res.scalar_one()
        if remaining_active == 0:
            raise AppException(
                message="Cannot delete the sole active variant of a live product. Unpublish or archive the product first.",
                code="SOLE_ACTIVE_VARIANT",
                status_code=400,
            )

    sku = variant.sku
    await db.delete(variant)
    await db.flush()

    await log_audit_event(
        db,
        action="product_variant.deleted",
        entity_type="product_variant",
        entity_id=str(variant_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"product_id": product_id, "sku": sku},
    )
    await db.flush()


async def assign_products_to_collection(
    db: AsyncSession,
    collection_id: int,
    product_ids: List[int],
    actor_user: User,
) -> Collection:
    """
    Associate products with a curated collection.
    """
    collection = await db.get(Collection, collection_id)
    if not collection:
        raise AppException(
            message=f"Collection with ID {collection_id} not found.",
            code="COLLECTION_NOT_FOUND",
            status_code=404,
        )

    # Load existing and new products
    stmt = select(Product).where(Product.id.in_(product_ids))
    res = await db.execute(stmt)
    products_to_add = res.scalars().all()

    # Eager load collection.products
    col_stmt = select(Collection).options(selectinload(Collection.products)).where(Collection.id == collection_id)
    col_res = await db.execute(col_stmt)
    col_loaded = col_res.scalar_one()

    current_ids = {p.id for p in col_loaded.products}
    for p in products_to_add:
        if p.id not in current_ids:
            col_loaded.products.append(p)

    await db.flush()

    await log_audit_event(
        db,
        action="collection.products_assigned",
        entity_type="collection",
        entity_id=str(collection_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"collection_id": collection_id, "product_ids": [p.id for p in products_to_add]},
    )
    await db.flush()

    return col_loaded


async def remove_product_from_collection(
    db: AsyncSession,
    collection_id: int,
    product_id: int,
    actor_user: User,
) -> Collection:
    """
    Remove product association from a curated collection.
    """
    col_stmt = select(Collection).options(selectinload(Collection.products)).where(Collection.id == collection_id)
    col_res = await db.execute(col_stmt)
    col_loaded = col_res.scalar_one_or_none()

    if not col_loaded:
        raise AppException(
            message=f"Collection with ID {collection_id} not found.",
            code="COLLECTION_NOT_FOUND",
            status_code=404,
        )

    col_loaded.products = [p for p in col_loaded.products if p.id != product_id]
    await db.flush()

    await log_audit_event(
        db,
        action="collection.product_removed",
        entity_type="collection",
        entity_id=str(collection_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"collection_id": collection_id, "product_id": product_id},
    )
    await db.flush()

    return col_loaded


