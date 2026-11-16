"use client";

import * as React from "react";
import Link from "next/link";
import { Heart, ArrowLeft } from "lucide-react";
import { useWishlist } from "@/context/WishlistContext";
import { PRODUCTS } from "@/data/products";
import { ProductCard } from "@/components/product/ProductCard";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { Button } from "@/components/ui/Button";
import { catalogApi } from "@/lib/api/catalog";
import { mapBackendProduct } from "@/lib/api/adapters";
import { Product } from "@/types/product";

export default function WishlistPage() {
  const { wishlistIds, removeFromWishlist } = useWishlist();
  const [backendProducts, setBackendProducts] = React.useState<Product[]>([]);

  React.useEffect(() => {
    let mounted = true;
    catalogApi.getProducts({ page_size: 100 })
      .then((res) => {
        if (mounted && res && Array.isArray(res.items)) {
          setBackendProducts(res.items.map(mapBackendProduct));
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  const wishlistedProducts = React.useMemo(() => {
    const allProducts = [...backendProducts, ...PRODUCTS];
    const seen = new Set<string>();
    const matched: Product[] = [];

    for (const p of allProducts) {
      if (wishlistIds.includes(String(p.id)) && !seen.has(String(p.id))) {
        seen.add(String(p.id));
        matched.push(p);
      }
    }
    return matched;
  }, [wishlistIds, backendProducts]);

  return (
    <main className="flex-1 pb-20 bg-ivory">
      <div className="container-site pt-6 pb-12">
        <Breadcrumbs items={[{ label: "Wishlist" }]} />

        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 pb-6 border-b border-hairline mt-4">
          <div>
            <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
              Curated Wardrobe
            </span>
            <h1 className="font-serif text-3xl sm:text-4xl font-medium text-obsidian tracking-tight mt-1">
              Saved Pieces ({wishlistedProducts.length})
            </h1>
            <p className="text-sm text-obsidian-600 mt-1 font-light">
              Your personal curation of luxury fashion and artisanal favorites.
            </p>
          </div>
          <Link
            href="/collections/all"
            className="text-xs sm:text-sm font-medium text-obsidian hover:text-champagne-dark transition-colors duration-fast inline-flex items-center gap-1.5 self-start sm:self-auto"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Continue Shopping</span>
          </Link>
        </div>

        {wishlistedProducts.length === 0 ? (
          <div className="py-24 text-center space-y-4 max-w-md mx-auto">
            <div className="w-16 h-16 rounded-full bg-sand/40 border border-hairline flex items-center justify-center mx-auto text-obsidian-400">
              <Heart className="w-8 h-8" />
            </div>
            <h2 className="font-serif text-2xl font-medium text-obsidian">
              Your wishlist is currently empty
            </h2>
            <p className="text-sm text-obsidian-600 leading-relaxed font-light">
              Tap the heart icon on any piece you love to save it to your wishlist for later.
            </p>
            <div className="pt-2">
              <Link href="/collections/all">
                <Button size="lg" variant="primary">
                  Explore The Catalogue
                </Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-8 mt-8">
            {wishlistedProducts.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                isWishlisted={true}
                onToggleWishlist={() => removeFromWishlist(product.id)}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
