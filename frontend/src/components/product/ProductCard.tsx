"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { Heart, Plus, Check } from "lucide-react";
import { Product } from "@/types/product";
import { formatPKR } from "@/lib/brand";
import { Badge } from "@/components/ui/Badge";
import { useWishlist } from "@/context/WishlistContext";
import { useCart } from "@/context/CartContext";
import { cn } from "@/lib/utils";

export interface ProductCardProps {
  product: Product;
  isWishlisted?: boolean;
  onToggleWishlist?: (product: Product) => void;
  className?: string;
  priority?: boolean;
}

export function ProductCard({
  product,
  isWishlisted: propIsWishlisted,
  onToggleWishlist,
  className,
  priority = false,
}: ProductCardProps) {
  const { isWishlisted: contextIsWishlisted, toggleWishlist } = useWishlist();
  const { addItem } = useCart();
  const [quickAdded, setQuickAdded] = React.useState(false);

  const wishlisted =
    propIsWishlisted !== undefined
      ? propIsWishlisted
      : contextIsWishlisted(product.id);

  const primaryImage = (product?.images && product.images[0]) || "/images/products/placeholder.svg";
  const secondaryImage = (product?.images && product.images[1]) || primaryImage;
  const hasSecondary = Boolean(product?.images && product.images.length > 1 && secondaryImage !== primaryImage);

  const handleWishlistClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onToggleWishlist) {
      onToggleWishlist(product);
    } else {
      toggleWishlist(product.id);
    }
  };

  const handleQuickAdd = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const variants = Array.isArray(product?.variants) ? product.variants : [];
    const firstInStock = variants.find((v) => v.inStock) || variants[0];
    if (firstInStock) {
      addItem(product, firstInStock, 1);
      setQuickAdded(true);
      setTimeout(() => setQuickAdded(false), 2000);
    }
  };

  const discountPercent =
    product.originalPrice && product.originalPrice > product.price
      ? Math.round(
          ((product.originalPrice - product.price) / product.originalPrice) * 100
        )
      : null;

  return (
    <div
      className={cn(
        "group relative flex flex-col rounded-card bg-ivory-light border border-hairline shadow-subtle hover:shadow-card-hover hover:-translate-y-1 transition-[transform,box-shadow] duration-base ease-out overflow-hidden",
        className
      )}
    >
      {/* Product Image Area with 4:5 Aspect Ratio */}
      <Link
        href={`/product/${product.slug}`}
        className="relative aspect-[4/5] w-full overflow-hidden bg-ivory-sand block select-none"
      >
        {/* Primary Image */}
        <Image
          src={primaryImage}
          alt={product.name}
          fill
          priority={priority}
          sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
          className={cn(
            "object-cover object-center transition-opacity duration-base ease-out",
            hasSecondary ? "group-hover:opacity-0" : ""
          )}
        />

        {/* Secondary Image with Pure Opacity Crossfade */}
        {hasSecondary && (
          <Image
            src={secondaryImage}
            alt={`${product.name} alternate view`}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-cover object-center absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-base ease-out"
          />
        )}

        {/* Badges */}
        <div className="absolute top-3 left-3 flex flex-col gap-1.5 z-10">
          {product.isNewArrival && (
            <Badge variant="default" size="sm">
              New
            </Badge>
          )}
          {discountPercent !== null && (
            <Badge variant="sale" size="sm">
              -{discountPercent}%
            </Badge>
          )}
        </div>

        {/* Wishlist Button */}
        <button
          type="button"
          onClick={handleWishlistClick}
          aria-label={
            wishlisted
              ? `Remove ${product.name} from wishlist`
              : `Add ${product.name} to wishlist`
          }
          className="absolute top-3 right-3 z-10 w-9 h-9 rounded-button bg-ivory-light/90 hover:bg-ivory-light text-obsidian shadow-subtle flex items-center justify-center transition-[transform,background-color] duration-fast active:scale-90"
        >
          <Heart
            className={cn(
              "w-4 h-4 transition-colors duration-fast",
              wishlisted
                ? "fill-sale text-sale"
                : "text-obsidian-700 hover:text-obsidian"
            )}
          />
        </button>

        {/* Quick Add Bar: Slides up from bottom of image on hover (desktop), compact on touch */}
        <div className="absolute inset-x-2 bottom-2 z-10 opacity-0 translate-y-2 group-hover:opacity-100 group-hover:translate-y-0 transition-[opacity,transform] duration-base ease-out">
          <button
            type="button"
            onClick={handleQuickAdd}
            className="w-full py-2.5 px-3 rounded-button bg-obsidian/90 hover:bg-obsidian text-ivory text-xs font-medium tracking-wide flex items-center justify-center gap-1.5 backdrop-blur-xs shadow-card transition-colors duration-fast"
          >
            {quickAdded ? (
              <>
                <Check className="w-3.5 h-3.5 text-champagne-light" />
                <span>Added to Bag</span>
              </>
            ) : (
              <>
                <Plus className="w-3.5 h-3.5" />
                <span>Quick Add</span>
              </>
            )}
          </button>
        </div>
      </Link>

      {/* Product Details */}
      <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
        <div className="space-y-1">
          {product.subtitle && (
            <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-champagne-dark">
              {product.subtitle}
            </p>
          )}
          <Link href={`/product/${product.slug}`} className="block">
            <h3 className="font-serif text-base font-medium text-obsidian hover:text-champagne-dark transition-colors duration-fast line-clamp-1 leading-snug">
              {product.name}
            </h3>
          </Link>
        </div>

        <div className="pt-2 border-t border-hairline flex items-baseline justify-between">
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-sm sm:text-base font-semibold text-obsidian">
              {formatPKR(product.price)}
            </span>
            {product.originalPrice && (
              <span className="text-xs text-obsidian-400 line-through">
                {formatPKR(product.originalPrice)}
              </span>
            )}
          </div>
          <span className="text-[11px] text-obsidian-500 capitalize tracking-wide font-light">
            {product.category}
          </span>
        </div>
      </div>
    </div>
  );
}
