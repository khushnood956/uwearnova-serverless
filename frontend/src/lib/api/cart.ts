/**
 * Storefront Shopping Cart & Wishlist API (Supabase Backend)
 * Direct database querying with RLS and PostgreSQL RPC for guest cart merge.
 */

import { supabase } from "@/lib/supabase/client";
import { getAnonymousCartToken, setAnonymousCartToken } from "./client";
import {
  CartItemResponse,
  CartResponse,
  WishlistItemResponse,
  WishlistResponse,
} from "./types";
import { settingsApi } from "./settings";

const FREE_SHIPPING_THRESHOLD = 5000.00;
const STANDARD_SHIPPING_FEE = 350.00;

async function getOrCreateActiveCartId(): Promise<number> {
  const { data: { user } } = await supabase.auth.getUser();

  if (user) {
    // 1. Look up domain user ID
    const { data: domainUser } = await supabase
      .from("users")
      .select("id")
      .eq("auth_user_id", user.id)
      .maybeSingle();

    const domainUserId = domainUser?.id;

    if (domainUserId) {
      // Find or create customer cart
      const { data: existingCart } = await supabase
        .from("carts")
        .select("id")
        .eq("user_id", domainUserId)
        .maybeSingle();

      if (existingCart) return existingCart.id;

      const { data: newCart, error } = await supabase
        .from("carts")
        .insert({ user_id: domainUserId })
        .select("id")
        .single();

      if (!error && newCart) return newCart.id;
    }
  }

  // 2. Guest User with anonymous cart token
  let anonToken = getAnonymousCartToken();
  if (!anonToken) {
    anonToken = "anon_" + Math.random().toString(36).substring(2) + Date.now().toString(36);
    setAnonymousCartToken(anonToken);
  }

  const { data: existingAnonCart } = await supabase
    .from("carts")
    .select("id")
    .eq("anonymous_token", anonToken)
    .maybeSingle();

  if (existingAnonCart) return existingAnonCart.id;

  const { data: newAnonCart, error: anonError } = await supabase
    .from("carts")
    .insert({ anonymous_token: anonToken })
    .select("id")
    .single();

  if (anonError || !newAnonCart) {
    throw new Error(anonError?.message || "Failed to establish active shopping cart session.");
  }

  return newAnonCart.id;
}

export const cartApi = {
  /**
   * Retrieve active cart with server-verified prices and free delivery calculations.
   */
  async getCart(): Promise<CartResponse> {
    try {
      const cartId = await getOrCreateActiveCartId();

      const { data: items, error } = await supabase
        .from("cart_items")
        .select(`
          id,
          variant_id,
          quantity,
          variant:product_variants (
            id,
            sku,
            size,
            color_name,
            price,
            inventory_count,
            product:products (
              id,
              name,
              slug,
              price,
              images:product_images (
                image_url,
                is_primary
              )
            )
          )
        `)
        .eq("cart_id", cartId);

      if (error) {
        console.warn("Failed to load cart items from Supabase:", error.message);
      }

      const cartItems: CartItemResponse[] = (items || []).map((ci: any) => {
        const v = ci.variant;
        const p = v?.product;
        const unitPrice = Number(v?.price ?? p?.price ?? 0);
        const subtotal = unitPrice * ci.quantity;
        const primaryImg = (p?.images || []).find((img: any) => img.is_primary) || p?.images?.[0];

        return {
          id: ci.id,
          variant_id: ci.variant_id,
          product_id: p?.id || 0,
          product_name: p?.name || "Product",
          product_slug: p?.slug || "",
          sku: v?.sku || "",
          size: v?.size || "",
          color: v?.color_name || "",
          image_url: primaryImg?.image_url || null,
          unit_price: unitPrice,
          quantity: ci.quantity,
          line_subtotal: subtotal,
          in_stock: (v?.inventory_count ?? 0) >= ci.quantity,
          available_inventory: v?.inventory_count ?? 0,
          is_price_changed: false,
        };
      });

      let dynamicThreshold = FREE_SHIPPING_THRESHOLD;
      let dynamicShippingFee = STANDARD_SHIPPING_FEE;
      try {
        const storeSettings = await settingsApi.getSettings();
        if (storeSettings.free_shipping_threshold !== undefined) {
          dynamicThreshold = Number(storeSettings.free_shipping_threshold);
        }
        if (storeSettings.delivery_fee !== undefined) {
          dynamicShippingFee = Number(storeSettings.delivery_fee);
        }
      } catch {
        // fallback
      }

      const totalItems = cartItems.reduce((acc, item) => acc + item.quantity, 0);
      const subtotal = cartItems.reduce((acc, item) => acc + Number(item.line_subtotal), 0);
      const isFreeShipping = subtotal >= dynamicThreshold;
      const shippingEstimate = totalItems === 0 || isFreeShipping ? 0.00 : dynamicShippingFee;
      const grandTotal = subtotal + shippingEstimate;
      const amountForFreeShipping = Math.max(0, dynamicThreshold - subtotal);

      return {
        id: cartId,
        items: cartItems,
        total_items: totalItems,
        subtotal,
        discount_total: 0,
        shipping_estimate: shippingEstimate,
        grand_total: grandTotal,
        is_free_shipping: isFreeShipping,
        amount_for_free_shipping: amountForFreeShipping,
        free_shipping_threshold: dynamicThreshold,
        currency: "PKR",
      };
    } catch (e: any) {
      // Fallback empty cart
      return {
        id: 0,
        items: [],
        total_items: 0,
        subtotal: 0,
        discount_total: 0,
        shipping_estimate: 0,
        grand_total: 0,
        is_free_shipping: false,
        amount_for_free_shipping: FREE_SHIPPING_THRESHOLD,
        free_shipping_threshold: FREE_SHIPPING_THRESHOLD,
        currency: "PKR",
      };
    }
  },

  /**
   * Add a product variant to the active cart.
   */
  async addToCart(variantId: number, quantity: number = 1): Promise<CartResponse> {
    const cartId = await getOrCreateActiveCartId();

    const { error } = await supabase
      .from("cart_items")
      .upsert(
        { cart_id: cartId, variant_id: variantId, quantity },
        { onConflict: "cart_id,variant_id" }
      );

    if (error) {
      throw new Error(`Failed to add item to cart: ${error.message}`);
    }

    return await cartApi.getCart();
  },

  /**
   * Update line-item quantity in cart.
   */
  async updateCartItem(itemId: number, quantity: number): Promise<CartResponse> {
    if (quantity <= 0) {
      return await cartApi.removeCartItem(itemId);
    }

    const { error } = await supabase
      .from("cart_items")
      .update({ quantity })
      .eq("id", itemId);

    if (error) {
      throw new Error(`Failed to update item quantity: ${error.message}`);
    }

    return await cartApi.getCart();
  },

  /**
   * Remove item from cart.
   */
  async removeCartItem(itemId: number): Promise<CartResponse> {
    const { error } = await supabase
      .from("cart_items")
      .delete()
      .eq("id", itemId);

    if (error) {
      throw new Error(`Failed to remove item: ${error.message}`);
    }

    return await cartApi.getCart();
  },

  /**
   * Clear all items from cart.
   */
  async clearCart(): Promise<CartResponse> {
    try {
      const cartId = await getOrCreateActiveCartId();
      await supabase.from("cart_items").delete().eq("cart_id", cartId);
    } catch {
      // ignore
    }
    return await cartApi.getCart();
  },

  /**
   * Merge anonymous guest cart into customer account on login.
   */
  async mergeCart(anonymousToken: string): Promise<CartResponse> {
    const { error } = await supabase.rpc("merge_guest_cart", {
      p_anon_token: anonymousToken,
    });

    if (error) {
      console.warn("Cart merge RPC warning:", error.message);
    }

    return await cartApi.getCart();
  },

  // -------------------------------------------------------------------------
  // Wishlist API
  // -------------------------------------------------------------------------

  async getWishlist(): Promise<WishlistResponse> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return { id: 0, user_id: 0, total_items: 0, items: [] };

    const { data: domainUser } = await supabase
      .from("users")
      .select("id")
      .eq("auth_user_id", user.id)
      .maybeSingle();

    if (!domainUser) return { id: 0, user_id: 0, total_items: 0, items: [] };

    const { data: wishlist } = await supabase
      .from("wishlists")
      .select("id, wishlist_items(id, product_id, product:products(*, variants:product_variants(*), images:product_images(*)))")
      .eq("user_id", domainUser.id)
      .maybeSingle();

    const rawItems = wishlist?.wishlist_items || [];
    const items: WishlistItemResponse[] = rawItems.map((wi: any) => ({
      id: wi.id,
      product_id: wi.product_id,
      product: wi.product,
      created_at: new Date().toISOString(),
    }));

    return {
      id: wishlist?.id || 0,
      user_id: domainUser.id,
      total_items: items.length,
      items,
    };
  },

  async addToWishlist(productId: number): Promise<WishlistResponse> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("Must be logged in to modify wishlist.");

    const { data: domainUser } = await supabase
      .from("users")
      .select("id")
      .eq("auth_user_id", user.id)
      .maybeSingle();

    if (!domainUser) throw new Error("Domain user record not found.");

    // Get or create wishlist
    let { data: wishlist } = await supabase
      .from("wishlists")
      .select("id")
      .eq("user_id", domainUser.id)
      .maybeSingle();

    if (!wishlist) {
      const { data: newW } = await supabase
        .from("wishlists")
        .insert({ user_id: domainUser.id })
        .select("id")
        .single();
      wishlist = newW;
    }

    if (wishlist) {
      await supabase
        .from("wishlist_items")
        .upsert({ wishlist_id: wishlist.id, product_id: productId }, { onConflict: "wishlist_id,product_id" });
    }

    return await cartApi.getWishlist();
  },

  async removeFromWishlist(productId: number): Promise<WishlistResponse> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return await cartApi.getWishlist();

    const { data: domainUser } = await supabase
      .from("users")
      .select("id")
      .eq("auth_user_id", user.id)
      .maybeSingle();

    if (domainUser) {
      const { data: wishlist } = await supabase
        .from("wishlists")
        .select("id")
        .eq("user_id", domainUser.id)
        .maybeSingle();

      if (wishlist) {
        await supabase
          .from("wishlist_items")
          .delete()
          .eq("wishlist_id", wishlist.id)
          .eq("product_id", productId);
      }
    }

    return await cartApi.getWishlist();
  },

  async clearWishlist(): Promise<WishlistResponse> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return { id: 0, user_id: 0, total_items: 0, items: [] };

    const { data: domainUser } = await supabase
      .from("users")
      .select("id")
      .eq("auth_user_id", user.id)
      .maybeSingle();

    if (domainUser) {
      const { data: wishlist } = await supabase
        .from("wishlists")
        .select("id")
        .eq("user_id", domainUser.id)
        .maybeSingle();

      if (wishlist) {
        await supabase.from("wishlist_items").delete().eq("wishlist_id", wishlist.id);
      }
    }

    return await cartApi.getWishlist();
  },
};
