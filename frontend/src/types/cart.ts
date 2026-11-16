import { Product, ProductVariant } from "./product";

export interface CartItem {
  id: string; // unique cart line item id, e.g. `${product.id}-${variant.sku}` or item ID
  rawId?: number;
  variantId?: number;
  product: Product;
  variant: ProductVariant;
  quantity: number;
}

export interface WishlistItem {
  productId: string;
  addedAt: number;
}
