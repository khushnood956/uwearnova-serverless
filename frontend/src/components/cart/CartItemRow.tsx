"use client";

import * as React from "react";
import Image from "next/image";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import { CartItem } from "@/types/cart";
import { formatPKR } from "@/lib/brand";

interface CartItemRowProps {
  item: CartItem;
  onUpdateQuantity: (id: string, qty: number) => void;
  onRemove: (id: string) => void;
  onCloseDrawer?: () => void;
}

export function CartItemRow({
  item,
  onUpdateQuantity,
  onRemove,
  onCloseDrawer,
}: CartItemRowProps) {
  const { product, variant, quantity } = item;

  return (
    <div className="flex gap-4 py-4 border-b border-hairline">
      {/* Thumbnail with 4:5 aspect */}
      <Link
        href={`/product/${product.slug}`}
        onClick={onCloseDrawer}
        className="relative aspect-[4/5] w-20 rounded-image overflow-hidden bg-ivory-sand shrink-0 border border-hairline"
      >
        <Image
          src={product.images[0]}
          alt={product.name}
          fill
          sizes="80px"
          className="object-cover object-center"
        />
      </Link>

      {/* Details */}
      <div className="flex-1 flex flex-col justify-between">
        <div className="space-y-1">
          <div className="flex items-start justify-between gap-2">
            <Link
              href={`/product/${product.slug}`}
              onClick={onCloseDrawer}
              className="text-sm font-serif font-medium text-obsidian hover:text-champagne-dark transition-colors duration-fast line-clamp-1 leading-snug"
            >
              {product.name}
            </Link>
            <button
              type="button"
              onClick={() => onRemove(item.id)}
              aria-label={`Remove ${product.name} from bag`}
              className="text-obsidian-400 hover:text-sale p-1.5 rounded-button transition-colors duration-fast"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-obsidian-500 font-light">
            <span>Size: <strong className="text-obsidian font-medium">{variant.size}</strong></span>
            <span>•</span>
            <span>Color: <strong className="text-obsidian font-medium">{variant.color}</strong></span>
          </div>

          <p className="text-xs font-semibold text-obsidian">
            {formatPKR(product.price)}
          </p>
        </div>

        {/* Quantity Controls */}
        <div className="flex items-center justify-between pt-2">
          <div className="inline-flex items-center rounded-button border border-obsidian/15 bg-ivory-light px-2 py-0.5 text-xs">
            <button
              type="button"
              onClick={() => onUpdateQuantity(item.id, quantity - 1)}
              disabled={quantity <= 1}
              className="w-6 h-6 flex items-center justify-center text-obsidian-600 hover:text-obsidian disabled:opacity-30"
              aria-label="Decrease quantity"
            >
              -
            </button>
            <span className="w-6 text-center font-medium">{quantity}</span>
            <button
              type="button"
              onClick={() => onUpdateQuantity(item.id, quantity + 1)}
              disabled={quantity >= (variant.inventoryCount || 99)}
              className="w-6 h-6 flex items-center justify-center text-obsidian-600 hover:text-obsidian disabled:opacity-30"
              aria-label="Increase quantity"
            >
              +
            </button>
          </div>

          <span className="font-serif text-sm font-semibold text-obsidian">
            {formatPKR(product.price * quantity)}
          </span>
        </div>
      </div>
    </div>
  );
}
