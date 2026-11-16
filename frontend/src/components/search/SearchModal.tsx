"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { Search, X, ArrowRight } from "lucide-react";
import { PRODUCTS } from "@/data/products";
import { Product } from "@/types/product";
import { formatPKR } from "@/lib/brand";

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      document.body.style.overflow = "";
      setQuery("");
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const filteredProducts: Product[] = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return PRODUCTS.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q) ||
        p.subtitle?.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q)
    ).slice(0, 5);
  }, [query]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Search Catalogue"
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 p-4"
    >
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-obsidian/60 backdrop-blur-xs transition-opacity duration-base"
      />

      {/* Modal Card */}
      <div className="relative w-full max-w-2xl bg-ivory-light rounded-card shadow-card-hover border border-hairline overflow-hidden z-10 animate-fade-in">
        {/* Search Input Bar */}
        <div className="flex items-center px-6 py-4 border-b border-hairline bg-sand/20">
          <Search className="w-5 h-5 text-obsidian-400 mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by piece, style, category, or textile..."
            className="w-full text-base sm:text-lg bg-transparent text-obsidian placeholder:text-obsidian-400 focus:outline-none"
          />
          <button
            onClick={onClose}
            aria-label="Close search"
            className="p-1.5 ml-2 text-obsidian-400 hover:text-obsidian rounded-full hover:bg-sand/40 transition-colors duration-fast"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Results Area */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {query.trim() === "" ? (
            <div className="space-y-4">
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-obsidian-500">
                Popular Searches
              </span>
              <div className="flex flex-wrap gap-2">
                {["Blazers", "Linen Shirts", "Loafers", "Silk Scarf", "Tote Bag"].map(
                  (term) => (
                    <button
                      key={term}
                      onClick={() => setQuery(term)}
                      className="px-3.5 py-1.5 rounded-button text-xs font-medium bg-sand/40 hover:bg-sand text-obsidian border border-hairline transition-colors duration-fast"
                    >
                      {term}
                    </button>
                  )
                )}
              </div>
            </div>
          ) : filteredProducts.length > 0 ? (
            <div className="space-y-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-obsidian-500">
                Found {filteredProducts.length}{" "}
                {filteredProducts.length === 1 ? "Result" : "Results"}
              </span>
              <div className="divide-y divide-hairline">
                {filteredProducts.map((product) => (
                  <Link
                    key={product.id}
                    href={`/product/${product.slug}`}
                    onClick={onClose}
                    className="flex items-center gap-4 py-3 group hover:bg-sand/30 px-2 rounded-card transition-colors duration-fast"
                  >
                    <div className="relative w-14 h-18 rounded-image overflow-hidden bg-sand/30 border border-hairline shrink-0">
                      <Image
                        src={product.images[0]}
                        alt={product.name}
                        fill
                        sizes="56px"
                        className="object-cover object-center"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-serif font-medium text-obsidian group-hover:text-champagne-dark transition-colors duration-fast truncate">
                        {product.name}
                      </h4>
                      <p className="text-xs text-obsidian-500 capitalize">
                        {product.category}
                      </p>
                      <p className="text-xs font-semibold text-obsidian mt-0.5">
                        {formatPKR(product.price)}
                      </p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-obsidian-400 group-hover:text-obsidian group-hover:translate-x-1 transition-transform duration-fast ease-out" />
                  </Link>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-obsidian-500 space-y-2">
              <p className="text-sm">No products found matching &ldquo;{query}&rdquo;</p>
              <p className="text-xs text-obsidian-400">
                Try searching for general terms like blazer, shirt, or leather.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
