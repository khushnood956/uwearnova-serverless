"""
Catalog API Endpoints
Public storefront browsing and protected administrative CRUD for Categories and Collections.
"""

from decimal import Decimal
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdate,
    CollectionCreate,
    CollectionProductAssignRequest,
    CollectionResponse,
    CollectionUpdate,
    ProductBulkStatusRequest,
    ProductBulkStatusResponse,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
)
from app.modules.catalog.service import (
    add_product_variant,
    archive_product,
    assign_products_to_collection,
    bulk_update_product_status,
    create_category,
    create_collection,
    create_product,
    delete_category,
    delete_collection,
    delete_product,
    delete_product_variant,
    get_active_categories,
    get_active_collections,
    get_category_by_slug_or_id,
    get_category_tree,
    get_collection_by_slug_or_id,
    get_product_by_slug_or_id,
    list_admin_categories,
    list_admin_collections,
    list_products,
    publish_product,
    remove_product_from_collection,
    unarchive_product,
    update_category,
    update_collection,
    update_product,
    update_product_variant,
)
from app.modules.rbac.dependencies import require_any_permission, require_permission

# Routers
public_categories_router = APIRouter(prefix="/categories", tags=["Storefront: Categories"])
public_collections_router = APIRouter(prefix="/collections", tags=["Storefront: Collections"])
public_products_router = APIRouter(prefix="/products", tags=["Storefront: Products"])
admin_categories_router = APIRouter(prefix="/admin/categories", tags=["Admin: Categories"])
admin_collections_router = APIRouter(prefix="/admin/collections", tags=["Admin: Collections"])
admin_products_router = APIRouter(prefix="/admin/products", tags=["Admin: Products"])


# ===========================================================================
# Public Categories Endpoints
# ===========================================================================

@public_categories_router.get(
    "",
    response_model=List[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List Active Storefront Categories",
)
async def list_public_categories(
    parent_id: Optional[int] = Query(None, description="Filter by parent category ID"),
    roots_only: bool = Query(False, description="Return only top-level categories"),
    db: AsyncSession = Depends(get_db),
) -> List[CategoryResponse]:
    """Retrieve active categories visible on the customer storefront."""
    categories = await get_active_categories(db, parent_id=parent_id, roots_only=roots_only)
    return [CategoryResponse.model_validate(c) for c in categories]


@public_categories_router.get(
    "/tree",
    response_model=List[CategoryTreeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Hierarchical Category Tree",
)
async def get_public_category_tree(
    db: AsyncSession = Depends(get_db),
) -> List[CategoryTreeResponse]:
    """Retrieve full hierarchical taxonomy tree of active categories."""
    return await get_category_tree(db)


@public_categories_router.get(
    "/{identifier}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Category by Slug or ID",
)
async def get_public_category(
    identifier: str,
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Retrieve single active category by numeric ID or slug."""
    category = await get_category_by_slug_or_id(db, identifier=identifier, active_only=True)
    return CategoryResponse.model_validate(category)


# ===========================================================================
# Public Collections Endpoints
# ===========================================================================

@public_collections_router.get(
    "",
    response_model=List[CollectionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Active Storefront Collections",
)
async def list_public_collections(
    db: AsyncSession = Depends(get_db),
) -> List[CollectionResponse]:
    """Retrieve active curated collections for storefront navigation."""
    collections = await get_active_collections(db)
    return [CollectionResponse.model_validate(c) for c in collections]


@public_collections_router.get(
    "/{identifier}",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Collection by Slug or ID",
)
async def get_public_collection(
    identifier: str,
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    """Retrieve single active collection by numeric ID or slug."""
    collection = await get_collection_by_slug_or_id(db, identifier=identifier, active_only=True)
    return CollectionResponse.model_validate(collection)


# ===========================================================================
# Admin Categories Endpoints
# ===========================================================================

@admin_categories_router.get(
    "",
    response_model=List[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List All Categories",
)
async def admin_list_categories(
    parent_id: Optional[int] = Query(None, description="Filter by parent ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_permission(["categories.manage", "products.read"])),
) -> List[CategoryResponse]:
    """Administrative listing of all categories including drafts/inactive."""
    categories = await list_admin_categories(db, parent_id=parent_id, is_active=is_active)
    return [CategoryResponse.model_validate(c) for c in categories]


@admin_categories_router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Get Category by ID",
)
async def admin_get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_permission(["categories.manage", "products.read"])),
) -> CategoryResponse:
    """Administrative retrieval of a category by numeric ID."""
    category = await get_category_by_slug_or_id(db, identifier=str(category_id), active_only=False)
    return CategoryResponse.model_validate(category)


@admin_categories_router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create Category",
)
async def admin_create_category(
    req: CategoryCreate,
    current_user: User = Depends(require_permission("categories.manage")),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Create a new category with name, slug uniqueness validation and audit logging."""
    category = await create_category(db, req, actor_user=current_user)
    return CategoryResponse.model_validate(category)


@admin_categories_router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Category",
)
async def admin_update_category(
    category_id: int,
    req: CategoryUpdate,
    current_user: User = Depends(require_permission("categories.manage")),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Update category attributes, cycle checking, and audit logging."""
    category = await update_category(db, category_id=category_id, data=req, actor_user=current_user)
    return CategoryResponse.model_validate(category)


@admin_categories_router.delete(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    summary="Admin: Delete Category",
)
async def admin_delete_category(
    category_id: int,
    current_user: User = Depends(require_permission("categories.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Safely delete category, preventing deletion if subcategories exist."""
    await delete_category(db, category_id=category_id, actor_user=current_user)
    return {"message": f"Category {category_id} successfully deleted."}


# ===========================================================================
# Admin Collections Endpoints
# ===========================================================================

@admin_collections_router.get(
    "",
    response_model=List[CollectionResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List All Collections",
)
async def admin_list_collections(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_permission(["collections.manage", "products.read"])),
) -> List[CollectionResponse]:
    """Administrative listing of all curated collections."""
    collections = await list_admin_collections(db, is_active=is_active)
    return [CollectionResponse.model_validate(c) for c in collections]


@admin_collections_router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Get Collection by ID",
)
async def admin_get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_permission(["collections.manage", "products.read"])),
) -> CollectionResponse:
    """Administrative retrieval of a collection by ID."""
    collection = await get_collection_by_slug_or_id(db, identifier=str(collection_id), active_only=False)
    return CollectionResponse.model_validate(collection)


@admin_collections_router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create Collection",
)
async def admin_create_collection(
    req: CollectionCreate,
    current_user: User = Depends(require_permission("collections.manage")),
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    """Create a curated collection with name and slug uniqueness validation."""
    collection = await create_collection(db, req, actor_user=current_user)
    return CollectionResponse.model_validate(collection)


@admin_collections_router.put(
    "/{collection_id}",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Collection",
)
async def admin_update_collection(
    collection_id: int,
    req: CollectionUpdate,
    current_user: User = Depends(require_permission("collections.manage")),
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    """Update collection attributes and record audit log."""
    collection = await update_collection(db, collection_id=collection_id, data=req, actor_user=current_user)
    return CollectionResponse.model_validate(collection)


@admin_collections_router.delete(
    "/{collection_id}",
    status_code=status.HTTP_200_OK,
    summary="Admin: Delete Collection",
)
async def admin_delete_collection(
    collection_id: int,
    current_user: User = Depends(require_permission("collections.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Safely delete collection with audit trail."""
    await delete_collection(db, collection_id=collection_id, actor_user=current_user)
    return {"message": f"Collection {collection_id} successfully deleted."}


@admin_collections_router.post(
    "/{collection_id}/products",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Assign Products to Collection",
)
async def admin_assign_products_to_collection(
    collection_id: int,
    req: CollectionProductAssignRequest,
    current_user: User = Depends(require_permission("collections.manage")),
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    """Assign one or more products to a curated collection."""
    collection = await assign_products_to_collection(
        db, collection_id=collection_id, product_ids=req.product_ids, actor_user=current_user
    )
    return CollectionResponse.model_validate(collection)


@admin_collections_router.delete(
    "/{collection_id}/products/{product_id}",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Remove Product from Collection",
)
async def admin_remove_product_from_collection(
    collection_id: int,
    product_id: int,
    current_user: User = Depends(require_permission("collections.manage")),
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    """Remove a product from a curated collection."""
    collection = await remove_product_from_collection(
        db, collection_id=collection_id, product_id=product_id, actor_user=current_user
    )
    return CollectionResponse.model_validate(collection)


# ===========================================================================
# Public Products Endpoints
# ===========================================================================

@public_products_router.get(
    "",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Storefront Products with Faceted Filtering & Sorting",
)
async def list_public_products(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    category_slug: Optional[str] = Query(None, description="Filter by category slug"),
    collection_id: Optional[int] = Query(None, description="Filter by collection ID"),
    collection_slug: Optional[str] = Query(None, description="Filter by collection slug"),
    min_price: Optional[Decimal] = Query(None, ge=Decimal(0), description="Minimum price in PKR"),
    max_price: Optional[Decimal] = Query(None, ge=Decimal(0), description="Maximum price in PKR"),
    sizes: Optional[List[str]] = Query(None, description="Filter by sizes"),
    colors: Optional[List[str]] = Query(None, description="Filter by color names"),
    in_stock_only: bool = Query(False, description="Filter only in-stock products"),
    is_new_arrival: Optional[bool] = Query(None, description="New arrivals filter"),
    is_trending: Optional[bool] = Query(None, description="Trending items filter"),
    is_featured: Optional[bool] = Query(None, description="Featured items filter"),
    search: Optional[str] = Query(None, description="Search keyword in title, subtitle, or description"),
    sort_by: str = Query("newest", pattern=r"^(newest|price_asc|price_desc|rating|featured)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    """Storefront product catalogue with faceted filtering, multi-attribute search, and pagination."""
    items, total = await list_products(
        db,
        category_id=category_id,
        category_slug=category_slug,
        collection_id=collection_id,
        collection_slug=collection_slug,
        min_price=min_price,
        max_price=max_price,
        sizes=sizes,
        colors=colors,
        in_stock_only=in_stock_only,
        is_new_arrival=is_new_arrival,
        is_trending=is_trending,
        is_featured=is_featured,
        search=search,
        status="active",
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@public_products_router.get(
    "/{identifier}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active Product by Slug or ID",
)
async def get_public_product(
    identifier: str,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Storefront retrieval of a live active product by its URL slug or numeric ID."""
    product = await get_product_by_slug_or_id(db, identifier=identifier, status="active")
    return ProductResponse.model_validate(product)


# ===========================================================================
# Admin Products Endpoints
# ===========================================================================

@admin_products_router.get(
    "",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: List All Products",
)
async def admin_list_products(
    category_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status", pattern=r"^(draft|active|archived)$"),
    search: Optional[str] = Query(None),
    sort_by: str = Query("newest", pattern=r"^(newest|price_asc|price_desc|rating|featured)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("products.read")),
) -> ProductListResponse:
    """Administrative product catalogue view including drafts, archived items, and inventory counts."""
    items, total = await list_products(
        db,
        category_id=category_id,
        status=status_filter,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@admin_products_router.post(
    "/bulk-status",
    response_model=ProductBulkStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Bulk Update Product Statuses",
)
async def admin_bulk_status(
    req: ProductBulkStatusRequest,
    current_user: User = Depends(require_any_permission(["products.update", "products.publish", "products.archive"])),
    db: AsyncSession = Depends(get_db),
) -> ProductBulkStatusResponse:
    """Bulk update product statuses (draft, active, archived) safely with validation."""
    count, ids = await bulk_update_product_status(
        db, product_ids=req.product_ids, new_status=req.status, actor_user=current_user
    )
    return ProductBulkStatusResponse(
        updated_count=count,
        status=req.status,
        product_ids=ids,
    )


@admin_products_router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Get Product by ID",
)
async def admin_get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("products.read")),
) -> ProductResponse:
    """Administrative retrieval of a product with all variants, images, and collections."""
    product = await get_product_by_slug_or_id(db, identifier=str(product_id), status=None)
    return ProductResponse.model_validate(product)


@admin_products_router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create Product",
)
async def admin_create_product(
    req: ProductCreate,
    current_user: User = Depends(require_permission("products.create")),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Create a new product with variants, imagery, collections, and audit logging."""
    product = await create_product(db, req, actor_user=current_user)
    return ProductResponse.model_validate(product)


@admin_products_router.put(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Product",
)
async def admin_update_product(
    product_id: int,
    req: ProductUpdate,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update product information, pricing, status, and collections with audit logging."""
    product = await update_product(db, product_id=product_id, data=req, actor_user=current_user)
    return ProductResponse.model_validate(product)


@admin_products_router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
    summary="Admin: Delete Product",
)
async def admin_delete_product(
    product_id: int,
    current_user: User = Depends(require_permission("products.archive")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a product, cascading to variants and images, with audit logging."""
    await delete_product(db, product_id=product_id, actor_user=current_user)
    return {"message": f"Product {product_id} successfully deleted."}


@admin_products_router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Add Product Variant",
)
async def admin_add_variant(
    product_id: int,
    req: ProductVariantCreate,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> ProductVariantResponse:
    """Add a new SKU variant to an existing product."""
    variant = await add_product_variant(db, product_id=product_id, data=req, actor_user=current_user)
    return ProductVariantResponse.model_validate(variant)


@admin_products_router.put(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Update Product Variant",
)
async def admin_update_variant(
    product_id: int,
    variant_id: int,
    req: ProductVariantUpdate,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> ProductVariantResponse:
    """Update variant details (SKU, price, size, color, active status)."""
    variant = await update_product_variant(
        db, product_id=product_id, variant_id=variant_id, data=req, actor_user=current_user
    )
    return ProductVariantResponse.model_validate(variant)


@admin_products_router.delete(
    "/{product_id}/variants/{variant_id}",
    status_code=status.HTTP_200_OK,
    summary="Admin: Delete Product Variant",
)
async def admin_delete_variant(
    product_id: int,
    variant_id: int,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
):
    """Safely delete variant. Prevents deleting the sole active variant of an active product."""
    await delete_product_variant(
        db, product_id=product_id, variant_id=variant_id, actor_user=current_user
    )
    return {"message": f"Variant {variant_id} successfully deleted."}


@admin_products_router.post(
    "/{product_id}/publish",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Publish Product",
)
async def admin_publish_product(
    product_id: int,
    current_user: User = Depends(require_permission("products.publish")),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Publish a draft product to active status after verifying variant requirements."""
    product = await publish_product(db, product_id=product_id, actor_user=current_user)
    return ProductResponse.model_validate(product)


@admin_products_router.post(
    "/{product_id}/archive",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Archive Product",
)
async def admin_archive_product(
    product_id: int,
    current_user: User = Depends(require_permission("products.archive")),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Archive an active or draft product, immediately hiding it from the storefront."""
    product = await archive_product(db, product_id=product_id, actor_user=current_user)
    return ProductResponse.model_validate(product)


@admin_products_router.post(
    "/{product_id}/unarchive",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Unarchive Product to Draft",
)
async def admin_unarchive_product(
    product_id: int,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Restore an archived product back to draft status for review before re-publishing."""
    product = await unarchive_product(db, product_id=product_id, actor_user=current_user)
    return ProductResponse.model_validate(product)

