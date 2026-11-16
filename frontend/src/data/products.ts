import { Product } from "@/types/product";

export const PRODUCTS: Product[] = [];

export function getProductBySlug(slug: string): Product | undefined {
  return PRODUCTS.find((p) => p.slug === slug);
}

export function getProductsByCategory(category: string): Product[] {
  if (category === "all") return PRODUCTS;
  return PRODUCTS.filter((p) => p.category === category);
}

export function getProductsByCollection(collection: string): Product[] {
  return PRODUCTS.filter((p) => p.collections?.includes(collection as any));
}

export function getFeaturedProducts(): Product[] {
  return PRODUCTS.filter((p) => p.isFeatured);
}

export function getTrendingProducts(): Product[] {
  return PRODUCTS.filter((p) => p.isTrending);
}
