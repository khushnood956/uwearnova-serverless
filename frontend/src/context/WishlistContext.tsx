"use client";

import * as React from "react";
import { cartApi } from "@/lib/api/cart";
import { useAuth } from "./AuthContext";

interface WishlistContextType {
  wishlistIds: string[];
  isWishlisted: (productId: string) => boolean;
  toggleWishlist: (productId: string) => Promise<void>;
  removeFromWishlist: (productId: string) => Promise<void>;
  clearWishlist: () => Promise<void>;
  totalWishlistCount: number;
  isLoading: boolean;
}

const WishlistContext = React.createContext<WishlistContextType | undefined>(
  undefined
);

const WISHLIST_STORAGE_KEY = "uwearnova_wishlist_v1";

export function WishlistProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [wishlistIds, setWishlistIds] = React.useState<string[]>([]);
  const [isHydrated, setIsHydrated] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);

  // Sync with backend if authenticated, or load from localStorage if guest
  React.useEffect(() => {
    // Skip if on admin/staff portal or user is privileged staff/admin to prevent useless latency
    if (typeof window !== "undefined") {
      const p = window.location.pathname;
      if (p.startsWith("/admin") || p.startsWith("/staff")) return;
      const role = localStorage.getItem("uwear_user_role");
      if (role === "admin" || role === "staff") return;
    }

    let mounted = true;
    if (isAuthenticated) {
      setIsLoading(true);
      cartApi.getWishlist()
        .then((res) => {
          if (mounted && res && Array.isArray(res.items)) {
            const ids = res.items.map((item) => String(item.product_id));
            setWishlistIds(ids);
          }
        })
        .catch((err) => {
          console.warn("Could not fetch server wishlist:", err);
        })
        .finally(() => {
          if (mounted) setIsLoading(false);
        });
    } else {
      try {
        const stored = localStorage.getItem(WISHLIST_STORAGE_KEY);
        if (stored) {
          setWishlistIds(JSON.parse(stored));
        }
      } catch {
        // ignore
      }
    }
    setIsHydrated(true);
    return () => {
      mounted = false;
    };
  }, [isAuthenticated]);

  // Save guest wishlist to localStorage
  React.useEffect(() => {
    if (!isHydrated || isAuthenticated) return;
    try {
      localStorage.setItem(WISHLIST_STORAGE_KEY, JSON.stringify(wishlistIds));
    } catch {
      // ignore
    }
  }, [wishlistIds, isHydrated, isAuthenticated]);

  const isWishlisted = React.useCallback(
    (productId: string) => wishlistIds.includes(String(productId)),
    [wishlistIds]
  );

  const toggleWishlist = React.useCallback(
    async (productId: string) => {
      const idStr = String(productId);
      const isCurrently = wishlistIds.includes(idStr);

      if (isAuthenticated) {
        const numId = Number(productId);
        if (!isNaN(numId)) {
          try {
            if (isCurrently) {
              const res = await cartApi.removeFromWishlist(numId);
              setWishlistIds(res.items.map((i) => String(i.product_id)));
              return;
            } else {
              const res = await cartApi.addToWishlist(numId);
              setWishlistIds(res.items.map((i) => String(i.product_id)));
              return;
            }
          } catch (err) {
            console.warn("Failed to update server wishlist, falling back:", err);
          }
        }
      }

      // Local / guest update
      setWishlistIds((prev) =>
        prev.includes(idStr)
          ? prev.filter((id) => id !== idStr)
          : [...prev, idStr]
      );
    },
    [wishlistIds, isAuthenticated]
  );

  const removeFromWishlist = React.useCallback(
    async (productId: string) => {
      const idStr = String(productId);
      if (isAuthenticated) {
        const numId = Number(productId);
        if (!isNaN(numId)) {
          try {
            const res = await cartApi.removeFromWishlist(numId);
            setWishlistIds(res.items.map((i) => String(i.product_id)));
            return;
          } catch (err) {
            console.warn("Failed to remove from server wishlist:", err);
          }
        }
      }
      setWishlistIds((prev) => prev.filter((id) => id !== idStr));
    },
    [isAuthenticated]
  );

  const clearWishlist = React.useCallback(async () => {
    if (isAuthenticated) {
      try {
        await cartApi.clearWishlist();
      } catch (err) {
        console.warn("Failed to clear server wishlist:", err);
      }
    }
    setWishlistIds([]);
  }, [isAuthenticated]);

  const value = {
    wishlistIds,
    isWishlisted,
    toggleWishlist,
    removeFromWishlist,
    clearWishlist,
    totalWishlistCount: wishlistIds.length,
    isLoading,
  };

  return (
    <WishlistContext.Provider value={value}>
      {children}
    </WishlistContext.Provider>
  );
}

export function useWishlist() {
  const context = React.useContext(WishlistContext);
  if (!context) {
    throw new Error("useWishlist must be used within a WishlistProvider");
  }
  return context;
}
