"use client";

import * as React from "react";
import { Product } from "@/types/product";
import { ProductGrid } from "@/components/product/ProductGrid";
import { ProductFilters, FilterOptions } from "./ProductFilters";

import { catalogApi } from "@/lib/api/catalog";
import { mapBackendProduct } from "@/lib/api/adapters";

export interface CollectionBrowserProps {
  initialProducts: Product[];
  categorySlug?: string;
}

export function CollectionBrowser({ initialProducts, categorySlug }: CollectionBrowserProps) {
  const [products, setProducts] = React.useState<Product[]>(initialProducts);

  React.useEffect(() => {
    setProducts(initialProducts);
  }, [initialProducts]);

  // Client-side refresh to guarantee fresh live data in browser
  React.useEffect(() => {
    if (!categorySlug) return;
    let isCancelled = false;

    const fetchLatest = async () => {
      try {
        const queryParams =
          categorySlug === "all"
            ? { limit: 50 }
            : categorySlug === "new-arrivals"
            ? { limit: 50 }
            : { category_slug: categorySlug, limit: 50 };

        const res = await catalogApi.getProducts(queryParams);
        if (!isCancelled && res && Array.isArray(res.items) && res.items.length > 0) {
          setProducts(res.items.map(mapBackendProduct));
        }
      } catch (e) {
        // Fall back gracefully to existing products
      }
    };

    fetchLatest();
    return () => {
      isCancelled = true;
    };
  }, [categorySlug]);

  const [filters, setFilters] = React.useState<FilterOptions>({
    priceBracket: "all",
    selectedSizes: [],
    inStockOnly: false,
    sortBy: "featured",
  });

  // Extract all unique sizes available in these products
  const availableSizes = React.useMemo(() => {
    const sizeSet = new Set<string>();
    (products || []).forEach((p) => {
      if (p && Array.isArray(p.variants)) {
        p.variants.forEach((v) => {
          if (v && v.size) sizeSet.add(v.size);
        });
      }
    });
    return Array.from(sizeSet);
  }, [products]);

  // Compute filtered & sorted products
  const filteredProducts = React.useMemo(() => {
    return (products || [])
      .filter((product) => {
        if (!product) return false;
        const price = Number(product.price || 0);

        // Price bracket filter
        if (filters.priceBracket === "under-10k" && price >= 10000) {
          return false;
        }
        if (
          filters.priceBracket === "10k-20k" &&
          (price < 10000 || price > 20000)
        ) {
          return false;
        }
        if (filters.priceBracket === "above-20k" && price <= 20000) {
          return false;
        }

        // In-stock filter
        if (filters.inStockOnly) {
          const hasInStockVariant = Array.isArray(product.variants) && product.variants.some((v) => v?.inStock);
          if (!hasInStockVariant) return false;
        }

        // Size filter
        if (filters.selectedSizes && filters.selectedSizes.length > 0) {
          const matchesSize = Array.isArray(product.variants) && product.variants.some(
            (v) => v?.size && filters.selectedSizes.includes(v.size) && v?.inStock
          );
          if (!matchesSize) return false;
        }

        return true;
      })
      .sort((a, b) => {
        const priceA = Number(a?.price || 0);
        const priceB = Number(b?.price || 0);
        if (filters.sortBy === "price-asc") {
          return priceA - priceB;
        }
        if (filters.sortBy === "price-desc") {
          return priceB - priceA;
        }
        if (filters.sortBy === "newest") {
          return (b?.isNewArrival ? 1 : 0) - (a?.isNewArrival ? 1 : 0);
        }
        // Default: featured
        return 0;
      });
  }, [products, filters]);

  return (
    <div>
      <ProductFilters
        filters={filters}
        onChange={setFilters}
        availableSizes={availableSizes}
        totalResults={filteredProducts.length}
      />
      <ProductGrid
        products={filteredProducts}
        columns={4}
        emptyMessage="No pieces match your selected filter criteria. Try clearing some filters."
      />
    </div>
  );
}
