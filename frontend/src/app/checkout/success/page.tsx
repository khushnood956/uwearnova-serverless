"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Check, Truck, ArrowRight, ShieldCheck, Package, ExternalLink } from "lucide-react";
import { formatPKR, BRAND_CONFIG } from "@/lib/brand";
import { ordersApi, OrderResponse } from "@/lib/api/orders";

function SuccessContent() {
  const searchParams = useSearchParams();
  const orderNumber = searchParams.get("order");

  const [order, setOrder] = React.useState<OrderResponse | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (orderNumber) {
      ordersApi.getOrder(orderNumber)
        .then((res) => {
          setOrder(res);
        })
        .catch((err) => {
          console.warn("Could not fetch order from backend:", err);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, [orderNumber]);

  return (
    <div className="container-site max-w-3xl py-12 px-4 sm:px-6">
      <div className="p-8 sm:p-12 rounded-2xl bg-ivory-light border border-hairline shadow-card space-y-8">
        {/* Header Icon & Title */}
        <div className="text-center space-y-3">
          <div className="w-14 h-14 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center justify-center mx-auto">
            <Check className="w-6 h-6" />
          </div>

          <span className="text-xs font-semibold tracking-[0.2em] uppercase text-champagne-dark block">
            Order Confirmed & Placed
          </span>

          <h1 className="font-serif text-3xl sm:text-4xl font-medium text-obsidian tracking-tight">
            Thank You for Shopping with {BRAND_CONFIG.name}
          </h1>

          <p className="text-xs sm:text-sm text-obsidian-600 font-light max-w-md mx-auto leading-relaxed">
            Your order has been recorded in our fulfillment ledger. A confirmation has been transmitted for preparation at our atelier.
          </p>
        </div>

        {/* Order Details Card */}
        {order ? (
          <div className="space-y-6">
            {/* Top Snapshot */}
            <div className="p-5 rounded-xl bg-ivory border border-hairline grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <span className="text-obsidian-400 uppercase text-[10px] font-semibold block">Order Reference</span>
                <strong className="font-serif text-sm font-semibold text-obsidian mt-0.5 block font-mono">
                  {order.order_number}
                </strong>
              </div>

              <div>
                <span className="text-obsidian-400 uppercase text-[10px] font-semibold block">Date Placed</span>
                <span className="font-medium text-obsidian mt-0.5 block">
                  {new Date(order.placed_at || order.created_at).toLocaleDateString()}
                </span>
              </div>

              <div>
                <span className="text-obsidian-400 uppercase text-[10px] font-semibold block">Order Status</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark mt-1 inline-block">
                  {order.status}
                </span>
              </div>

              <div>
                <span className="text-obsidian-400 uppercase text-[10px] font-semibold block">Payment Status</span>
                <span className="capitalize font-medium text-obsidian mt-0.5 block">
                  {order.payment_method === "cod" ? "COD (Unpaid until delivery)" : order.payment_status}
                </span>
              </div>
            </div>

            {/* Products List */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-obsidian">
                Purchased Pieces ({order.items.length})
              </h3>
              <div className="divide-y divide-hairline border border-hairline rounded-xl overflow-hidden bg-ivory text-xs">
                {order.items.map((item) => (
                  <div key={item.id} className="p-3.5 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-obsidian">{item.product_name}</p>
                      <p className="text-[11px] text-obsidian-500 font-light mt-0.5">
                        SKU: {item.sku} • Size: {item.size} • Color: {item.color} • Qty: {item.quantity}
                      </p>
                    </div>
                    <span className="font-mono font-medium text-obsidian">
                      {formatPKR(Number(item.line_total))}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Delivery Address & Financial Breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              {/* Shipping Address Snapshot */}
              <div className="p-4 rounded-xl bg-ivory border border-hairline space-y-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-obsidian-400">
                  Delivery Destination
                </span>
                <p className="font-medium text-obsidian text-sm pt-0.5">{order.shipping_address.full_name}</p>
                <p className="text-obsidian-600">{order.shipping_address.address_line_1}</p>
                {order.shipping_address.address_line_2 && (
                  <p className="text-obsidian-500">{order.shipping_address.address_line_2}</p>
                )}
                <p className="text-obsidian-600">
                  {order.shipping_address.city}, Pakistan {order.shipping_address.postal_code || ""}
                </p>
                <p className="text-obsidian-500 pt-1 font-mono">Mobile: {order.shipping_address.phone}</p>
              </div>

              {/* Financial Totals */}
              <div className="p-4 rounded-xl bg-ivory-sand/60 border border-hairline space-y-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-obsidian-400">
                  Financial Summary
                </span>
                <div className="space-y-1.5 pt-1">
                  <div className="flex justify-between text-obsidian-600 font-light">
                    <span>Subtotal</span>
                    <span className="font-mono">{formatPKR(Number(order.subtotal))}</span>
                  </div>
                  {Number(order.discount_total) > 0 && (
                    <div className="flex justify-between text-emerald-700">
                      <span>Discount</span>
                      <span className="font-mono">-{formatPKR(Number(order.discount_total))}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-obsidian-600 font-light">
                    <span>Shipping ({order.shipping_method_name || "Nationwide"})</span>
                    <span className="font-mono">
                      {Number(order.shipping_total) === 0 ? "FREE" : formatPKR(Number(order.shipping_total))}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm font-serif font-semibold text-obsidian border-t border-hairline pt-2">
                    <span>Total Amount</span>
                    <span className="font-mono text-base">{formatPKR(Number(order.grand_total))}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : loading ? (
          <div className="py-12 text-center text-xs text-obsidian-500">
            <div className="w-6 h-6 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <span>Fetching verified order receipt...</span>
          </div>
        ) : (
          <div className="p-6 rounded-xl bg-ivory border border-hairline text-center text-xs text-obsidian-600 space-y-1">
            <p className="font-semibold text-obsidian">Order Reference: {orderNumber || "UNV-PENDING"}</p>
            <p className="font-light">Your order has been recorded. Check your registered email for updates.</p>
          </div>
        )}

        {/* Courier Dispatch Commitment Notice */}
        <div className="p-4 rounded-xl bg-ivory border border-hairline flex items-start gap-3 text-xs text-obsidian-600">
          <Truck className="w-5 h-5 text-champagne-dark shrink-0 mt-0.5" />
          <div className="space-y-0.5 font-light">
            <p className="font-medium text-obsidian">Estimated Transit Timeline: 2–4 Business Days</p>
            <p>
              Consignment dispatch numbers will be messaged via SMS upon warehouse handover to partner couriers (Trax / Leopards / TCS).
            </p>
          </div>
        </div>

        {/* Actions Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-hairline">
          <Link
            href="/account?tab=orders"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-5 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
          >
            <span>Track in Account Portal</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>

          <Link
            href="/collections/all"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-5 py-2.5 rounded-button border border-hairline text-obsidian text-xs font-medium hover:bg-ivory-sand transition-colors"
          >
            <span>Continue Shopping</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function CheckoutSuccessPage() {
  return (
    <main className="flex-1 pb-20 bg-ivory">
      <React.Suspense
        fallback={
          <div className="py-20 text-center text-xs text-obsidian-500">
            <div className="w-8 h-8 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p>Loading confirmation...</p>
          </div>
        }
      >
        <SuccessContent />
      </React.Suspense>
    </main>
  );
}
