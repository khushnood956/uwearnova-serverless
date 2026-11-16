/**
 * Customer Payments API (Supabase Backend)
 */

import { supabase } from "@/lib/supabase/client";

export interface PaymentInitiateRequest {
  order_id: number;
  provider_code?: string;
  return_url?: string;
  cancel_url?: string;
}

export interface PaymentInitiateResponse {
  payment_id: number;
  order_id: number;
  order_number: string;
  provider_code: string;
  provider_reference: string;
  redirect_url?: string | null;
  client_token?: string | null;
  status: string;
  amount: number;
  currency_code: string;
}

export interface PaymentResponse {
  id: number;
  order_id: number;
  order_number: string;
  payment_method: string;
  provider_code: string;
  provider_reference?: string | null;
  status: string;
  currency_code: string;
  amount: number;
  amount_collected: number;
  amount_outstanding: number;
  initiated_at: string;
  confirmed_at?: string | null;
  dispatched_at?: string | null;
  collected_at?: string | null;
  reconciled_at?: string | null;
}

export const paymentsApi = {
  async initiatePayment(data: PaymentInitiateRequest): Promise<PaymentInitiateResponse> {
    const { data: order, error: oError } = await supabase
      .from("orders")
      .select("id, order_number, grand_total, currency_code")
      .eq("id", data.order_id)
      .single();

    if (oError || !order) throw new Error(oError?.message || "Order not found");

    const providerCode = data.provider_code || "cod";
    const ref = `PAY-${order.order_number}`;

    const { data: payment, error: pError } = await supabase
      .from("payments")
      .insert({
        order_id: order.id,
        provider_code: providerCode,
        payment_method: providerCode,
        status: "pending",
        amount: order.grand_total,
        currency_code: order.currency_code,
        provider_reference: ref,
      })
      .select("*")
      .single();

    if (pError || !payment) throw new Error(pError?.message || "Failed to initiate payment");

    return {
      payment_id: payment.id,
      order_id: order.id,
      order_number: order.order_number,
      provider_code: providerCode,
      provider_reference: ref,
      redirect_url: null,
      client_token: null,
      status: "pending",
      amount: Number(payment.amount),
      currency_code: payment.currency_code,
    };
  },

  async getOrderPayment(orderNumber: string): Promise<PaymentResponse> {
    const { data: order, error: oError } = await supabase
      .from("orders")
      .select("id, order_number")
      .eq("order_number", orderNumber)
      .single();

    if (oError || !order) throw new Error(oError?.message || `Order '${orderNumber}' not found`);

    const { data: payment, error: pError } = await supabase
      .from("payments")
      .select("*")
      .eq("order_id", order.id)
      .order("created_at", { ascending: false })
      .limit(1)
      .single();

    if (pError || !payment) throw new Error(pError?.message || "Payment record not found");

    const amount = Number(payment.amount);
    const isPaid = payment.status === "paid";

    return {
      id: payment.id,
      order_id: order.id,
      order_number: order.order_number,
      payment_method: payment.payment_method,
      provider_code: payment.provider_code,
      provider_reference: payment.provider_reference,
      status: payment.status,
      currency_code: payment.currency_code,
      amount,
      amount_collected: isPaid ? amount : 0,
      amount_outstanding: isPaid ? 0 : amount,
      initiated_at: payment.created_at,
      confirmed_at: isPaid ? payment.updated_at : null,
      dispatched_at: null,
      collected_at: isPaid ? payment.updated_at : null,
      reconciled_at: isPaid ? payment.updated_at : null,
    };
  },

  async confirmCodPayment(orderNumber: string, data: { confirmed: boolean; notes?: string }): Promise<PaymentResponse> {
    const current = await paymentsApi.getOrderPayment(orderNumber);

    if (data.confirmed) {
      await supabase
        .from("payments")
        .update({ status: "authorized", notes: data.notes || "Customer confirmed Cash on Delivery" })
        .eq("id", current.id);
    }

    return await paymentsApi.getOrderPayment(orderNumber);
  },
};
