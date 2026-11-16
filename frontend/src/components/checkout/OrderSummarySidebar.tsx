"use client";

import * as React from "react";
import Image from "next/image";
import { ShieldCheck } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { formatPKR } from "@/lib/brand";

export function OrderSummarySidebar() {
  const { items, subtotal, isFreeShipping, totalItems, deliveryFee, shippingFee } = useCart();
  const fee = isFreeShipping ? 0 : deliveryFee;
  const grandTotal = subtotal + fee;

  return (
    <div className="p-6 sm:p-8 rounded-card bg-ivory-sand border border-hairline shadow-subtle space-y-6">
      <h2 className="font-serif text-xl font-medium text-obsidian border-b border-hairline pb-4">
        Order Summary ({totalItems} {totalItems === 1 ? "Piece" : "Pieces"})
      </h2>

      {/* Item List */}
      <div className="space-y-3 max-h-72 overflow-y-auto pr-1 divide-y divide-hairline">
        {items.map((item) => (
          <div key={item.id} className="pt-3 first:pt-0 flex gap-3 text-xs">
            <div className="relative aspect-[4/5] w-14 rounded-image overflow-hidden bg-ivory shrink-0 border border-hairline">
              <Image
                src={item.product.images[0]}
                alt={item.product.name}
                fill
                sizes="56px"
                className="object-cover object-center"
              />
              <span className="absolute top-1 right-1 px-1.5 py-0.2 rounded-button text-[9px] font-bold bg-obsidian text-ivory">
                {item.quantity}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-serif font-medium text-obsidian truncate text-sm">
                {item.product.name}
              </h4>
              <p className="text-obsidian-500 font-light mt-0.5">
                {item.variant.size} • {item.variant.color}
              </p>
              <p className="font-semibold text-obsidian mt-1">
                {formatPKR(item.product.price * item.quantity)}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Cost Breakdown */}
      <div className="space-y-2.5 border-t border-hairline pt-4 text-xs sm:text-sm">
        <div className="flex justify-between text-obsidian-600 font-light">
          <span>Subtotal</span>
          <span className="font-medium text-obsidian">{formatPKR(subtotal)}</span>
        </div>
        <div className="flex justify-between text-obsidian-600 font-light">
          <span>Nationwide Shipping</span>
          <span className="font-medium text-obsidian">
            {isFreeShipping ? (
              <span className="text-success font-semibold uppercase text-xs">
                Free
              </span>
            ) : (
              formatPKR(fee)
            )}
          </span>
        </div>
        <div className="flex justify-between font-serif font-semibold text-base text-obsidian border-t border-hairline pt-3">
          <span>Estimated Total</span>
          <span className="text-xl font-medium">{formatPKR(grandTotal)}</span>
        </div>
      </div>

      {/* Assurance */}
      <div className="pt-2 border-t border-hairline flex items-center gap-2 text-xs text-obsidian-500 font-light">
        <ShieldCheck className="w-4 h-4 text-champagne-dark shrink-0" />
        <span>Verified Courier Fulfillment across Pakistan</span>
      </div>
    </div>
  );
}
