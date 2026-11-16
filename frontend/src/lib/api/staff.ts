/**
 * Staff Operations & Work Queues API (Supabase Backend)
 */

import { supabase } from "@/lib/supabase/client";

export interface StaffDashboardSummary {
  staff_name: string;
  assigned_role: string;
  pending_orders_count?: number;
  pending_fulfillments_count?: number;
  low_stock_alerts_count?: number;
  open_support_cases_count?: number;
  assigned_tasks_count?: number;
}

export interface StaffTask {
  id: number;
  title: string;
  description?: string;
  task_type: string;
  priority: "low" | "medium" | "high" | "urgent";
  status: "pending" | "in_progress" | "completed" | "cancelled";
  due_date?: string;
  created_at: string;
}

export const staffApi = {
  async getDashboardSummary(): Promise<StaffDashboardSummary> {
    const { count: pendingOrders } = await supabase
      .from("orders")
      .select("id", { count: "exact", head: true })
      .eq("status", "pending_confirmation");

    const { count: pendingShipments } = await supabase
      .from("shipments")
      .select("id", { count: "exact", head: true })
      .in("status", ["manifested", "picked_up"]);

    const { count: lowStock } = await supabase
      .from("v_low_stock_alerts")
      .select("sku", { count: "exact", head: true });

    const { count: openTickets } = await supabase
      .from("support_tickets")
      .select("id", { count: "exact", head: true })
      .eq("status", "open");

    return {
      staff_name: "Staff Associate",
      assigned_role: "Operations Specialist",
      pending_orders_count: pendingOrders || 0,
      pending_fulfillments_count: pendingShipments || 0,
      low_stock_alerts_count: lowStock || 0,
      open_support_cases_count: openTickets || 0,
      assigned_tasks_count: 0,
    };
  },

  async getOrderQueue(): Promise<any> {
    const { data, error } = await supabase
      .from("orders")
      .select("*, items:order_items(*)")
      .eq("status", "pending_confirmation")
      .order("placed_at", { ascending: true });
    if (error) throw new Error(error.message);
    return data || [];
  },

  async getFulfillmentQueue(): Promise<any> {
    const { data, error } = await supabase
      .from("shipments")
      .select("*, order:orders(order_number, customer_name, shipping_address)")
      .in("status", ["manifested", "picked_up"])
      .order("created_at", { ascending: true });
    if (error) throw new Error(error.message);
    return data || [];
  },

  async getInventoryQueue(): Promise<any> {
    const { data, error } = await supabase.from("v_low_stock_alerts").select("*");
    if (error) throw new Error(error.message);
    return data || [];
  },

  async getReturnsQueue(): Promise<any> {
    const { data, error } = await supabase
      .from("return_requests")
      .select("*, items:return_items(*), order:orders(order_number)")
      .eq("status", "submitted")
      .order("created_at", { ascending: true });
    if (error) throw new Error(error.message);
    return data || [];
  },

  async getSupportQueue(): Promise<any> {
    const { data, error } = await supabase
      .from("support_tickets")
      .select("*")
      .eq("status", "open")
      .order("created_at", { ascending: true });
    if (error) throw new Error(error.message);
    return data || [];
  },

  async getMyTasks(): Promise<{ items: StaffTask[]; total: number }> {
    const { data, count, error } = await supabase
      .from("staff_tasks")
      .select("*", { count: "exact" })
      .order("created_at", { ascending: false });
    if (error) throw new Error(error.message);
    return { items: data || [], total: count || 0 };
  },

  async updateTaskStatus(taskId: number | string, status: "in_progress" | "completed" | "cancelled"): Promise<any> {
    const { data, error } = await supabase
      .from("staff_tasks")
      .update({ status })
      .eq("id", Number(taskId))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async processOrder(orderId: number | string, action: string, notes?: string): Promise<any> {
    const targetStatus = action === "confirm" ? "confirmed" : action === "cancel" ? "cancelled" : "processing";
    const { data, error } = await supabase
      .from("orders")
      .update({ status: targetStatus })
      .eq("id", Number(orderId))
      .select("*")
      .single();

    if (error) throw new Error(error.message);

    await supabase.from("order_status_history").insert({
      order_id: Number(orderId),
      from_status: "pending_confirmation",
      to_status: targetStatus,
      notes: notes || `Staff executed: ${action}`,
    });

    return data;
  },

  async packShipment(shipmentId: number | string, _package_weight_kg?: number): Promise<any> {
    const { data, error } = await supabase
      .from("shipments")
      .update({ status: "in_transit" })
      .eq("id", Number(shipmentId))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async dispatchShipment(shipmentId: number | string, courier_tracking_number: string): Promise<any> {
    const { data, error } = await supabase
      .from("shipments")
      .update({ status: "in_transit", tracking_number: courier_tracking_number, shipped_at: new Date().toISOString() })
      .eq("id", Number(shipmentId))
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async receiveStock(variant_id: number, quantity: number, reference_note?: string): Promise<any> {
    // 1. Fetch current stock
    const { data: v } = await supabase
      .from("product_variants")
      .select("inventory_count")
      .eq("id", variant_id)
      .single();

    const newCount = (v?.inventory_count || 0) + quantity;
    const { data, error } = await supabase
      .from("product_variants")
      .update({ inventory_count: newCount })
      .eq("id", variant_id)
      .select("*")
      .single();

    if (error) throw new Error(error.message);

    // 2. Log movement
    await supabase.from("inventory_movements").insert({
      inventory_item_id: variant_id,
      movement_type: "purchase_receipt",
      quantity,
      reference_type: "stock_receipt",
      reference_id: "MANUAL-RECEIPT",
      notes: reference_note || "Staff manual stock receipt",
    });

    return data;
  },

  async replySupportTicket(ticketId: number | string, message: string): Promise<any> {
    const { data, error } = await supabase
      .from("support_ticket_messages")
      .insert({
        ticket_id: Number(ticketId),
        message,
        is_internal: false,
      })
      .select("*")
      .single();

    if (error) throw new Error(error.message);
    return data;
  },
};
