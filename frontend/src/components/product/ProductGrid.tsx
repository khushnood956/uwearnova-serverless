import * as React from "react";
import { Product } from "@/types/product";
import { ProductCard } from "./ProductCard";
import { cn } from "@/lib/utils";

export interface ProductGridProps {
  products: Product[];
  columns?: 2 | 3 | 4;
  className?: string;
  emptyMessage?: string;
}

export function ProductGrid({
  products,
  columns = 4,
  className,
  emptyMessage = "No pieces found.",
}: ProductGridProps) {
  if (products.length === 0) {
    return (
      <div className="py-16 text-center text-obsidian-500 bg-ivory-light rounded-card border border-hairline p-8">
        <p className="text-base font-light">{emptyMessage}</p>
      </div>
    );
  }

  // When count is 4 (or columns=4), use 2 cols on mobile/tablet and 4 cols on desktop to eliminate the 3+1 orphan bug
  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-2 md:grid-cols-3",
    4: "grid-cols-2 lg:grid-cols-4",
  };

  return (
    <div className={cn("grid gap-4 sm:gap-6 lg:gap-8", gridCols[columns], className)}>
      {products.map((product, idx) => (
        <ProductCard
          key={product.id}
          product={product}
          priority={idx < 4}
        />
      ))}
    </div>
  );
}
