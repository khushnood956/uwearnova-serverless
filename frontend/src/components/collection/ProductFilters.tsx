"use client";

import * as React from "react";
import { X, SlidersHorizontal, RotateCcw, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export interface FilterOptions {
  priceBracket: string; // "all" | "under-10k" | "10k-20k" | "above-20k"
  selectedSizes: string[];
  inStockOnly: boolean;
  sortBy: "featured" | "price-asc" | "price-desc" | "newest";
}

export interface ProductFiltersProps {
  filters: FilterOptions;
  onChange: (filters: FilterOptions) => void;
  availableSizes: string[];
  totalResults: number;
}

export function ProductFilters({
  filters,
  onChange,
  availableSizes,
  totalResults,
}: ProductFiltersProps) {
  const [mobileDrawerOpen, setMobileDrawerOpen] = React.useState(false);

  const handlePriceChange = (bracket: string) => {
    onChange({ ...filters, priceBracket: bracket });
  };

  const handleSizeToggle = (size: string) => {
    const nextSizes = filters.selectedSizes.includes(size)
      ? filters.selectedSizes.filter((s) => s !== size)
      : [...filters.selectedSizes, size];
    onChange({ ...filters, selectedSizes: nextSizes });
  };

  const handleReset = () => {
    onChange({
      priceBracket: "all",
      selectedSizes: [],
      inStockOnly: false,
      sortBy: "featured",
    });
  };

  const activeFiltersCount =
    (filters.priceBracket !== "all" ? 1 : 0) +
    filters.selectedSizes.length +
    (filters.inStockOnly ? 1 : 0);

  const FilterControls = () => (
    <div className="space-y-6">
      {/* In-Stock Toggle */}
      <div>
        <label className="flex items-center gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={filters.inStockOnly}
            onChange={(e) =>
              onChange({ ...filters, inStockOnly: e.target.checked })
            }
            className="w-4 h-4 rounded border-hairline text-obsidian focus:ring-champagne focus:ring-offset-0 accent-obsidian"
          />
          <span className="text-xs sm:text-sm font-medium text-obsidian-800">
            In-Stock Items Only
          </span>
        </label>
      </div>

      {/* Price Bracket */}
      <div className="space-y-2.5">
        <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-obsidian-600">
          Price Range
        </span>
        <div className="flex flex-wrap gap-2 text-xs">
          {[
            { id: "all", label: "All Prices" },
            { id: "under-10k", label: "Under Rs. 10,000" },
            { id: "10k-20k", label: "Rs. 10k – 20k" },
            { id: "above-20k", label: "Over Rs. 20,000" },
          ].map((option) => {
            const isSelected = filters.priceBracket === option.id;
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => handlePriceChange(option.id)}
                className={`px-3.5 py-1.5 rounded-button text-xs font-medium border transition-[background-color,border-color,color] duration-fast ease-out ${
                  isSelected
                    ? "bg-obsidian text-ivory border-obsidian"
                    : "bg-ivory-light text-obsidian-700 border-hairline hover:border-obsidian/40 hover:bg-sand/40"
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Sizes */}
      {availableSizes.length > 0 && (
        <div className="space-y-2.5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-obsidian-600">
            Available Sizes
          </span>
          <div className="flex flex-wrap gap-1.5">
            {availableSizes.map((size) => {
              const isSelected = filters.selectedSizes.includes(size);
              return (
                <button
                  key={size}
                  type="button"
                  onClick={() => handleSizeToggle(size)}
                  className={`min-w-[40px] h-9 px-3 rounded-button text-xs font-medium border transition-[background-color,border-color,color] duration-fast ease-out ${
                    isSelected
                      ? "bg-obsidian text-ivory border-obsidian"
                      : "bg-ivory-light text-obsidian-700 border-hairline hover:border-obsidian/40 hover:bg-sand/40"
                  }`}
                >
                  {size}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Clear All */}
      {activeFiltersCount > 0 && (
        <div className="pt-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleReset}
            className="w-full text-xs text-obsidian-600 border-dashed"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
            Clear Active Filters ({activeFiltersCount})
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <div className="mb-8">
      {/* Top Filter & Sort Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 py-3 px-4 sm:px-5 rounded-card bg-ivory-light border border-hairline shadow-subtle">
        {/* Left: Mobile trigger & Active badges */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileDrawerOpen(true)}
            className="inline-flex lg:hidden items-center gap-2 px-3 py-1.5 rounded-button border border-hairline text-xs font-medium text-obsidian hover:bg-sand/40 transition-[background-color] duration-fast ease-out"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Filters</span>
            {activeFiltersCount > 0 && (
              <Badge variant="accent" size="sm">
                {activeFiltersCount}
              </Badge>
            )}
          </button>

          <span className="text-xs text-obsidian-600 font-medium">
            Showing <strong className="text-obsidian font-semibold">{totalResults}</strong> {totalResults === 1 ? "piece" : "pieces"}
          </span>
        </div>

        {/* Right: Sort By */}
        <div className="flex items-center gap-2.5">
          <label
            htmlFor="sort-select"
            className="text-[11px] font-semibold uppercase tracking-[0.16em] text-obsidian-600 hidden sm:inline"
          >
            Sort by:
          </label>
          <div className="relative">
            <select
              id="sort-select"
              value={filters.sortBy}
              onChange={(e) =>
                onChange({
                  ...filters,
                  sortBy: e.target.value as FilterOptions["sortBy"],
                })
              }
              className="appearance-none text-xs sm:text-sm font-medium bg-sand/30 border border-hairline rounded-button pl-3.5 pr-8 py-1.5 text-obsidian focus:outline-none focus:border-champagne focus:ring-1 focus:ring-champagne cursor-pointer transition-[border-color] duration-fast ease-out"
            >
              <option value="featured">Featured Curations</option>
              <option value="newest">Newest Arrivals</option>
              <option value="price-asc">Price: Low to High</option>
              <option value="price-desc">Price: High to Low</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-obsidian-500" />
          </div>
        </div>
      </div>

      {/* Desktop Filter Panel */}
      <div className="hidden lg:block mt-3 p-5 rounded-card bg-ivory-light/70 border border-hairline">
        <FilterControls />
      </div>

      {/* Mobile Drawer */}
      {mobileDrawerOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex lg:hidden"
        >
          <div
            onClick={() => setMobileDrawerOpen(false)}
            className="fixed inset-0 bg-obsidian/60 backdrop-blur-xs transition-opacity duration-base"
          />
          <div className="relative w-4/5 max-w-xs bg-ivory-light h-full shadow-2xl p-6 z-10 flex flex-col overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-hairline">
              <h3 className="font-serif text-lg font-medium text-obsidian">
                Refine Pieces
              </h3>
              <button
                onClick={() => setMobileDrawerOpen(false)}
                className="p-1.5 text-obsidian-500 hover:text-obsidian rounded-full transition-colors duration-fast"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="py-6 flex-1">
              <FilterControls />
            </div>
            <Button
              variant="primary"
              onClick={() => setMobileDrawerOpen(false)}
              className="w-full mt-4"
            >
              Apply Filters ({totalResults} Results)
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
