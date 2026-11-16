/**
 * Storefront Order & Checkout API (Supabase Backend)
 * Implements atomic transactional checkout via PostgreSQL RPC (place_order_atomic).
 */

import { supabase } from "@/lib/supabase/client";
import { cartApi } from "./cart";

export interface AddressSnapshot {
  full_name: string;
  phone: string;
  address_line_1: string;
  address_line_2?: string | null;
  city: string;
  postal_code?: string | null;
  country_code?: string;
}

export interface CheckoutRequest {
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  shipping_address: AddressSnapshot;
  shipping_method_code?: string;
  payment_method?: string; // "cod" | "card" | "mock"
  customer_note?: string | null;
  coupon_code?: string | null;
  idempotency_key?: string | null;
}

export interface OrderItemResponse {
  id: number;
  product_id?: number | null;
  variant_id?: number | null;
  product_name: string;
  product_slug: string;
  sku: string;
  size: string;
  color: string;
  unit_price: number;
  quantity: number;
  line_discount: number;
  line_total: number;
  image_url?: string | null;
}

export interface OrderStatusHistoryResponse {
  id: number;
  from_status: string;
  to_status: string;
  note?: string | null;
  created_at: string;
}

export interface OrderResponse {
  id: number;
  order_number: string;
  status: string;
  payment_status: string;
  fulfillment_status: string;
  payment_method: string;
  currency_code: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  subtotal: number;
  discount_total: number;
  shipping_total: number;
  tax_total: number;
  grand_total: number;
  shipping_method_code: string;
  shipping_method_name: string;
  shipping_address: AddressSnapshot;
  customer_note?: string | null;
  items: OrderItemResponse[];
  status_history: OrderStatusHistoryResponse[];
  placed_at: string;
  created_at: string;
}

export const ordersApi = {
  /**
   * Atomic checkout mutation executing through PostgreSQL RPC
   */
  async checkout(data: CheckoutRequest, idempotencyKey?: string): Promise<OrderResponse> {
    // 1. Fetch current cart items to assemble trusted payload
    const activeCart = await cartApi.getCart();

    if (!activeCart.items || activeCart.items.length === 0) {
      throw new Error("Cannot checkout with an empty shopping cart.");
    }

    const itemsPayload = activeCart.items.map((item) => ({
      variant_id: item.variant_id,
      product_name: item.product_name,
      product_slug: item.product_slug,
      sku: item.sku,
      size: item.size,
      color: item.color,
      quantity: item.quantity,
      image_url: item.image_url,
    }));

    const rpcPayload = {
      customer_name: data.customer_name,
      customer_email: data.customer_email,
      customer_phone: data.customer_phone,
      shipping_address: data.shipping_address,
      shipping_method_code: data.shipping_method_code || "standard",
      shipping_method_name: "Standard Delivery",
      shipping_fee: Number(activeCart.shipping_estimate) || 350.00,
      discount_amount: Number(activeCart.discount_total) || 0.00,
      payment_method: data.payment_method || "cod",
      customer_note: data.customer_note || null,
      idempotency_key: idempotencyKey || data.idempotency_key || null,
      cart_id: activeCart.id || null,
      items: itemsPayload,
    };

    // 2. Call place_order_atomic RPC
    const { data: result, error } = await supabase.rpc("place_order_atomic", {
      p_order_data: rpcPayload,
    });

    if (error) {
      throw new Error(`Checkout transaction failed: ${error.message}`);
    }

    const orderNumber = result?.order_number;
    if (!orderNumber) {
      throw new Error("Failed to receive order confirmation number from database.");
    }

    // 3. Clear local storage cart if fallback was used
    cartApi.clearCart().catch(() => {});

    // 4. Return complete order snapshot
    return await ordersApi.getOrder(orderNumber);
  },

  /**
   * Retrieve order details by unique order number
   */
  async getOrder(orderNumber: string): Promise<OrderResponse> {
    const { data, error } = await supabase
      .from("orders")
      .select("*, items:order_items(*), status_history:order_status_history(*)")
      .eq("order_number", orderNumber)
      .single();

    if (error || !data) {
      throw new Error(error?.message || `Order '${orderNumber}' not found`);
    }

    return {
      id: data.id,
      order_number: data.order_number,
      status: data.status,
      payment_status: data.payment_status,
      fulfillment_status: data.fulfillment_status,
      payment_method: data.payment_method,
      currency_code: data.currency_code,
      customer_name: data.customer_name,
      customer_email: data.customer_email,
      customer_phone: data.customer_phone,
      subtotal: Number(data.subtotal),
      discount_total: Number(data.discount_amount),
      shipping_total: Number(data.shipping_fee),
      tax_total: Number(data.tax_amount),
      grand_total: Number(data.grand_total),
      shipping_method_code: data.shipping_method_code,
      shipping_method_name: data.shipping_method_name,
      shipping_address: data.shipping_address,
      customer_note: data.customer_note,
      items: (data.items || []).map((i: any) => ({
        ...i,
        unit_price: Number(i.unit_price),
        line_total: Number(i.line_total),
        line_discount: Number(i.line_discount || 0),
      })),
      status_history: (data.status_history || []).sort(
        (a: any, b: any) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      ),
      placed_at: data.placed_at,
      created_at: data.created_at,
    };
  },
};
