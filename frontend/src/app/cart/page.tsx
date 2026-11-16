"use client";

import * as React from "react";
import Link from "next/link";
import { ShoppingBag, ArrowRight, ArrowLeft, ShieldCheck, Truck, RefreshCw } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { formatPKR, BRAND_CONFIG } from "@/lib/brand";
import { Button } from "@/components/ui/Button";
import { CartItemRow } from "@/components/cart/CartItemRow";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { ProductGrid } from "@/components/product/ProductGrid";
import { getFeaturedProducts } from "@/data/products";

export default function CartPage() {
  const {
    items,
    removeItem,
    updateQuantity,
    totalItems,
    subtotal,
    isFreeShipping,
    amountNeededForFreeShipping,
    freeShippingThreshold,
  } = useCart();

  const progressRatio = Math.min(1, subtotal / freeShippingThreshold);
  const featured = getFeaturedProducts().slice(0, 4);

  return (
    <main className="flex-1 pb-16 bg-ivory">
      <div className="container-site pt-4 pb-8">
        <Breadcrumbs items={[{ label: "Shopping Bag" }]} />

        <div className="flex items-center justify-between pb-6 border-b border-hairline mt-2">
          <h1 className="font-serif text-3xl sm:text-4xl font-medium text-obsidian tracking-tight">
            Shopping Bag ({totalItems})
          </h1>
          <Link
            href="/collections/all"
            className="text-xs sm:text-sm font-semibold tracking-wide uppercase text-obsidian hover:text-champagne-dark transition-colors duration-fast inline-flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Continue Shopping</span>
          </Link>
        </div>

        {items.length === 0 ? (
          <div className="py-20 text-center space-y-6 max-w-lg mx-auto">
            <div className="w-16 h-16 rounded-button bg-ivory-sand flex items-center justify-center mx-auto text-obsidian-400 border border-hairline">
              <ShoppingBag className="w-7 h-7" />
            </div>
            <div className="space-y-2">
              <h2 className="font-serif text-2xl sm:text-3xl font-medium text-obsidian">
                Your Bag is Currently Empty
              </h2>
              <p className="text-sm text-obsidian-600 leading-relaxed font-light">
                Discover our latest contemporary Pakistani fashion, seasonal tailoring, and luxury footwear.
              </p>
            </div>
            <Link href="/collections/all" className="inline-block pt-2">
              <Button size="lg" variant="primary">
                Explore Collections
              </Button>
            </Link>

            {/* Curated You May Also Like on Empty State */}
            {featured.length > 0 && (
              <div className="pt-16 text-left border-t border-hairline">
                <h3 className="font-serif text-xl font-medium text-obsidian mb-6">
                  Curated Suggestions For You
                </h3>
                <ProductGrid products={featured} columns={4} />
              </div>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 mt-8">
            {/* Left: Item List */}
            <div className="lg:col-span-8 space-y-4">
              {/* Shipping Progress Banner with scaleX */}
              <div className="p-4 rounded-card bg-ivory-sand border border-hairline text-xs sm:text-sm space-y-2.5">
                <div className="flex items-center gap-2">
                  <Truck className="w-4 h-4 text-champagne-dark shrink-0" />
                  {isFreeShipping ? (
                    <span className="font-semibold text-success">
                      Your order qualifies for Free Nationwide Delivery across Pakistan!
                    </span>
                  ) : (
                    <span>
                      Add <strong>{formatPKR(amountNeededForFreeShipping)}</strong> more to unlock Free Nationwide Delivery.
                    </span>
                  )}
                </div>
                <div className="w-full bg-obsidian/10 h-1.5 rounded-button overflow-hidden relative">
                  <div
                    className="absolute inset-0 bg-champagne-dark rounded-button origin-left transition-transform duration-base ease-out"
                    style={{ transform: `scaleX(${progressRatio})` }}
                  />
                </div>
              </div>

              <div className="divide-y divide-hairline bg-ivory-light rounded-card p-6 border border-hairline">
                {items.map((item) => (
                  <CartItemRow
                    key={item.id}
                    item={item}
                    onUpdateQuantity={updateQuantity}
                    onRemove={removeItem}
                  />
                ))}
              </div>
            </div>

            {/* Right: Order Summary Card on Sand Panel */}
            <div className="lg:col-span-4">
              <div className="p-6 rounded-card bg-ivory-sand border border-hairline space-y-6 sticky top-28 shadow-subtle">
                <h2 className="font-serif text-xl font-medium text-obsidian">
                  Order Summary
                </h2>

                <div className="space-y-3 text-sm divide-y divide-hairline">
                  <div className="flex justify-between py-1 text-obsidian-700">
                    <span>Subtotal ({totalItems} pieces)</span>
                    <span className="font-medium text-obsidian">
                      {formatPKR(subtotal)}
                    </span>
                  </div>

                  <div className="flex justify-between py-2.5 text-obsidian-700">
                    <span>Nationwide Shipping</span>
                    <span className="font-medium text-obsidian">
                      {isFreeShipping ? (
                        <span className="text-success uppercase text-xs tracking-wider font-semibold">
                          Free
                        </span>
                      ) : (
                        formatPKR(350)
                      )}
                    </span>
                  </div>

                  <div className="flex justify-between pt-3 text-base font-semibold text-obsidian">
                    <span>Total Due</span>
                    <span className="font-serif text-xl font-medium">
                      {formatPKR(subtotal + (isFreeShipping ? 0 : 350))}
                    </span>
                  </div>
                </div>

                <Link href="/checkout" className="block w-full">
                  <Button size="lg" variant="primary" className="w-full">
                    <span>Proceed to Checkout</span>
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </Link>

                {/* Trust Badges */}
                <div className="pt-2 border-t border-hairline space-y-2 text-xs text-obsidian-600 font-light">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-champagne-dark shrink-0" />
                    <span>Cash on Delivery & Secure Local Options</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 text-champagne-dark shrink-0" />
                    <span>7-Day Complimentary Doorstep Exchanges</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
