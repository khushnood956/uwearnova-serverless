/**
 * UWEARNOVA API Domain TypeScript Definitions
 * Directly maps to FastAPI backend schemas (M01-M22).
 */

// ---------------------------------------------------------------------------
// Error & Response Meta
// ---------------------------------------------------------------------------

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface ApiErrorResponse {
  error?: ApiErrorDetail;
  detail?: string | Array<{ loc: string[]; msg: string; type: string }>;
}

// ---------------------------------------------------------------------------
// Identity & Authentication
// ---------------------------------------------------------------------------

export interface UserResponse {
  id: number;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  status: string;
  user_type: "customer" | "staff" | "admin";
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// ---------------------------------------------------------------------------
// Catalog & Categories
// ---------------------------------------------------------------------------

export interface Category {
  id: number | string;
  name: string;
  slug: string;
  description?: string | null;
  image_url?: string | null;
  sort_order?: number;
  display_order?: number;
  level?: number;
  is_active: boolean;
  is_coming_soon: boolean;
  parent_id?: number | string | null;
  created_at?: string;
  updated_at?: string;
}

export interface CategoryTree extends Category {
  children: CategoryTree[];
}

export type CategoryTreeNode = CategoryTree;

export interface Collection {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  image_url?: string | null;
  sort_order: number;
  is_active: boolean;
  product_count?: number;
  created_at: string;
  updated_at: string;
}

export interface ProductVariant {
  id: number;
  product_id: number;
  sku: string;
  size: string;
  color_name: string;
  color_hex?: string | null;
  price?: number | string | null;
  inventory_count: number;
  in_stock: boolean;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ProductImage {
  id: number;
  image_url: string;
  alt_text?: string | null;
  sort_order: number;
  is_primary: boolean;
}

export interface Product {
  id: number;
  name: string;
  slug: string;
  subtitle?: string | null;
  description?: string | null;
  brand_label: string;
  status: "draft" | "active" | "archived";
  price: number | string;
  original_price?: number | string | null;
  is_new_arrival: boolean;
  is_trending: boolean;
  is_featured: boolean;
  fabric_care?: string[] | string | null;
  delivery_notes?: string | null;
  rating: number | string;
  review_count: number;
  category_id: number;
  category?: Category | null;
  collections?: Collection[];
  variants: ProductVariant[];
  images: ProductImage[];
  created_at: string;
  updated_at: string;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProductQueryParams {
  category_id?: number;
  category_slug?: string;
  collection_id?: number;
  collection_slug?: string;
  min_price?: number;
  max_price?: number;
  sizes?: string[];
  colors?: string[];
  in_stock_only?: boolean;
  is_new_arrival?: boolean;
  is_trending?: boolean;
  is_featured?: boolean;
  search?: string;
  sort_by?: "newest" | "price_asc" | "price_desc" | "rating" | "featured";
  limit?: number;
  offset?: number;
  page_size?: number;
}

// ---------------------------------------------------------------------------
// Cart & Wishlist
// ---------------------------------------------------------------------------

export interface CartItemResponse {
  id: number;
  variant_id: number;
  product_id: number;
  product_name: string;
  product_slug: string;
  sku: string;
  size: string;
  color: string;
  image_url?: string | null;
  unit_price: number | string;
  quantity: number;
  line_subtotal: number | string;
  in_stock: boolean;
  available_inventory: number;
  is_price_changed: boolean;
}

export interface CartResponse {
  id: number;
  user_id?: number | null;
  anonymous_token?: string | null;
  items: CartItemResponse[];
  total_items: number;
  subtotal: number | string;
  discount_total: number | string;
  shipping_estimate: number | string;
  grand_total: number | string;
  is_free_shipping: boolean;
  amount_for_free_shipping: number | string;
  free_shipping_threshold: number | string;
  currency: string;
}

export type ProductResponse = Product;
export type ProductVariantResponse = ProductVariant;
export type CategoryResponse = Category;
export type CollectionResponse = Collection;

export interface AddToCartRequest {
  variant_id: number;
  quantity?: number;
}

export interface UpdateCartItemRequest {
  quantity: number;
}

export interface MergeCartRequest {
  anonymous_token: string;
}

export interface WishlistItemResponse {
  id: number;
  product_id: number;
  product: Product;
  created_at: string;
}

export interface WishlistResponse {
  id: number;
  user_id: number;
  total_items: number;
  items: WishlistItemResponse[];
}
