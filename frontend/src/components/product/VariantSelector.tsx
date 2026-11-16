"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ShoppingBag, Check } from "lucide-react";
import { Product, ProductVariant } from "@/types/product";
import { Button } from "@/components/ui/Button";
import { useCart } from "@/context/CartContext";
import { SizeGuideModal } from "./SizeGuideModal";
import { cn } from "@/lib/utils";

interface VariantSelectorProps {
  product: Product;
  onAddToCart?: (variant: ProductVariant, quantity: number) => void;
  onBuyNow?: (variant: ProductVariant, quantity: number) => void;
}

export function VariantSelector({
  product,
  onAddToCart,
  onBuyNow,
}: VariantSelectorProps) {
  const router = useRouter();
  const { addItem } = useCart();

  // Unique colors and sizes
  const availableColors = React.useMemo(() => {
    const map = new Map<string, { name: string; hex?: string }>();
    product.variants.forEach((v) => {
      if (!map.has(v.color)) {
        map.set(v.color, { name: v.color, hex: v.colorHex });
      }
    });
    return Array.from(map.values());
  }, [product.variants]);

  const [selectedColor, setSelectedColor] = React.useState<string>(
    availableColors[0]?.name || ""
  );

  // Available sizes for the chosen color
  const colorVariants = React.useMemo(() => {
    return product.variants.filter((v) => v.color === selectedColor);
  }, [product.variants, selectedColor]);

  const [selectedSize, setSelectedSize] = React.useState<string>(
    colorVariants.find((v) => v.inStock)?.size || colorVariants[0]?.size || ""
  );

  const [quantity, setQuantity] = React.useState(1);
  const [sizeGuideOpen, setSizeGuideOpen] = React.useState(false);
  const [feedback, setFeedback] = React.useState<string | null>(null);

  // Active chosen variant
  const activeVariant = React.useMemo(() => {
    return colorVariants.find((v) => v.size === selectedSize);
  }, [colorVariants, selectedSize]);

  const handleAddToCart = () => {
    if (!activeVariant) {
      setFeedback("Please select a size first.");
      return;
    }
    if (!activeVariant.inStock) {
      setFeedback("Selected variant is currently sold out.");
      return;
    }
    setFeedback("Added to your shopping bag");
    setTimeout(() => setFeedback(null), 3000);
    if (onAddToCart) {
      onAddToCart(activeVariant, quantity);
    } else {
      addItem(product, activeVariant, quantity);
    }
  };

  const handleBuyNow = () => {
    if (!activeVariant || !activeVariant.inStock) {
      setFeedback("Please select an in-stock variant.");
      return;
    }
    if (onBuyNow) {
      onBuyNow(activeVariant, quantity);
    } else {
      addItem(product, activeVariant, quantity);
      router.push("/checkout");
    }
  };

  return (
    <div className="space-y-6">
      {/* Color Picker */}
      {availableColors.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-[0.18em] text-obsidian-600">
            <span>
              Color:{" "}
              <strong className="text-obsidian capitalize font-semibold tracking-normal">
                {selectedColor}
              </strong>
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {availableColors.map((col) => {
              const isSelected = selectedColor === col.name;
              return (
                <button
                  key={col.name}
                  type="button"
                  title={col.name}
                  aria-label={`Select color ${col.name}`}
                  onClick={() => {
                    setSelectedColor(col.name);
                    const matching = product.variants.filter((v) => v.color === col.name);
                    if (!matching.some((v) => v.size === selectedSize && v.inStock)) {
                      setSelectedSize(matching.find((v) => v.inStock)?.size || matching[0]?.size || "");
                    }
                  }}
                  className={cn(
                    "relative w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center transition-[box-shadow,transform] duration-fast ease-out",
                    isSelected
                      ? "ring-2 ring-obsidian ring-offset-2 ring-offset-ivory"
                      : "hover:scale-105"
                  )}
                >
                  <span
                    className="w-full h-full rounded-full border border-hairline shadow-inner"
                    style={{ backgroundColor: col.hex || "#C5AA82" }}
                  />
                  {isSelected && (
                    <span className="sr-only">Selected</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Size Picker */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold uppercase tracking-[0.18em] text-obsidian-600">
            Select Size
          </span>
          <button
            type="button"
            onClick={() => setSizeGuideOpen(true)}
            className="text-champagne-dark hover:text-obsidian underline underline-offset-4 font-medium transition-colors duration-fast"
          >
            Size Guide
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {colorVariants.map((v) => {
            const isSelected = selectedSize === v.size;
            return (
              <button
                key={v.size}
                type="button"
                disabled={!v.inStock}
                onClick={() => setSelectedSize(v.size)}
                className={cn(
                  "min-w-[44px] h-11 px-3.5 rounded-button text-xs font-medium border flex items-center justify-center transition-[background-color,border-color,color] duration-fast ease-out",
                  isSelected
                    ? "bg-obsidian text-ivory border-obsidian"
                    : v.inStock
                    ? "bg-ivory-light text-obsidian border-hairline hover:border-obsidian/50"
                    : "bg-sand/30 text-obsidian-400 border-hairline cursor-not-allowed line-through opacity-50"
                )}
              >
                {v.size}
              </button>
            );
          })}
        </div>
      </div>

      {/* Stock Status Indicator - Clean static dot, no infinite pulse */}
      <div className="text-xs flex items-center gap-2">
        {activeVariant?.inStock ? (
          <>
            <span className="w-2 h-2 rounded-full bg-success shrink-0" />
            <span className="text-success font-medium">
              In Stock & Ready for Immediate Dispatch
            </span>
            {activeVariant.inventoryCount <= 5 && (
              <span className="text-champagne-dark font-medium">
                (Only {activeVariant.inventoryCount} left)
              </span>
            )}
          </>
        ) : (
          <>
            <span className="w-2 h-2 rounded-full bg-danger shrink-0" />
            <span className="text-danger font-medium">Currently Sold Out</span>
          </>
        )}
      </div>

      {/* Quantity & Actions */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center gap-3">
          <div className="inline-flex items-center rounded-button border border-hairline bg-ivory-light px-2 py-0.5">
            <button
              type="button"
              onClick={() => setQuantity(Math.max(1, quantity - 1))}
              disabled={quantity <= 1}
              className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center text-obsidian-600 hover:text-obsidian disabled:opacity-30 transition-colors duration-fast"
              aria-label="Decrease quantity"
            >
              -
            </button>
            <span className="w-8 text-center text-xs font-semibold text-obsidian">{quantity}</span>
            <button
              type="button"
              onClick={() => setQuantity(quantity + 1)}
              disabled={!activeVariant || quantity >= activeVariant.inventoryCount}
              className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center text-obsidian-600 hover:text-obsidian disabled:opacity-30 transition-colors duration-fast"
              aria-label="Increase quantity"
            >
              +
            </button>
          </div>

          <Button
            size="lg"
            variant="primary"
            onClick={handleAddToCart}
            disabled={!activeVariant?.inStock}
            className="flex-1"
          >
            <ShoppingBag className="w-4 h-4 mr-2" />
            <span>Add to Bag</span>
          </Button>
        </div>

        <Button
          size="lg"
          variant="accent"
          onClick={handleBuyNow}
          disabled={!activeVariant?.inStock}
          className="w-full"
        >
          Buy Now with Cash on Delivery
        </Button>
      </div>

      {/* Feedback Notice */}
      {feedback && (
        <div className="p-3 rounded-card bg-obsidian text-ivory text-xs flex items-center gap-2 transition-opacity duration-fast">
          <Check className="w-4 h-4 text-champagne-light shrink-0" />
          <span>{feedback}</span>
        </div>
      )}

      {/* Size Guide Modal Shell */}
      <SizeGuideModal
        isOpen={sizeGuideOpen}
        onClose={() => setSizeGuideOpen(false)}
        category={product.category}
      />
    </div>
  );
}
