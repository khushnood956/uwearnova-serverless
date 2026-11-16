import { Product as FrontendProduct, ProductVariant as FrontendVariant, CategorySlug } from "@/types/product";
import { CartItem } from "@/types/cart";
import { Product, ProductVariant, CartItemResponse } from "./types";

export function mapBackendVariant(v: any): FrontendVariant {
  const inStock = v.in_stock !== undefined
    ? Boolean(v.in_stock)
    : (v.inventory_count || v.available_inventory || 0) > 0;

  return {
    id: v.id,
    sku: v.sku || v.variant_sku || `SKU-${v.id}`,
    size: v.size || "Standard",
    color: v.color_name || v.color || "Classic",
    colorHex: v.color_hex || v.color_code || undefined,
    inStock,
    inventoryCount: v.inventory_count ?? v.available_inventory ?? 0,
  };
}

export function mapBackendProduct(p: any): FrontendProduct {
  // Map images
  const images: string[] = [];
  if (Array.isArray(p.images) && p.images.length > 0) {
    const sorted = [...p.images].sort(
      (a, b) => (a.sort_order ?? a.position ?? 0) - (b.sort_order ?? b.position ?? 0)
    );
    for (const img of sorted) {
      const src = typeof img === "string" ? img : (img.image_url || img.url);
      if (src) images.push(src);
    }
  }
  if (images.length === 0) {
    images.push("/images/products/placeholder.svg");
  }

  // Map category slug
  const categorySlug = (p.category?.slug as CategorySlug) || "men";

  // Map variants
  const variants = Array.isArray(p.variants) && p.variants.length > 0
    ? p.variants.map(mapBackendVariant)
    : [
        {
          id: 1,
          sku: `SKU-${p.id}-STD`,
          size: "Standard",
          color: "Classic",
          inStock: true,
          inventoryCount: 10,
        },
      ];

  const priceNum = typeof p.price === "string" ? parseFloat(p.price) : Number(p.price || 0);
  const origPrice = p.original_price ?? p.compare_at_price;
  const origPriceNum = origPrice ? (typeof origPrice === "string" ? parseFloat(origPrice) : Number(origPrice)) : undefined;

  return {
    id: String(p.id),
    slug: p.slug,
    name: p.name,
    subtitle: p.subtitle || undefined,
    description: p.description || "",
    category: categorySlug,
    price: priceNum,
    originalPrice: origPriceNum,
    images,
    isFeatured: Boolean(p.is_featured),
    isNewArrival: Boolean(p.is_new_arrival),
    isTrending: Boolean(p.is_trending),
    rating: p.rating ? Number(p.rating) : undefined,
    reviewCount: p.review_count ? Number(p.review_count) : undefined,
    fabricCare: Array.isArray(p.fabric_care) ? p.fabric_care : undefined,
    variants,
  };
}

export function mapBackendCartItem(item: any): CartItem {
  const unitPrice = typeof item.unit_price === "string" ? parseFloat(item.unit_price) : Number(item.unit_price || 0);
  const origPrice = item.original_price;
  const origPriceNum = origPrice ? (typeof origPrice === "string" ? parseFloat(origPrice) : Number(origPrice)) : undefined;

  return {
    id: String(item.id),
    rawId: item.id,
    variantId: item.variant_id,
    quantity: item.quantity,
    product: {
      id: String(item.product_id),
      slug: item.product_slug,
      name: item.product_name,
      description: "",
      category: "men",
      price: unitPrice,
      originalPrice: origPriceNum,
      images: item.image_url ? [item.image_url] : ["/images/products/placeholder.jpg"],
      variants: [],
    },
    variant: {
      id: item.variant_id,
      sku: item.sku || item.variant_sku || `SKU-${item.variant_id}`,
      size: item.size || "Standard",
      color: item.color || item.color_name || "Classic",
      colorHex: item.color_hex || undefined,
      inStock: item.in_stock ?? item.is_available ?? true,
      inventoryCount: item.available_inventory ?? item.available_stock ?? 99,
    },
  };
}
