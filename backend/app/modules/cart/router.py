"""
Cart and Wishlist API Endpoints (M10)
Public storefront endpoints for managing shopping carts and customer wishlists.
Supports both guest shopping carts (via X-Anonymous-Cart-Token) and authenticated
customer accounts, ensuring complete customer ownership isolation.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.models import User
from app.modules.cart.schemas import (
    AddToCartRequest,
    AddToWishlistRequest,
    CartResponse,
    MergeCartRequest,
    UpdateCartItemRequest,
    WishlistResponse,
)
from app.modules.cart.service import (
    add_item_to_cart,
    add_product_to_wishlist,
    build_cart_response,
    clear_cart,
    clear_customer_wishlist,
    get_or_create_cart,
    get_or_create_wishlist,
    merge_guest_cart_into_user_cart,
    remove_cart_item,
    remove_product_from_wishlist,
    update_cart_item_quantity,
)

cart_router = APIRouter(prefix="/cart", tags=["Storefront: Cart"])
wishlist_router = APIRouter(prefix="/wishlist", tags=["Storefront: Wishlist"])


# ===========================================================================
# Cart Endpoints
# ===========================================================================

@cart_router.get(
    "",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Active Cart",
)
async def get_cart(
    response: Response,
    x_anonymous_cart_token: Optional[str] = Header(None, alias="X-Anonymous-Cart-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """
    Retrieve active shopping cart with verified catalogue prices, available stock,
    and free-shipping calculation. Never trusts client values.
    """
    cart, _ = await get_or_create_cart(
        db,
        user=current_user,
        anonymous_token=x_anonymous_cart_token,
    )
    if not current_user and cart.anonymous_token:
        response.headers["X-Anonymous-Cart-Token"] = cart.anonymous_token

    return await build_cart_response(db, cart)


@cart_router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Add Product Variant to Cart",
)
async def add_to_cart_endpoint(
    req: AddToCartRequest,
    response: Response,
    x_anonymous_cart_token: Optional[str] = Header(None, alias="X-Anonymous-Cart-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """
    Add a product SKU variant to the active cart.
    Validates variant existence, publication status, and stock availability.
    """
    cart, _ = await get_or_create_cart(
        db,
        user=current_user,
        anonymous_token=x_anonymous_cart_token,
    )
    if not current_user and cart.anonymous_token:
        response.headers["X-Anonymous-Cart-Token"] = cart.anonymous_token

    return await add_item_to_cart(
        db,
        cart=cart,
        variant_id=req.variant_id,
        quantity=req.quantity,
    )


@cart_router.patch(
    "/items/{item_id}",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Line Item Quantity",
)
async def update_item_quantity_endpoint(
    item_id: int,
    req: UpdateCartItemRequest,
    response: Response,
    x_anonymous_cart_token: Optional[str] = Header(None, alias="X-Anonymous-Cart-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """
    Update line item quantity or delete if quantity is zero.
    Enforces strict cart ownership isolation (cannot modify item in another user's cart).
    """
    cart, _ = await get_or_create_cart(
        db,
        user=current_user,
        anonymous_token=x_anonymous_cart_token,
    )
    if not current_user and cart.anonymous_token:
        response.headers["X-Anonymous-Cart-Token"] = cart.anonymous_token

    return await update_cart_item_quantity(
        db,
        cart=cart,
        item_id=item_id,
        quantity=req.quantity,
    )


@cart_router.delete(
    "/items/{item_id}",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove Line Item from Cart",
)
async def remove_item_endpoint(
    item_id: int,
    response: Response,
    x_anonymous_cart_token: Optional[str] = Header(None, alias="X-Anonymous-Cart-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """Remove a line item from the active cart."""
    cart, _ = await get_or_create_cart(
        db,
        user=current_user,
        anonymous_token=x_anonymous_cart_token,
    )
    if not current_user and cart.anonymous_token:
        response.headers["X-Anonymous-Cart-Token"] = cart.anonymous_token

    return await remove_cart_item(db, cart=cart, item_id=item_id)


@cart_router.delete(
    "",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear All Items from Cart",
)
async def clear_cart_endpoint(
    response: Response,
    x_anonymous_cart_token: Optional[str] = Header(None, alias="X-Anonymous-Cart-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """Empty the current shopping cart."""
    cart, _ = await get_or_create_cart(
        db,
        user=current_user,
        anonymous_token=x_anonymous_cart_token,
    )
    if not current_user and cart.anonymous_token:
        response.headers["X-Anonymous-Cart-Token"] = cart.anonymous_token

    return await clear_cart(db, cart=cart)


@cart_router.post(
    "/merge",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Merge Anonymous Guest Cart into Customer Account",
)
async def merge_cart_endpoint(
    req: MergeCartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """
    Merge items from an anonymous session cart into the customer's permanent cart upon login.
    """
    return await merge_guest_cart_into_user_cart(
        db,
        user=current_user,
        anonymous_token=req.anonymous_token,
    )


# ===========================================================================
# Wishlist Endpoints
# ===========================================================================

@wishlist_router.get(
    "",
    response_model=WishlistResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Customer Wishlist",
)
async def get_wishlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WishlistResponse:
    """Retrieve bookmarked products for the authenticated customer."""
    wishlist = await get_or_create_wishlist(db, current_user)
    from app.modules.cart.service import build_wishlist_response
    return await build_wishlist_response(db, wishlist)


@wishlist_router.post(
    "/items",
    response_model=WishlistResponse,
    status_code=status.HTTP_200_OK,
    summary="Add Product to Wishlist",
)
async def add_to_wishlist_endpoint(
    req: AddToWishlistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WishlistResponse:
    """Bookmark a catalog product to customer wishlist."""
    return await add_product_to_wishlist(
        db,
        user=current_user,
        product_id=req.product_id,
    )


@wishlist_router.delete(
    "/items/{product_id}",
    response_model=WishlistResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove Product from Wishlist",
)
async def remove_from_wishlist_endpoint(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WishlistResponse:
    """Remove a bookmarked product from customer wishlist."""
    return await remove_product_from_wishlist(
        db,
        user=current_user,
        product_id=product_id,
    )


@wishlist_router.delete(
    "",
    response_model=WishlistResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear Wishlist",
)
async def clear_wishlist_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WishlistResponse:
    """Remove all items from customer wishlist."""
    return await clear_customer_wishlist(db, user=current_user)
