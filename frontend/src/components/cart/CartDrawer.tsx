"use client";

import * as React from "react";
import Link from "next/link";
import { X, ShoppingBag, ArrowRight, Truck } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { formatPKR } from "@/lib/brand";
import { Button } from "@/components/ui/Button";
import { CartItemRow } from "./CartItemRow";

export function CartDrawer() {
  const {
    items,
    isCartDrawerOpen,
    closeCartDrawer,
    removeItem,
    updateQuantity,
    totalItems,
    subtotal,
    isFreeShipping,
    amountNeededForFreeShipping,
    freeShippingThreshold,
  } = useCart();

  React.useEffect(() => {
    if (isCartDrawerOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isCartDrawerOpen]);

  if (!isCartDrawerOpen) return null;

  const progressRatio = Math.min(1, subtotal / freeShippingThreshold);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Shopping Bag"
      className="fixed inset-0 z-50 flex justify-end"
    >
      {/* Backdrop */}
      <div
        onClick={closeCartDrawer}
        className="fixed inset-0 bg-obsidian/60 backdrop-blur-xs transition-opacity duration-base ease-out"
      />

      {/* Drawer */}
      <div className="relative w-full max-w-md bg-ivory-light h-full shadow-card-hover flex flex-col z-10 overflow-hidden border-l border-hairline">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-hairline">
          <div className="flex items-center gap-2.5">
            <ShoppingBag className="w-5 h-5 text-obsidian" />
            <h2 className="font-serif text-xl font-medium text-obsidian tracking-tight">
              Shopping Bag ({totalItems})
            </h2>
          </div>
          <button
            onClick={closeCartDrawer}
            aria-label="Close bag"
            className="w-10 h-10 flex items-center justify-center text-obsidian-500 hover:text-obsidian rounded-button hover:bg-ivory-sand transition-colors duration-fast"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Free Shipping Progress Meter using scaleX (No layout-property width animation) */}
        <div className="px-6 py-3.5 bg-ivory-sand/60 border-b border-hairline text-xs">
          <div className="flex items-center gap-2 font-medium text-obsidian">
            <Truck className="w-4 h-4 text-champagne-dark shrink-0" />
            {isFreeShipping ? (
              <span className="text-success font-semibold">
                You&apos;ve unlocked Free Nationwide Delivery!
              </span>
            ) : (
              <span>
                Add{" "}
                <strong className="text-obsidian font-semibold">
                  {formatPKR(amountNeededForFreeShipping)}
                </strong>{" "}
                more to unlock Free Delivery
              </span>
            )}
          </div>
          <div className="w-full bg-obsidian/10 h-1.5 rounded-button mt-2 overflow-hidden relative">
            <div
              className="absolute inset-0 bg-champagne-dark rounded-button origin-left transition-transform duration-base ease-out"
              style={{ transform: `scaleX(${progressRatio})` }}
            />
          </div>
        </div>

        {/* Items List */}
        <div className="flex-1 overflow-y-auto px-6 py-2 divide-y divide-hairline">
          {items.length === 0 ? (
            <div className="py-20 text-center space-y-4">
              <div className="w-14 h-14 rounded-button bg-ivory-sand flex items-center justify-center mx-auto text-obsidian-400">
                <ShoppingBag className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="font-serif text-lg font-medium text-obsidian">
                  Your bag is empty
                </h3>
                <p className="text-xs text-obsidian-500 max-w-xs mx-auto font-light">
                  Explore our curated seasonal tailoring, essentials, and accessories.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={closeCartDrawer}
                className="mt-2"
              >
                Continue Shopping
              </Button>
            </div>
          ) : (
            items.map((item) => (
              <CartItemRow
                key={item.id}
                item={item}
                onUpdateQuantity={updateQuantity}
                onRemove={removeItem}
                onCloseDrawer={closeCartDrawer}
              />
            ))
          )}
        </div>

        {/* Footer Subtotal & Checkout CTA */}
        {items.length > 0 && (
          <div className="p-6 border-t border-hairline bg-ivory-light space-y-4">
            <div className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-obsidian-600 font-light">Subtotal</span>
                <span className="font-serif font-medium text-lg text-obsidian">
                  {formatPKR(subtotal)}
                </span>
              </div>
              <p className="text-[11px] text-obsidian-500 font-light">
                Taxes & standard nationwide shipping calculated at checkout.
              </p>
            </div>

            <div className="space-y-2">
              <Link
                href="/checkout"
                onClick={closeCartDrawer}
                className="block w-full"
              >
                <Button size="lg" variant="primary" className="w-full">
                  <span>Proceed to Checkout</span>
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>

              <Link
                href="/cart"
                onClick={closeCartDrawer}
                className="block text-center text-xs font-semibold text-obsidian-600 hover:text-obsidian py-1 uppercase tracking-wider"
              >
                View Detailed Shopping Bag
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
