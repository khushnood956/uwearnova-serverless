/**
 * Product Data Models and Types for UWEARNOVA Fashion E-Commerce
 */

export type CategorySlug = "men" | "women" | "footwear" | "accessories";

export type CollectionSlug =
  | "new-arrivals"
  | "essentials"
  | "signature"
  | "trending"
  | "sale";

export interface Category {
  id: string;
  name: string;
  slug: CategorySlug;
  description: string;
  image: string;
}

export interface ProductVariant {
  id?: number | string;
  sku: string;
  size: string; // e.g. "S", "M", "L", "XL" or "40", "41", "42" or "One Size"
  color: string; // e.g. "Obsidian Black", "Sand Ivory", "Champagne Gold"
  colorHex?: string;
  inStock: boolean;
  inventoryCount: number;
}

export interface Product {
  id: string;
  slug: string;
  name: string;
  subtitle?: string;
  description: string;
  category: CategorySlug;
  collections?: CollectionSlug[];
  price: number; // in PKR
  originalPrice?: number; // for sale items in PKR
  images: string[]; // Primary, secondary, multi-angle
  isNewArrival?: boolean;
  isTrending?: boolean;
  isFeatured?: boolean;
  fabricCare?: string[];
  deliveryNotes?: string;
  variants: ProductVariant[];
  rating?: number;
  reviewCount?: number;
}

export interface FilterState {
  category?: CategorySlug | "all";
  collection?: CollectionSlug | "all";
  minPrice?: number;
  maxPrice?: number;
  sizes: string[];
  colors: string[];
  inStockOnly: boolean;
  searchQuery: string;
  sortBy: "featured" | "price-asc" | "price-desc" | "newest";
}
