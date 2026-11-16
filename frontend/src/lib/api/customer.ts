/**
 * Customer Account, Address Book & Profile API (Supabase Backend)
 * Direct database querying with Row Level Security.
 */

import { supabase } from "@/lib/supabase/client";

export interface CustomerProfile {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  user_type: string;
  status: string;
  created_at: string;
}

export interface CustomerPreferences {
  marketing_email: boolean;
  marketing_sms: boolean;
  marketing_whatsapp: boolean;
  language: string;
  currency: string;
}

export interface CustomerAddress {
  id: number;
  label?: string | null;
  full_name: string;
  phone: string;
  street_address: string;
  apartment_suite?: string | null;
  city: string;
  province?: string | null;
  postal_code?: string | null;
  delivery_instructions?: string | null;
  is_default: boolean;
}

export interface CustomerOrderItem {
  id: number;
  product_id: number;
  product_name: string;
  product_slug: string;
  variant_sku: string;
  size: string;
  color_name: string;
  image_url?: string | null;
  unit_price: number | string;
  quantity: number;
  line_total: number | string;
}

export interface CustomerShipment {
  id: number;
  tracking_number: string;
  courier_name: string;
  status: string;
  shipped_at?: string | null;
  delivered_at?: string | null;
}

export interface OrderStatusTimelineItem {
  id: number;
  status: string;
  notes?: string | null;
  created_at: string;
}

export interface CustomerOrderDetail {
  id: number;
  order_number: string;
  status: string;
  payment_method: string;
  payment_status: string;
  subtotal: number | string;
  shipping_fee: number | string;
  discount_amount: number | string;
  grand_total: number | string;
  created_at: string;
  shipping_address: any;
  items: CustomerOrderItem[];
  shipments: CustomerShipment[];
  timeline: OrderStatusTimelineItem[];
}

export interface CustomerOrderListResponse {
  items: CustomerOrderDetail[];
  total: number;
  limit: number;
  offset: number;
}

export interface CustomerReturnItem {
  id: number;
  order_item_id: number;
  product_name: string;
  variant_sku: string;
  quantity: number;
  reason: string;
  condition: string;
  status: string;
}

export interface CustomerReturnDetail {
  id: number;
  return_number: string;
  order_number: string;
  request_type: "return" | "exchange";
  status: string;
  refund_status?: string | null;
  refund_amount?: number | string | null;
  items: CustomerReturnItem[];
  created_at: string;
  updated_at: string;
}

export interface CustomerSecurityOverview {
  email: string;
  is_verified: boolean;
  active_sessions_count: number;
  last_login_at?: string | null;
  last_password_change_at?: string | null;
}

async function getDomainUserId(): Promise<number> {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Authentication required.");

  const { data, error } = await supabase
    .from("users")
    .select("id")
    .eq("auth_user_id", user.id)
    .single();

  if (error || !data) throw new Error("Domain user record not found.");
  return data.id;
}

export const customerApi = {
  // ---------------------------------------------------------------------------
  // Profile & Preferences
  // ---------------------------------------------------------------------------

  async getProfile(): Promise<CustomerProfile> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("Authentication required.");

    const { data: u, error } = await supabase
      .from("users")
      .select("id, email, phone, status, user_type, created_at, customer_profiles(first_name, last_name, phone)")
      .eq("auth_user_id", user.id)
      .single();

    if (error || !u) throw new Error(error?.message || "Profile not found.");

    const cp = Array.isArray(u.customer_profiles) ? u.customer_profiles[0] : u.customer_profiles;

    return {
      id: u.id,
      email: u.email,
      first_name: cp?.first_name || user.user_metadata?.first_name || "",
      last_name: cp?.last_name || user.user_metadata?.last_name || "",
      phone: u.phone || cp?.phone || user.user_metadata?.phone || null,
      status: u.status,
      user_type: u.user_type,
      created_at: u.created_at,
    };
  },

  async updateProfile(data: { first_name?: string; last_name?: string; phone?: string }): Promise<CustomerProfile> {
    const domainUserId = await getDomainUserId();

    if (data.first_name !== undefined || data.last_name !== undefined || data.phone !== undefined) {
      await supabase
        .from("customer_profiles")
        .update({
          ...(data.first_name ? { first_name: data.first_name } : {}),
          ...(data.last_name ? { last_name: data.last_name } : {}),
          ...(data.phone ? { phone: data.phone } : {}),
        })
        .eq("user_id", domainUserId);

      if (data.phone) {
        await supabase.from("users").update({ phone: data.phone }).eq("id", domainUserId);
      }
    }

    return await customerApi.getProfile();
  },

  async getPreferences(): Promise<CustomerPreferences> {
    const domainUserId = await getDomainUserId();

    const { data } = await supabase
      .from("customer_profiles")
      .select("preferences")
      .eq("user_id", domainUserId)
      .single();

    return (
      data?.preferences || {
        marketing_email: false,
        marketing_sms: false,
        marketing_whatsapp: false,
        language: "en",
        currency: "PKR",
      }
    );
  },

  async updatePreferences(data: Partial<CustomerPreferences>): Promise<CustomerPreferences> {
    const domainUserId = await getDomainUserId();
    const current = await customerApi.getPreferences();
    const updated = { ...current, ...data };

    await supabase
      .from("customer_profiles")
      .update({ preferences: updated })
      .eq("user_id", domainUserId);

    return updated;
  },

  // ---------------------------------------------------------------------------
  // Address Book
  // ---------------------------------------------------------------------------

  async getAddresses(): Promise<{ items: CustomerAddress[]; total: number }> {
    const domainUserId = await getDomainUserId();

    const { data, count, error } = await supabase
      .from("addresses")
      .select("*", { count: "exact" })
      .eq("user_id", domainUserId)
      .order("is_default", { ascending: false })
      .order("id", { ascending: false });

    if (error) throw new Error(error.message);
    return { items: data || [], total: count || 0 };
  },

  async createAddress(data: Omit<CustomerAddress, "id" | "is_default"> & { is_default?: boolean }): Promise<CustomerAddress> {
    const domainUserId = await getDomainUserId();

    if (data.is_default) {
      await supabase.from("addresses").update({ is_default: false }).eq("user_id", domainUserId);
    }

    const { data: newAddr, error } = await supabase
      .from("addresses")
      .insert({ ...data, user_id: domainUserId })
      .select("*")
      .single();

    if (error || !newAddr) throw new Error(error?.message || "Failed to create address");
    return newAddr;
  },

  async updateAddress(id: number, data: Partial<CustomerAddress>): Promise<CustomerAddress> {
    const domainUserId = await getDomainUserId();

    if (data.is_default) {
      await supabase.from("addresses").update({ is_default: false }).eq("user_id", domainUserId);
    }

    const { data: updated, error } = await supabase
      .from("addresses")
      .update(data)
      .eq("id", id)
      .eq("user_id", domainUserId)
      .select("*")
      .single();

    if (error || !updated) throw new Error(error?.message || "Failed to update address");
    return updated;
  },

  async deleteAddress(id: number): Promise<void> {
    const domainUserId = await getDomainUserId();
    const { error } = await supabase.from("addresses").delete().eq("id", id).eq("user_id", domainUserId);
    if (error) throw new Error(error.message);
  },

  async setDefaultAddress(id: number): Promise<CustomerAddress> {
    return await customerApi.updateAddress(id, { is_default: true });
  },

  // ---------------------------------------------------------------------------
  // Orders
  // ---------------------------------------------------------------------------

  async getOrders(params?: { limit?: number; offset?: number }): Promise<CustomerOrderListResponse> {
    const domainUserId = await getDomainUserId();
    const limit = params?.limit || 20;
    const offset = params?.offset || 0;

    const { data, count, error } = await supabase
      .from("orders")
      .select("*, items:order_items(*), shipments:shipments(*), timeline:order_status_history(*)", { count: "exact" })
      .eq("user_id", domainUserId)
      .order("placed_at", { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) throw new Error(error.message);

    const items: CustomerOrderDetail[] = (data || []).map((o: any) => ({
      id: o.id,
      order_number: o.order_number,
      status: o.status,
      payment_method: o.payment_method,
      payment_status: o.payment_status,
      subtotal: Number(o.subtotal),
      shipping_fee: Number(o.shipping_fee),
      discount_amount: Number(o.discount_amount),
      grand_total: Number(o.grand_total),
      created_at: o.placed_at || o.created_at,
      shipping_address: o.shipping_address,
      items: (o.items || []).map((i: any) => ({
        id: i.id,
        product_id: i.variant_id || 0,
        product_name: i.product_name,
        product_slug: i.product_slug || "",
        variant_sku: i.sku,
        size: i.size,
        color_name: i.color,
        image_url: i.image_url,
        unit_price: Number(i.unit_price),
        quantity: i.quantity,
        line_total: Number(i.line_total),
      })),
      shipments: o.shipments || [],
      timeline: o.timeline || [],
    }));

    return { items, total: count || items.length, limit, offset };
  },

  async getOrderDetail(orderNumber: string): Promise<CustomerOrderDetail> {
    const domainUserId = await getDomainUserId();

    const { data: o, error } = await supabase
      .from("orders")
      .select("*, items:order_items(*), shipments:shipments(*), timeline:order_status_history(*)")
      .eq("order_number", orderNumber)
      .eq("user_id", domainUserId)
      .single();

    if (error || !o) throw new Error(error?.message || `Order '${orderNumber}' not found`);

    return {
      id: o.id,
      order_number: o.order_number,
      status: o.status,
      payment_method: o.payment_method,
      payment_status: o.payment_status,
      subtotal: Number(o.subtotal),
      shipping_fee: Number(o.shipping_fee),
      discount_amount: Number(o.discount_amount),
      grand_total: Number(o.grand_total),
      created_at: o.placed_at || o.created_at,
      shipping_address: o.shipping_address,
      items: (o.items || []).map((i: any) => ({
        id: i.id,
        product_id: i.variant_id || 0,
        product_name: i.product_name,
        product_slug: i.product_slug || "",
        variant_sku: i.sku,
        size: i.size,
        color_name: i.color,
        image_url: i.image_url,
        unit_price: Number(i.unit_price),
        quantity: i.quantity,
        line_total: Number(i.line_total),
      })),
      shipments: o.shipments || [],
      timeline: o.timeline || [],
    };
  },

  // ---------------------------------------------------------------------------
  // Returns & Exchanges
  // ---------------------------------------------------------------------------

  async getReturns(params?: { page?: number; page_size?: number }): Promise<{ items: CustomerReturnDetail[]; total: number }> {
    const domainUserId = await getDomainUserId();

    const { data, count, error } = await supabase
      .from("return_requests")
      .select("*, items:return_items(*), order:orders(order_number)", { count: "exact" })
      .eq("user_id", domainUserId)
      .order("created_at", { ascending: false });

    if (error) throw new Error(error.message);

    const items: CustomerReturnDetail[] = (data || []).map((r: any) => ({
      id: r.id,
      return_number: r.return_number,
      order_number: r.order?.order_number || "",
      request_type: r.request_type,
      status: r.status,
      refund_status: r.refund_status,
      refund_amount: r.refund_amount ? Number(r.refund_amount) : null,
      items: r.items || [],
      created_at: r.created_at,
      updated_at: r.updated_at,
    }));

    return { items, total: count || items.length };
  },

  async getReturnDetail(id: number): Promise<CustomerReturnDetail> {
    const domainUserId = await getDomainUserId();

    const { data: r, error } = await supabase
      .from("return_requests")
      .select("*, items:return_items(*), order:orders(order_number)")
      .eq("id", id)
      .eq("user_id", domainUserId)
      .single();

    if (error || !r) throw new Error(error?.message || "Return request not found");

    return {
      id: r.id,
      return_number: r.return_number,
      order_number: r.order?.order_number || "",
      request_type: r.request_type,
      status: r.status,
      refund_status: r.refund_status,
      refund_amount: r.refund_amount ? Number(r.refund_amount) : null,
      items: r.items || [],
      created_at: r.created_at,
      updated_at: r.updated_at,
    };
  },

  async submitReturn(data: {
    order_number: string;
    request_type: "return" | "exchange";
    reason: string;
    items: Array<{ order_item_id: number; quantity: number; reason: string }>;
  }): Promise<CustomerReturnDetail> {
    const domainUserId = await getDomainUserId();

    // Verify order
    const { data: order } = await supabase
      .from("orders")
      .select("id")
      .eq("order_number", data.order_number)
      .eq("user_id", domainUserId)
      .single();

    if (!order) throw new Error(`Order '${data.order_number}' not found or does not belong to you.`);

    const returnNumber = "RET-" + Date.now().toString(36).toUpperCase();

    const { data: newRet, error: retError } = await supabase
      .from("return_requests")
      .insert({
        return_number: returnNumber,
        order_id: order.id,
        user_id: domainUserId,
        request_type: data.request_type,
        reason: data.reason,
        status: "submitted",
      })
      .select("*")
      .single();

    if (retError || !newRet) throw new Error(retError?.message || "Failed to submit return request");

    // Insert return items
    if (data.items.length > 0) {
      await supabase.from("return_items").insert(
        data.items.map((it) => ({
          return_request_id: newRet.id,
          order_item_id: it.order_item_id,
          quantity: it.quantity,
          reason: it.reason,
          status: "pending",
        }))
      );
    }

    return await customerApi.getReturnDetail(newRet.id);
  },

  // ---------------------------------------------------------------------------
  // Security
  // ---------------------------------------------------------------------------

  async getSecurityOverview(): Promise<CustomerSecurityOverview> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("Authentication required.");

    return {
      email: user.email || "",
      is_verified: Boolean(user.email_confirmed_at),
      active_sessions_count: 1,
      last_login_at: user.last_sign_in_at || null,
      last_password_change_at: null,
    };
  },

  async changePassword(data: { current_password: string; new_password: string }): Promise<{ message: string }> {
    const { error } = await supabase.auth.updateUser({ password: data.new_password });
    if (error) throw new Error(error.message);
    return { message: "Password updated successfully." };
  },

  async revokeSessions(): Promise<{ message: string }> {
    await supabase.auth.signOut({ scope: "others" });
    return { message: "All other sessions have been revoked." };
  },
};
