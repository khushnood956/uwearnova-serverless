"use client";

import * as React from "react";
import { Product, ProductVariant } from "@/types/product";
import { CartItem } from "@/types/cart";
import { BRAND_CONFIG } from "@/lib/brand";
import { cartApi } from "@/lib/api/cart";
import { CartResponse } from "@/lib/api/types";
import { mapBackendCartItem } from "@/lib/api/adapters";

interface CartContextType {
  items: CartItem[];
  addItem: (product: Product, variant: ProductVariant, quantity?: number) => Promise<void>;
  removeItem: (itemId: string) => Promise<void>;
  updateQuantity: (itemId: string, quantity: number) => Promise<void>;
  clearCart: () => Promise<void>;
  refreshCart: () => Promise<void>;
  totalItems: number;
  subtotal: number;
  freeShippingThreshold: number;
  amountNeededForFreeShipping: number;
  isFreeShipping: boolean;
  isCartDrawerOpen: boolean;
  openCartDrawer: () => void;
  closeCartDrawer: () => void;
  isLoading: boolean;
}

const CartContext = React.createContext<CartContextType | undefined>(undefined);

const CART_STORAGE_KEY = "uwearnova_cart_v1";

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [serverCart, setServerCart] = React.useState<CartResponse | null>(null);
  const [localItems, setLocalItems] = React.useState<CartItem[]>([]);
  const [isCartDrawerOpen, setIsCartDrawerOpen] = React.useState(false);
  const [isHydrated, setIsHydrated] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);

  // Fetch server cart
  const refreshCart = React.useCallback(async () => {
    try {
      setIsLoading(true);
      const cart = await cartApi.getCart();
      setServerCart(cart);
    } catch (err) {
      console.warn("Backend cart unavailable, using local state:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // On mount: fetch active server cart, or fallback to local storage
  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(CART_STORAGE_KEY);
      if (stored) {
        setLocalItems(JSON.parse(stored));
      }
    } catch {
      // ignore
    } finally {
      setIsHydrated(true);
    }

    refreshCart();
  }, [refreshCart]);

  // Sync items
  const items: CartItem[] = React.useMemo(() => {
    if (serverCart && Array.isArray(serverCart.items)) {
      return serverCart.items.map(mapBackendCartItem);
    }
    return localItems;
  }, [serverCart, localItems]);

  // Persist local items if fallback
  React.useEffect(() => {
    if (!isHydrated) return;
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(localItems));
    } catch {
      // ignore
    }
  }, [localItems, isHydrated]);

  const addItem = React.useCallback(
    async (product: Product, variant: ProductVariant, quantity: number = 1) => {
      setIsCartDrawerOpen(true);

      // Attempt server add
      if (variant.id) {
        try {
          const updatedCart = await cartApi.addToCart(Number(variant.id), quantity);
          setServerCart(updatedCart);
          return;
        } catch (err) {
          console.warn("Failed to add to server cart, falling back to local:", err);
        }
      }

      // Local fallback
      const itemId = `${product.id}-${variant.sku}`;
      setLocalItems((prev) => {
        const existingIndex = prev.findIndex((i) => i.id === itemId);
        if (existingIndex > -1) {
          const updated = [...prev];
          const newQty = updated[existingIndex].quantity + quantity;
          updated[existingIndex] = {
            ...updated[existingIndex],
            quantity: Math.min(newQty, variant.inventoryCount || 99),
          };
          return updated;
        }
        return [...prev, { id: itemId, product, variant, quantity }];
      });
    },
    []
  );

  const removeItem = React.useCallback(
    async (itemId: string) => {
      // Check if backend item
      const item = items.find((i) => i.id === itemId);
      if (item?.rawId) {
        try {
          const updated = await cartApi.removeCartItem(item.rawId);
          setServerCart(updated);
          return;
        } catch (err) {
          console.warn("Failed to remove item on server, updating local:", err);
        }
      }

      setLocalItems((prev) => prev.filter((i) => i.id !== itemId));
      if (serverCart) {
        setServerCart((prev) =>
          prev ? { ...prev, items: prev.items.filter((i) => String(i.id) !== itemId) } : null
        );
      }
    },
    [items, serverCart]
  );

  const updateQuantity = React.useCallback(
    async (itemId: string, quantity: number) => {
      const item = items.find((i) => i.id === itemId);
      if (item?.rawId) {
        try {
          const updated = await cartApi.updateCartItem(item.rawId, quantity);
          setServerCart(updated);
          return;
        } catch (err) {
          console.warn("Failed to update item quantity on server, updating local:", err);
        }
      }

      if (quantity <= 0) {
        setLocalItems((prev) => prev.filter((i) => i.id !== itemId));
        return;
      }

      setLocalItems((prev) =>
        prev.map((i) =>
          i.id === itemId
            ? {
                ...i,
                quantity: Math.min(quantity, i.variant.inventoryCount || 99),
              }
            : i
        )
      );
    },
    [items]
  );

  const clearCart = React.useCallback(async () => {
    try {
      await cartApi.clearCart();
    } catch {
      // ignore
    }
    setServerCart(null);
    setLocalItems([]);
  }, []);

  const totalItems = React.useMemo(() => {
    if (serverCart) return serverCart.total_items;
    return items.reduce((sum, item) => sum + item.quantity, 0);
  }, [serverCart, items]);

  const subtotal = React.useMemo(() => {
    if (serverCart) return Number(serverCart.subtotal);
    return items.reduce(
      (sum, item) => sum + item.product.price * item.quantity,
      0
    );
  }, [serverCart, items]);

  const freeShippingThreshold = serverCart
    ? Number(serverCart.free_shipping_threshold)
    : BRAND_CONFIG.freeShippingThreshold;

  const isFreeShipping = serverCart
    ? serverCart.is_free_shipping
    : subtotal >= freeShippingThreshold;

  const amountNeededForFreeShipping = serverCart
    ? Number((serverCart as any).amount_needed_for_free_shipping ?? (serverCart as any).amount_for_free_shipping ?? 0)
    : Math.max(0, freeShippingThreshold - subtotal);

  const value = {
    items,
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    refreshCart,
    totalItems,
    subtotal,
    freeShippingThreshold,
    amountNeededForFreeShipping,
    isFreeShipping,
    isCartDrawerOpen,
    openCartDrawer: () => setIsCartDrawerOpen(true),
    closeCartDrawer: () => setIsCartDrawerOpen(false),
    isLoading,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = React.useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}
