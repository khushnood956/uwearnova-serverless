"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, ShoppingBag } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import { OrderSummarySidebar } from "@/components/checkout/OrderSummarySidebar";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { Button } from "@/components/ui/Button";

export default function CheckoutPage() {
  const { items } = useCart();

  return (
    <main className="flex-1 pb-16 bg-ivory">
      <div className="container-site pt-4 pb-8">
        <Breadcrumbs
          items={[
            { label: "Shopping Bag", href: "/cart" },
            { label: "Secure Checkout" },
          ]}
        />

        <div className="flex items-center justify-between pb-6 border-b border-hairline mt-2">
          <div>
            <h1 className="font-serif text-3xl sm:text-4xl font-medium text-obsidian tracking-tight">
              Secure Checkout
            </h1>
            <p className="text-sm text-obsidian-600 mt-1 font-light">
              Review items, confirm nationwide delivery address, and place order.
            </p>
          </div>
          <Link
            href="/cart"
            className="text-xs sm:text-sm font-semibold tracking-wide uppercase text-obsidian hover:text-champagne-dark transition-colors duration-fast inline-flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Bag</span>
          </Link>
        </div>

        {items.length === 0 ? (
          <div className="py-24 text-center space-y-4 max-w-md mx-auto">
            <div className="w-16 h-16 rounded-button bg-ivory-sand flex items-center justify-center mx-auto text-obsidian-400">
              <ShoppingBag className="w-8 h-8" />
            </div>
            <h2 className="font-serif text-2xl font-medium text-obsidian">
              Your bag is empty
            </h2>
            <p className="text-sm text-obsidian-600 font-light">
              Add pieces to your shopping bag to test the simulated checkout.
            </p>
            <Link href="/collections/all" className="inline-block pt-2">
              <Button size="lg" variant="primary">
                Explore Collections
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 mt-8">
            <div className="lg:col-span-7">
              <CheckoutForm />
            </div>
            <div className="lg:col-span-5">
              <div className="sticky top-28">
                <OrderSummarySidebar />
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
