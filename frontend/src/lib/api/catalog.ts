/**
 * Public Catalogue, Categories, and Collections API (Supabase Backend)
 * Directly queries Supabase PostgreSQL tables using PostgREST and RLS.
 */

import { supabase } from "@/lib/supabase/client";
import {
  Category,
  CategoryTree,
  Collection,
  Product,
  ProductListResponse,
  ProductQueryParams,
} from "./types";

// In-memory request deduplication and client-side caching to eliminate
// remote round-trip latency to Tokyo on repeated navigations.
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
let categoryTreePromise: Promise<CategoryTree[]> | null = null;
let categoryTreeCache: { data: CategoryTree[]; expiresAt: number } | null = null;
const categoryCache = new Map<string, { data: Category; expiresAt: number }>();

export const catalogApi = {
  /**
   * Retrieve hierarchical category taxonomy tree for dynamic department navigation.
   * Deduplicates concurrent calls (e.g. Navbar + MobileNav) into a single remote round-trip.
   */
  async getCategoryTree(): Promise<CategoryTree[]> {
    if (categoryTreeCache && Date.now() < categoryTreeCache.expiresAt) {
      return categoryTreeCache.data;
    }

    if (categoryTreePromise) {
      return categoryTreePromise;
    }

    categoryTreePromise = (async () => {
      try {
        const { data, error } = await supabase
          .from("categories")
          .select("*")
          .eq("is_active", true)
          .order("sort_order", { ascending: true });

        if (error) {
          console.warn("Failed to fetch categories from Supabase:", error.message);
          return [];
        }

        const categories: Category[] = data || [];
        const roots: CategoryTree[] = [];
        const map = new Map<number | string, CategoryTree>();

        categories.forEach((cat) => {
          map.set(cat.id, { ...cat, children: [] });
          // Populate single category cache
          categoryCache.set(String(cat.id), { data: cat, expiresAt: Date.now() + CACHE_TTL_MS });
          if (cat.slug) {
            categoryCache.set(cat.slug, { data: cat, expiresAt: Date.now() + CACHE_TTL_MS });
          }
        });

        categories.forEach((cat) => {
          const node = map.get(cat.id);
          if (!node) return;
          if (cat.parent_id && map.has(cat.parent_id)) {
            map.get(cat.parent_id)!.children.push(node);
          } else if (!cat.parent_id) {
            roots.push(node);
          }
        });

        categoryTreeCache = { data: roots, expiresAt: Date.now() + CACHE_TTL_MS };
        return roots;
      } finally {
        categoryTreePromise = null;
      }
    })();

    return categoryTreePromise;
  },

  /**
   * List storefront categories with optional parent filtering or roots-only flag.
   */
  async getCategories(params?: { parent_id?: number; roots_only?: boolean }): Promise<Category[]> {
    let query = supabase.from("categories").select("*").eq("is_active", true);

    if (params?.roots_only) {
      query = query.is("parent_id", null);
    } else if (params?.parent_id !== undefined) {
      query = query.eq("parent_id", params.parent_id);
    }

    query = query.order("sort_order", { ascending: true });

    const { data, error } = await query;
    if (error) {
      console.warn("Error fetching categories:", error.message);
      return [];
    }
    return data || [];
  },

  /**
   * Get single category by slug or numeric ID with in-memory cache lookup.
   */
  async getCategory(identifier: string): Promise<Category> {
    const cached = categoryCache.get(identifier);
    if (cached && Date.now() < cached.expiresAt) {
      return cached.data;
    }

    const isId = /^\d+$/.test(identifier);
    const query = supabase.from("categories").select("*");

    const { data, error } = isId
      ? await query.eq("id", Number(identifier)).single()
      : await query.eq("slug", identifier).single();

    if (error || !data) {
      throw new Error(error?.message || `Category '${identifier}' not found`);
    }

    categoryCache.set(String(data.id), { data, expiresAt: Date.now() + CACHE_TTL_MS });
    if (data.slug) {
      categoryCache.set(data.slug, { data, expiresAt: Date.now() + CACHE_TTL_MS });
    }

    return data;
  },

  /**
   * List active curated collections for seasonal groupings.
   */
  async getCollections(): Promise<Collection[]> {
    const { data, error } = await supabase
      .from("collections")
      .select("*")
      .eq("is_active", true)
      .order("sort_order", { ascending: true });

    if (error) {
      console.warn("Error fetching collections:", error.message);
      return [];
    }
    return data || [];
  },

  /**
   * Search, filter, and paginate storefront products.
   */
  async getProducts(params?: ProductQueryParams): Promise<ProductListResponse> {
    let query = supabase
      .from("products")
      .select("*, category:categories(*), variants:product_variants(*), images:product_images(*)", { count: "exact" })
      .eq("status", "active");

    if (params?.category_id) {
      query = query.eq("category_id", params.category_id);
    }

    if (params?.category_slug) {
      let catId: number | null = null;
      let childIds: number[] = [];

      const cached = categoryCache.get(params.category_slug);
      if (cached && Date.now() < cached.expiresAt) {
        catId = Number(cached.data.id);
      }

      if (!catId) {
        const { data: cat } = await supabase
          .from("categories")
          .select("id, children:categories!parent_id(id)")
          .eq("slug", params.category_slug)
          .maybeSingle();

        if (cat) {
          catId = Number((cat as any).id);
          childIds = Array.isArray((cat as any).children)
            ? (cat as any).children.map((c: any) => Number(c.id))
            : [];
        }
      } else {
        const { data: subCats } = await supabase
          .from("categories")
          .select("id")
          .eq("parent_id", catId);
        childIds = (subCats || []).map((s: any) => Number(s.id));
      }

      if (catId) {
        const catIds = [catId, ...childIds];
        query = query.in("category_id", catIds);
      }
    }

    if (params?.min_price !== undefined) {
      query = query.gte("price", params.min_price);
    }
    if (params?.max_price !== undefined) {
      query = query.lte("price", params.max_price);
    }
    if (params?.is_featured !== undefined) {
      query = query.eq("is_featured", params.is_featured);
    }
    if (params?.is_trending !== undefined) {
      query = query.eq("is_trending", params.is_trending);
    }
    if (params?.is_new_arrival !== undefined) {
      query = query.eq("is_new_arrival", params.is_new_arrival);
    }
    if (params?.search) {
      query = query.ilike("name", `%${params.search}%`);
    }

    // Sort order
    if (params?.sort_by === "price_asc") {
      query = query.order("price", { ascending: true });
    } else if (params?.sort_by === "price_desc") {
      query = query.order("price", { ascending: false });
    } else if (params?.sort_by === "featured") {
      query = query.order("is_featured", { ascending: false }).order("created_at", { ascending: false });
    } else {
      query = query.order("created_at", { ascending: false });
    }

    // Pagination
    const limit = params?.limit || params?.page_size || 20;
    const offset = params?.offset || 0;
    query = query.range(offset, offset + limit - 1);

    const { data, count, error } = await query;

    if (error) {
      console.warn("Error querying products from Supabase:", error.message);
      return { items: [], total: 0, limit, offset };
    }

    const items: Product[] = (data || []).map((p: any) => ({
      ...p,
      variants: (p.variants || []).filter((v: any) => v.is_active),
      images: (p.images || []).sort((a: any, b: any) => a.sort_order - b.sort_order),
    }));

    return {
      items,
      total: count || items.length,
      limit,
      offset,
    };
  },

  /**
   * Retrieve single product with full variant inventory and image gallery by URL slug.
   */
  async getProductBySlug(slug: string): Promise<Product> {
    const { data, error } = await supabase
      .from("products")
      .select("*, category:categories(*), variants:product_variants(*), images:product_images(*)")
      .eq("slug", slug)
      .single();

    if (error || !data) {
      throw new Error(error?.message || `Product with slug '${slug}' not found`);
    }

    return {
      ...data,
      variants: (data.variants || []).filter((v: any) => v.is_active),
      images: (data.images || []).sort((a: any, b: any) => a.sort_order - b.sort_order),
    };
  },
};
