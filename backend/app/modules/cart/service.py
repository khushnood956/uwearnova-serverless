"""
Cart and Wishlist Service Layer (M10)
Handles server-side cart calculation, authoritative pricing from catalogue,
stock availability validation, guest cart merging, and customer wishlists.
"""

from decimal import Decimal
import secrets
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import User
from app.modules.catalog.models import Product, ProductImage, ProductVariant
from app.modules.cart.models import Cart, CartItem, Wishlist, WishlistItem
from app.modules.cart.schemas import (
    CartItemResponse,
    CartResponse,
    WishlistItemResponse,
    WishlistResponse,
)

FREE_SHIPPING_THRESHOLD_PKR = Decimal("15000.00")


# ===========================================================================
# Cart Helper & Core Functions
# ===========================================================================

async def get_or_create_cart(
    db: AsyncSession,
    user: Optional[User] = None,
    anonymous_token: Optional[str] = None,
) -> Tuple[Cart, bool]:
    """
    Retrieve active cart for customer or guest visitor.
    If none exists, initializes an active cart. Returns (cart, is_new).
    """
    if user is not None:
        stmt = (
            select(Cart)
            .where(Cart.user_id == user.id, Cart.status == "active")
            .order_by(Cart.created_at.desc())
        )
        res = await db.execute(stmt)
        cart = res.scalar_one_or_none()
        if cart is not None:
            return cart, False

        cart = Cart(user_id=user.id, status="active")
        db.add(cart)
        await db.flush()
        await db.refresh(cart)
        return cart, True

    if anonymous_token:
        stmt = (
            select(Cart)
            .where(Cart.anonymous_token == anonymous_token, Cart.status == "active")
            .order_by(Cart.created_at.desc())
        )
        res = await db.execute(stmt)
        cart = res.scalar_one_or_none()
        if cart is not None:
            return cart, False

    token = anonymous_token or secrets.token_urlsafe(32)
    cart = Cart(anonymous_token=token, status="active")
    db.add(cart)
    await db.flush()
    await db.refresh(cart)
    return cart, True


async def build_cart_response(db: AsyncSession, cart: Cart) -> CartResponse:
    """
    Assemble authoritative CartResponse by recalculating line item prices,
    validating stock availability, and evaluating free-shipping thresholds.
    Never trusts client prices or totals.
    """
    stmt = (
        select(CartItem)
        .where(CartItem.cart_id == cart.id)
        .order_by(CartItem.created_at.asc())
    )
    res = await db.execute(stmt)
    cart_items = res.scalars().all()

    items_response: List[CartItemResponse] = []
    total_items = 0
    subtotal = Decimal("0.00")

    for item in cart_items:
        # Fetch variant with product and product gallery images
        v_stmt = (
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.product).selectinload(Product.images)
            )
            .where(ProductVariant.id == item.variant_id)
        )
        v_res = await db.execute(v_stmt)
        variant = v_res.scalar_one_or_none()

        if not variant or not variant.product:
            # Variant or product was purged from catalog
            items_response.append(
                CartItemResponse(
                    id=item.id,
                    variant_id=item.variant_id,
                    product_id=0,
                    product_name="Unavailable Product",
                    product_slug="",
                    variant_sku=f"SKU-{item.variant_id}",
                    size="",
                    color_name="",
                    color_hex=None,
                    image_url=None,
                    unit_price=Decimal("0.00"),
                    original_price=None,
                    quantity=item.quantity,
                    line_total=Decimal("0.00"),
                    available_stock=0,
                    is_available=False,
                    availability_message="This item is no longer available in the catalogue",
                )
            )
            total_items += item.quantity
            continue

        product = variant.product

        # Resolve primary image
        primary_img = next(
            (img.image_url for img in product.images if img.is_primary),
            product.images[0].image_url if product.images else None,
        )

        # Authoritative price resolution
        unit_price = variant.price if variant.price is not None else product.price
        original_price = (
            variant.compare_at_price
            if variant.compare_at_price is not None
            else product.original_price
        )
        line_total = unit_price * item.quantity

        # Availability and stock evaluation
        available_stock = max(0, variant.inventory_count)
        is_available = True
        avail_msg: Optional[str] = None

        if product.status != "active" or not variant.is_active:
            is_available = False
            avail_msg = "Product is currently inactive"
        elif not variant.in_stock or available_stock <= 0:
            is_available = False
            avail_msg = "Item is currently out of stock"
        elif item.quantity > available_stock:
            is_available = False
            avail_msg = f"Only {available_stock} units available in stock"

        items_response.append(
            CartItemResponse(
                id=item.id,
                variant_id=variant.id,
                product_id=product.id,
                product_name=product.name,
                product_slug=product.slug,
                variant_sku=variant.sku,
                size=variant.size,
                color_name=variant.color_name,
                color_hex=variant.color_hex,
                image_url=primary_img,
                unit_price=unit_price,
                original_price=original_price,
                quantity=item.quantity,
                line_total=line_total,
                available_stock=available_stock,
                is_available=is_available,
                availability_message=avail_msg,
            )
        )

        total_items += item.quantity
        if is_available:
            subtotal += line_total

    # Free shipping evaluation
    threshold = FREE_SHIPPING_THRESHOLD_PKR
    is_free_shipping = subtotal >= threshold
    amount_needed = max(Decimal("0.00"), threshold - subtotal)

    return CartResponse(
        id=cart.id,
        user_id=cart.user_id,
        anonymous_token=cart.anonymous_token,
        status=cart.status,
        items=items_response,
        total_items=total_items,
        subtotal=subtotal,
        free_shipping_threshold=threshold,
        amount_needed_for_free_shipping=amount_needed,
        is_free_shipping=is_free_shipping,
        updated_at=cart.updated_at,
    )


async def add_item_to_cart(
    db: AsyncSession,
    cart: Cart,
    variant_id: int,
    quantity: int,
) -> CartResponse:
    """
    Add a product variant to the cart.
    Validates product active status and stock availability.
    """
    v_stmt = (
        select(ProductVariant)
        .options(selectinload(ProductVariant.product))
        .where(ProductVariant.id == variant_id)
    )
    v_res = await db.execute(v_stmt)
    variant = v_res.scalar_one_or_none()

    if not variant or not variant.product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found",
        )

    if variant.product.status != "active" or not variant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRODUCT_UNAVAILABLE: Product or variant is not active for purchase",
        )

    if not variant.in_stock or variant.inventory_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OUT_OF_STOCK: Product variant is currently out of stock",
        )

    # Check if variant already exists in cart
    stmt = select(CartItem).where(
        CartItem.cart_id == cart.id,
        CartItem.variant_id == variant_id,
    )
    res = await db.execute(stmt)
    existing_item = res.scalar_one_or_none()

    if existing_item:
        new_quantity = existing_item.quantity + quantity
        existing_item.quantity = min(new_quantity, 99)
    else:
        new_item = CartItem(
            cart_id=cart.id,
            variant_id=variant_id,
            quantity=min(quantity, 99),
        )
        db.add(new_item)

    await db.flush()
    await db.refresh(cart)
    return await build_cart_response(db, cart)


async def update_cart_item_quantity(
    db: AsyncSession,
    cart: Cart,
    item_id: int,
    quantity: int,
) -> CartResponse:
    """
    Update the quantity of an existing line item.
    Enforces ownership isolation (cannot modify item belonging to another cart).
    Setting quantity to 0 removes the item.
    """
    stmt = select(CartItem).where(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id,
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart line item not found",
        )

    if quantity <= 0:
        await db.delete(item)
    else:
        item.quantity = min(quantity, 99)

    await db.flush()
    await db.refresh(cart)
    return await build_cart_response(db, cart)


async def remove_cart_item(
    db: AsyncSession,
    cart: Cart,
    item_id: int,
) -> CartResponse:
    """
    Remove an item from the cart. Enforces cart ownership isolation.
    """
    stmt = select(CartItem).where(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id,
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart line item not found",
        )

    await db.delete(item)
    await db.flush()
    await db.refresh(cart)
    return await build_cart_response(db, cart)


async def clear_cart(
    db: AsyncSession,
    cart: Cart,
) -> CartResponse:
    """
    Remove all line items from the specified cart.
    """
    stmt = delete(CartItem).where(CartItem.cart_id == cart.id)
    await db.execute(stmt)
    await db.flush()
    await db.refresh(cart)
    return await build_cart_response(db, cart)


async def merge_guest_cart_into_user_cart(
    db: AsyncSession,
    user: User,
    anonymous_token: str,
) -> CartResponse:
    """
    Merge an anonymous guest cart into the authenticated customer cart upon login.
    Combines quantities for duplicate items and marks guest cart as 'merged'.
    """
    # 1. Fetch guest cart
    g_stmt = select(Cart).where(
        Cart.anonymous_token == anonymous_token,
        Cart.status == "active",
    )
    g_res = await db.execute(g_stmt)
    guest_cart = g_res.scalar_one_or_none()

    # 2. Get or create user cart
    user_cart, _ = await get_or_create_cart(db, user=user)

    if not guest_cart or guest_cart.id == user_cart.id:
        return await build_cart_response(db, user_cart)

    # 3. Retrieve guest items
    gi_stmt = select(CartItem).where(CartItem.cart_id == guest_cart.id)
    gi_res = await db.execute(gi_stmt)
    guest_items = gi_res.scalars().all()

    for gi in guest_items:
        # Check if user cart already has this variant
        ui_stmt = select(CartItem).where(
            CartItem.cart_id == user_cart.id,
            CartItem.variant_id == gi.variant_id,
        )
        ui_res = await db.execute(ui_stmt)
        user_item = ui_res.scalar_one_or_none()

        if user_item:
            user_item.quantity = min(user_item.quantity + gi.quantity, 99)
        else:
            new_item = CartItem(
                cart_id=user_cart.id,
                variant_id=gi.variant_id,
                quantity=min(gi.quantity, 99),
            )
            db.add(new_item)

    # 4. Mark guest cart as merged
    guest_cart.status = "merged"
    await db.flush()
    await db.refresh(user_cart)
    return await build_cart_response(db, user_cart)


# ===========================================================================
# Wishlist Functions
# ===========================================================================

async def get_or_create_wishlist(
    db: AsyncSession,
    user: User,
) -> Wishlist:
    """Retrieve or initialize customer wishlist."""
    stmt = select(Wishlist).where(Wishlist.user_id == user.id)
    res = await db.execute(stmt)
    wishlist = res.scalar_one_or_none()
    if wishlist:
        return wishlist

    wishlist = Wishlist(user_id=user.id)
    db.add(wishlist)
    await db.flush()
    await db.refresh(wishlist)
    return wishlist


async def build_wishlist_response(
    db: AsyncSession,
    wishlist: Wishlist,
) -> WishlistResponse:
    """Build enriched WishlistResponse with product metadata and primary thumbnails."""
    stmt = (
        select(WishlistItem)
        .options(
            selectinload(WishlistItem.product).selectinload(Product.images)
        )
        .where(WishlistItem.wishlist_id == wishlist.id)
        .order_by(WishlistItem.created_at.desc())
    )
    res = await db.execute(stmt)
    items = res.scalars().all()

    response_items: List[WishlistItemResponse] = []
    for wi in items:
        prod = wi.product
        if not prod:
            continue

        primary_img = next(
            (img.image_url for img in prod.images if img.is_primary),
            prod.images[0].image_url if prod.images else None,
        )

        response_items.append(
            WishlistItemResponse(
                id=wi.id,
                product_id=prod.id,
                product_name=prod.name,
                product_slug=prod.slug,
                price=prod.price,
                original_price=prod.original_price,
                image_url=primary_img,
                is_available=prod.status == "active",
                added_at=wi.created_at,
            )
        )

    return WishlistResponse(
        id=wishlist.id,
        user_id=wishlist.user_id,
        items=response_items,
        total_items=len(response_items),
        updated_at=wishlist.updated_at,
    )


async def add_product_to_wishlist(
    db: AsyncSession,
    user: User,
    product_id: int,
) -> WishlistResponse:
    """Add a product to the customer's wishlist."""
    # Verify product exists
    p_stmt = select(Product).where(Product.id == product_id)
    p_res = await db.execute(p_stmt)
    product = p_res.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    wishlist = await get_or_create_wishlist(db, user)

    # Check if already present
    wi_stmt = select(WishlistItem).where(
        WishlistItem.wishlist_id == wishlist.id,
        WishlistItem.product_id == product_id,
    )
    wi_res = await db.execute(wi_stmt)
    existing = wi_res.scalar_one_or_none()

    if not existing:
        item = WishlistItem(wishlist_id=wishlist.id, product_id=product_id)
        db.add(item)
        await db.flush()

    return await build_wishlist_response(db, wishlist)


async def remove_product_from_wishlist(
    db: AsyncSession,
    user: User,
    product_id: int,
) -> WishlistResponse:
    """Remove a product from customer's wishlist."""
    wishlist = await get_or_create_wishlist(db, user)

    wi_stmt = select(WishlistItem).where(
        WishlistItem.wishlist_id == wishlist.id,
        WishlistItem.product_id == product_id,
    )
    wi_res = await db.execute(wi_stmt)
    existing = wi_res.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.flush()

    return await build_wishlist_response(db, wishlist)


async def clear_customer_wishlist(
    db: AsyncSession,
    user: User,
) -> WishlistResponse:
    """Clear all items from customer's wishlist."""
    wishlist = await get_or_create_wishlist(db, user)
    stmt = delete(WishlistItem).where(WishlistItem.wishlist_id == wishlist.id)
    await db.execute(stmt)
    await db.flush()
    return await build_wishlist_response(db, wishlist)
