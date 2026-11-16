/**
 * Admin Dashboard & Operations API (Supabase Backend)
 * Direct database querying with RBAC Row Level Security and PostgreSQL RPCs.
 */

import { supabase } from "@/lib/supabase/client";
import { Category, CategoryTree, Product, ProductListResponse } from "./types";

export interface AdminCategoryCreate {
  name: string;
  slug: string;
  description?: string;
  parent_id?: number | null;
  sort_order?: number;
  is_active?: boolean;
  is_coming_soon?: boolean;
}

export interface AdminCategoryUpdate {
  name?: string;
  slug?: string;
  description?: string;
  parent_id?: number | null;
  sort_order?: number;
  is_active?: boolean;
  is_coming_soon?: boolean;
}

export interface AdminProductCreate {
  name: string;
  slug: string;
  subtitle?: string;
  description?: string;
  category_id: number;
  collection_ids?: number[];
  price: number;
  original_price?: number;
  brand_label?: string;
  status?: "draft" | "active" | "archived";
  is_featured?: boolean;
  is_new_arrival?: boolean;
  is_trending?: boolean;
  fabric_care?: string[];
  delivery_notes?: string;
}

export interface AdminVariantCreate {
  sku: string;
  size: string;
  color_name: string;
  color_hex?: string;
  price?: number;
  inventory_count: number;
  is_active?: boolean;
}

export interface AdminReportsOverview {
  gross_sales: number | string;
  net_revenue: number | string;
  collected_payments: number | string;
  outstanding_cod: number | string;
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  cancelled_orders: number;
  total_customers: number;
  active_products_count: number;
  low_stock_items_count: number;
}

export interface AdminAuditLog {
  id: number;
  actor_id?: number;
  actor_email?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  changes?: any;
  ip_address?: string;
  created_at: string;
}

export const adminApi = {
  // ---------------------------------------------------------------------------
  // 1. Reports & Analytics
  // ---------------------------------------------------------------------------

  async getOverview(): Promise<AdminReportsOverview> {
    const { data: salesOverview } = await supabase
      .from("v_admin_sales_overview")
      .select("*")
      .maybeSingle();

    const { count: customerCount } = await supabase
      .from("users")
      .select("id", { count: "exact", head: true })
      .eq("user_type", "customer");

    const { count: productCount } = await supabase
      .from("products")
      .select("id", { count: "exact", head: true })
      .eq("status", "active");

    const { count: lowStockCount } = await supabase
      .from("v_low_stock_alerts")
      .select("sku", { count: "exact", head: true });

    return {
      gross_sales: salesOverview?.gross_sales || 0,
      net_revenue: salesOverview?.collected_revenue || 0,
      collected_payments: salesOverview?.collected_revenue || 0,
      outstanding_cod: salesOverview?.outstanding_cod || 0,
      total_orders: salesOverview?.total_orders || 0,
      pending_orders: salesOverview?.pending_orders || 0,
      completed_orders: salesOverview?.completed_orders || 0,
      cancelled_orders: salesOverview?.cancelled_orders || 0,
      total_customers: customerCount || 0,
      active_products_count: productCount || 0,
      low_stock_items_count: lowStockCount || 0,
    };
  },

  async getSalesTrends(): Promise<any> {
    const { data } = await supabase
      .from("orders")
      .select("grand_total, placed_at, status")
      .order("placed_at", { ascending: true })
      .limit(100);
    return data || [];
  },

  async getBestSellers(): Promise<any> {
    const { data } = await supabase
      .from("order_items")
      .select("product_name, sku, quantity, line_total")
      .limit(10);
    return data || [];
  },

  async getInventoryReport(): Promise<any> {
    const { data } = await supabase.from("v_low_stock_alerts").select("*");
    return data || [];
  },

  // ---------------------------------------------------------------------------
  // 2. Categories & Departments
  // ---------------------------------------------------------------------------

  async getCategories(is_active?: boolean): Promise<Category[]> {
    let query = supabase.from("categories").select("*").order("sort_order", { ascending: true });
    if (is_active !== undefined) query = query.eq("is_active", is_active);

    const { data, error } = await query;
    if (error) throw new Error(error.message);
    return data || [];
  },

  async getCategoryTree(): Promise<CategoryTree[]> {
    const categories = await adminApi.getCategories();
    const roots: CategoryTree[] = [];
    const map = new Map<number | string, CategoryTree>();

    categories.forEach((cat) => map.set(cat.id, { ...cat, children: [] }));
    categories.forEach((cat) => {
      const node = map.get(cat.id);
      if (!node) return;
      if (cat.parent_id && map.has(cat.parent_id)) {
        map.get(cat.parent_id)!.children.push(node);
      } else if (!cat.parent_id) {
        roots.push(node);
      }
    });

    return roots;
  },

  async createCategory(data: AdminCategoryCreate): Promise<Category> {
    const { data: cat, error } = await supabase.from("categories").insert(data).select("*").single();
    if (error) throw new Error(error.message);
    return cat;
  },

  async updateCategory(id: number | string, data: AdminCategoryUpdate): Promise<Category> {
    const { data: cat, error } = await supabase
      .from("categories")
      .update(data)
      .eq("id", Number(id))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return cat;
  },

  async deleteCategory(id: number | string): Promise<{ message: string }> {
    const { error } = await supabase.from("categories").delete().eq("id", Number(id));
    if (error) throw new Error(error.message);
    return { message: "Category deleted successfully" };
  },

  // ---------------------------------------------------------------------------
  // 3. Products & Variants
  // ---------------------------------------------------------------------------

  async getProducts(params?: {
    category_id?: number;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<ProductListResponse> {
    const limit = params?.limit || 20;
    const offset = params?.offset || 0;

    let query = supabase
      .from("products")
      .select("*, category:categories(*), variants:product_variants(*), images:product_images(*)", { count: "exact" });

    if (params?.category_id) query = query.eq("category_id", params.category_id);
    if (params?.status) query = query.eq("status", params.status);
    if (params?.search) query = query.ilike("name", `%${params.search}%`);

    query = query.order("created_at", { ascending: false }).range(offset, offset + limit - 1);

    const { data, count, error } = await query;
    if (error) throw new Error(error.message);

    return { items: data || [], total: count || 0, limit, offset };
  },

  async getProduct(id: number | string): Promise<Product> {
    const { data, error } = await supabase
      .from("products")
      .select("*, category:categories(*), variants:product_variants(*), images:product_images(*)")
      .eq("id", Number(id))
      .single();

    if (error || !data) throw new Error(error?.message || `Product ${id} not found`);
    return data;
  },

  async createProduct(data: AdminProductCreate): Promise<Product> {
    const { collection_ids, ...productData } = data;
    const { data: p, error } = await supabase.from("products").insert(productData).select("*").single();
    if (error || !p) throw new Error(error?.message || "Failed to create product");

    if (collection_ids && collection_ids.length > 0) {
      await supabase.from("product_collections").insert(
        collection_ids.map((cid) => ({ product_id: p.id, collection_id: cid }))
      );
    }

    return await adminApi.getProduct(p.id);
  },

  async updateProduct(id: number | string, data: Partial<AdminProductCreate>): Promise<Product> {
    const { collection_ids, ...productData } = data;
    const { error } = await supabase.from("products").update(productData).eq("id", Number(id));
    if (error) throw new Error(error.message);

    if (collection_ids) {
      await supabase.from("product_collections").delete().eq("product_id", Number(id));
      if (collection_ids.length > 0) {
        await supabase.from("product_collections").insert(
          collection_ids.map((cid) => ({ product_id: Number(id), collection_id: cid }))
        );
      }
    }

    return await adminApi.getProduct(id);
  },

  async deleteProduct(id: number | string): Promise<{ message: string }> {
    const { error } = await supabase.from("products").delete().eq("id", Number(id));
    if (error) throw new Error(error.message);
    return { message: "Product deleted" };
  },

  async archiveProduct(id: number | string): Promise<Product> {
    return await adminApi.updateProduct(id, { status: "archived" });
  },

  async publishProduct(id: number | string): Promise<Product> {
    return await adminApi.updateProduct(id, { status: "active" });
  },

  async bulkUpdateStatus(product_ids: number[], status: "draft" | "active" | "archived"): Promise<any> {
    const { error } = await supabase.from("products").update({ status }).in("id", product_ids);
    if (error) throw new Error(error.message);
    return { updated_count: product_ids.length };
  },

  async addVariant(productId: number | string, data: AdminVariantCreate): Promise<any> {
    const { data: v, error } = await supabase
      .from("product_variants")
      .insert({ ...data, product_id: Number(productId) })
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return v;
  },

  async updateVariant(productId: number | string, variantId: number | string, data: Partial<AdminVariantCreate>): Promise<any> {
    const { data: v, error } = await supabase
      .from("product_variants")
      .update(data)
      .eq("id", Number(variantId))
      .eq("product_id", Number(productId))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return v;
  },

  async deleteVariant(productId: number | string, variantId: number | string): Promise<any> {
    const { error } = await supabase
      .from("product_variants")
      .delete()
      .eq("id", Number(variantId))
      .eq("product_id", Number(productId));
    if (error) throw new Error(error.message);
    return { message: "Variant deleted" };
  },

  // ---------------------------------------------------------------------------
  // Product Media (Cloudflare R2 Direct Presigned Upload & Supabase Metadata)
  // ---------------------------------------------------------------------------

  async getProductImages(productId: number | string): Promise<any[]> {
    const { data, error } = await supabase
      .from("product_images")
      .select("*")
      .eq("product_id", Number(productId))
      .order("sort_order", { ascending: true });
    if (error) throw new Error(error.message);
    return data || [];
  },

  async requestMediaUploadIntent(
    productId: number | string,
    params: { filename: string; mime_type: string; size_bytes?: number }
  ): Promise<{
    upload_url: string;
    http_method: string;
    required_headers: Record<string, string>;
    storage_key: string;
    public_url: string;
    expires_in_seconds: number;
    is_mock?: boolean;
  }> {
    const res = await fetch("/api/media/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: Number(productId),
        filename: params.filename,
        mime_type: params.mime_type,
        size_bytes: params.size_bytes,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Failed to request upload intent" }));
      throw new Error(err.error || `Upload intent failed with status ${res.status}`);
    }

    return await res.json();
  },

  async confirmProductImageUpload(
    productId: number | string,
    data: {
      image_url: string;
      alt_text?: string;
      is_primary?: boolean;
      sort_order?: number;
    }
  ): Promise<any> {
    if (data.is_primary) {
      await supabase
        .from("product_images")
        .update({ is_primary: false })
        .eq("product_id", Number(productId));
    }

    const { data: img, error } = await supabase
      .from("product_images")
      .insert({
        product_id: Number(productId),
        image_url: data.image_url,
        alt_text: data.alt_text || "",
        is_primary: data.is_primary ?? false,
        sort_order: data.sort_order ?? 0,
      })
      .select("*")
      .single();

    if (error) throw new Error(error.message);
    return img;
  },

  async addProductImageUrl(
    productId: number | string,
    data: { image_url: string; alt_text?: string; is_primary?: boolean }
  ): Promise<any> {
    return await adminApi.confirmProductImageUpload(productId, data);
  },

  async uploadProductImage(
    productId: number | string,
    fileOrFormData: File | FormData,
    options?: { alt_text?: string; is_primary?: boolean }
  ): Promise<any> {
    let file: File;
    let altText = options?.alt_text;
    let isPrimary = options?.is_primary;

    if (typeof FormData !== "undefined" && fileOrFormData instanceof FormData) {
      file = fileOrFormData.get("file") as File;
      altText = (fileOrFormData.get("alt_text") as string) || altText;
      isPrimary = fileOrFormData.get("is_primary") === "true" || (isPrimary ?? false);
    } else {
      file = fileOrFormData as File;
    }

    if (!file) {
      throw new Error("No file provided for upload");
    }

    // 1. Get presigned R2 upload URL
    const intent = await adminApi.requestMediaUploadIntent(productId, {
      filename: file.name,
      mime_type: file.type || "image/jpeg",
      size_bytes: file.size,
    });

    // 2. Perform direct PUT to Cloudflare R2 (or simulated dev endpoint)
    if (!intent.is_mock) {
      const uploadRes = await fetch(intent.upload_url, {
        method: "PUT",
        headers: intent.required_headers,
        body: file,
      });

      if (!uploadRes.ok) {
        throw new Error(`Direct R2 upload failed with HTTP status ${uploadRes.status}`);
      }
    }

    // 3. Register image in database
    return await adminApi.confirmProductImageUpload(productId, {
      image_url: intent.public_url,
      alt_text: altText || file.name.replace(/\.[^/.]+$/, ""),
      is_primary: isPrimary ?? false,
    });
  },

  async reorderProductImages(
    productId: number | string,
    imageIds: number[]
  ): Promise<any[]> {
    for (let index = 0; index < imageIds.length; index++) {
      await supabase
        .from("product_images")
        .update({ sort_order: index })
        .eq("id", imageIds[index])
        .eq("product_id", Number(productId));
    }
    return await adminApi.getProductImages(productId);
  },

  async deleteProductImage(
    productId: number | string,
    imageId: number | string,
    storageKey?: string
  ): Promise<any> {
    // Delete record from Supabase
    const { error } = await supabase
      .from("product_images")
      .delete()
      .eq("id", Number(imageId))
      .eq("product_id", Number(productId));

    if (error) throw new Error(error.message);

    // If storageKey is provided or detectable, request R2 deletion
    if (storageKey) {
      await fetch(`/api/media/upload`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ storage_key: storageKey }),
      }).catch((e) => console.warn("Failed to delete object from R2:", e));
    }

    return { message: "Image deleted" };
  },

  async setPrimaryProductImage(productId: number | string, imageId: number | string): Promise<any> {
    await supabase.from("product_images").update({ is_primary: false }).eq("product_id", Number(productId));
    const { error } = await supabase.from("product_images").update({ is_primary: true }).eq("id", Number(imageId));
    if (error) throw new Error(error.message);
    return { message: "Primary image updated" };
  },

  // ---------------------------------------------------------------------------
  // 4. Orders & Management
  // ---------------------------------------------------------------------------

  async getOrders(params?: { status?: string; payment_status?: string; limit?: number; offset?: number }): Promise<any> {
    const limit = params?.limit || 20;
    const offset = params?.offset || 0;

    let query = supabase.from("orders").select("*, items:order_items(*)", { count: "exact" });
    if (params?.status) query = query.eq("status", params.status);
    if (params?.payment_status) query = query.eq("payment_status", params.payment_status);

    query = query.order("placed_at", { ascending: false }).range(offset, offset + limit - 1);
    const { data, count, error } = await query;
    if (error) throw new Error(error.message);
    return { items: data || [], total: count || 0 };
  },

  async getOrderDetail(id: number | string): Promise<any> {
    const { data, error } = await supabase
      .from("orders")
      .select("*, items:order_items(*), status_history:order_status_history(*)")
      .eq("id", Number(id))
      .single();
    if (error || !data) throw new Error(error?.message || `Order ${id} not found`);
    return data;
  },

  async confirmOrder(id: number | string): Promise<any> {
    const { data, error } = await supabase
      .from("orders")
      .update({ status: "confirmed" })
      .eq("id", Number(id))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async cancelOrder(id: number | string, reason: string): Promise<any> {
    const { data, error } = await supabase
      .from("orders")
      .update({ status: "cancelled", customer_note: reason })
      .eq("id", Number(id))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  // ---------------------------------------------------------------------------
  // 5. Payments
  // ---------------------------------------------------------------------------

  async getPayments(params?: { status?: string; method?: string; limit?: number; offset?: number }): Promise<any> {
    let query = supabase.from("payments").select("*, order:orders(order_number, customer_name)", { count: "exact" });
    if (params?.status) query = query.eq("status", params.status);
    query = query.order("created_at", { ascending: false }).range(params?.offset || 0, (params?.offset || 0) + (params?.limit || 20) - 1);
    const { data, count, error } = await query;
    if (error) throw new Error(error.message);
    return { items: data || [], total: count || 0 };
  },

  async collectCodCash(paymentId: number | string, amount: number, notes?: string): Promise<any> {
    const { data, error } = await supabase
      .from("payments")
      .update({ status: "paid", notes: notes || "COD Cash Collected" })
      .eq("id", Number(paymentId))
      .select("*")
      .single();
    if (error) throw new Error(error.message);

    // Also update order payment status
    if (data?.order_id) {
      await supabase.from("orders").update({ payment_status: "paid" }).eq("id", data.order_id);
    }
    return data;
  },

  // ---------------------------------------------------------------------------
  // 6. Customers
  // ---------------------------------------------------------------------------

  async getCustomers(params?: { search?: string; status?: string; limit?: number; offset?: number }): Promise<any> {
    let query = supabase.from("users").select("*, customer_profiles(*)", { count: "exact" }).eq("user_type", "customer");
    if (params?.status) query = query.eq("status", params.status);
    if (params?.search) query = query.ilike("email", `%${params.search}%`);
    query = query.order("created_at", { ascending: false }).range(params?.offset || 0, (params?.offset || 0) + (params?.limit || 20) - 1);
    const { data, count, error } = await query;
    if (error) throw new Error(error.message);
    return { items: data || [], total: count || 0 };
  },

  async getCustomerDetail(id: number | string): Promise<any> {
    const { data, error } = await supabase
      .from("users")
      .select("*, customer_profiles(*), addresses(*), orders(*)")
      .eq("id", Number(id))
      .single();
    if (error || !data) throw new Error(error?.message || `Customer ${id} not found`);
    return data;
  },

  async updateCustomerStatus(id: number | string, status: "active" | "suspended" | "banned", _reason?: string): Promise<any> {
    const { data, error } = await supabase
      .from("users")
      .update({ status })
      .eq("id", Number(id))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  // ---------------------------------------------------------------------------
  // 7. Returns & Refunds
  // ---------------------------------------------------------------------------

  async getReturns(params?: { status?: string; limit?: number; offset?: number }): Promise<any> {
    let query = supabase.from("return_requests").select("*, items:return_items(*), order:orders(order_number)", { count: "exact" });
    if (params?.status) query = query.eq("status", params.status);
    query = query.order("created_at", { ascending: false }).range(params?.offset || 0, (params?.offset || 0) + (params?.limit || 20) - 1);
    const { data, count, error } = await query;
    if (error) throw new Error(error.message);
    return { items: data || [], total: count || 0 };
  },

  // ---------------------------------------------------------------------------
  // 8. Audit Trail
  // ---------------------------------------------------------------------------

  async getAuditLogs(params?: { limit?: number; offset?: number; entity_type?: string }): Promise<{ items: AdminAuditLog[]; total: number }> {
    let query = supabase.from("audit_logs").select("*", { count: "exact" });
    if (params?.entity_type) query = query.eq("entity_type", params.entity_type);
    query = query.order("created_at", { ascending: false }).range(params?.offset || 0, (params?.offset || 0) + (params?.limit || 20) - 1);
    const { data, count, error } = await query;
    if (error) throw new Error(error.message);
    return { items: data || [], total: count || 0 };
  },

  // ---------------------------------------------------------------------------
  // 9. Offline Sales & POS
  // ---------------------------------------------------------------------------

  async getOfflineSales(params?: { search?: string; payment_method?: string; status?: string; limit?: number; offset?: number }): Promise<any> {
    let query = supabase.from("offline_sales").select("*, items:offline_sale_items(*)", { count: "exact" });
    if (params?.status) query = query.eq("status", params.status);
    if (params?.payment_method) query = query.eq("payment_method", params.payment_method);
    query = query.order("created_at", { ascending: false }).range(params?.offset || 0, (params?.offset || 0) + (params?.limit || 20) - 1);
    const { data, count, error } = await query;
    if (error) throw new Error(error.message);
    return { items: data || [], total: count || 0 };
  },

  async getOfflineSale(id: number | string): Promise<any> {
    const { data, error } = await supabase
      .from("offline_sales")
      .select("*, items:offline_sale_items(*)")
      .eq("id", Number(id))
      .single();
    if (error || !data) throw new Error(error?.message || `Offline sale ${id} not found`);
    return data;
  },

  async createOfflineSale(data: {
    customer_name?: string;
    customer_phone?: string;
    customer_email?: string;
    payment_method: string;
    discount_amount?: number;
    tax_amount?: number;
    notes?: string;
    items: Array<{
      variant_id: number;
      quantity: number;
      unit_price_override?: number;
    }>;
  }): Promise<any> {
    const { data: result, error } = await supabase.rpc("create_offline_sale", {
      p_sale_data: data,
    });
    if (error) throw new Error(`POS transaction failed: ${error.message}`);
    return result;
  },

  async voidOfflineSale(id: number | string): Promise<any> {
    const { data, error } = await supabase
      .from("offline_sales")
      .update({ status: "voided" })
      .eq("id", Number(id))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data;
  },
};
