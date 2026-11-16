"use client";

import * as React from "react";
import Link from "next/link";
import {
  Package,
  Search,
  Filter,
  CheckCircle,
  AlertCircle,
  Clock,
  Truck,
  XCircle,
  Eye,
  RefreshCw,
} from "lucide-react";
import { adminApi } from "@/lib/api/admin";
import { formatPKR } from "@/lib/brand";

export default function AdminOrdersPage() {
  const [orders, setOrders] = React.useState<any[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [selectedOrder, setSelectedOrder] = React.useState<any | null>(null);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadOrders = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getOrders({
        status: statusFilter !== "all" ? statusFilter : undefined,
        limit: 50,
      });
      setOrders(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      showNotification(err.message || "Failed to load orders", "error");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  React.useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  // Handle Confirm Order
  const handleConfirmOrder = async (id: number | string) => {
    try {
      await adminApi.confirmOrder(id);
      showNotification("Order confirmed for fulfillment processing.");
      loadOrders();
      if (selectedOrder && selectedOrder.id === id) {
        setSelectedOrder((p: any) => ({ ...p, status: "confirmed" }));
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to confirm order", "error");
    }
  };

  // Handle Cancel Order
  const handleCancelOrder = async (id: number | string) => {
    const reason = prompt("Please provide a reason for order cancellation (stock deficit, customer request, etc.):");
    if (!reason) return;
    try {
      await adminApi.cancelOrder(id, reason);
      showNotification("Order cancelled and inventory reservations released.");
      loadOrders();
      if (selectedOrder && selectedOrder.id === id) {
        setSelectedOrder((p: any) => ({ ...p, status: "cancelled" }));
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to cancel order", "error");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Toast */}
      {notification && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-card text-xs font-medium flex items-center gap-2 border animate-in slide-in-from-bottom-2 ${
            notification.type === "success"
              ? "bg-emerald-950 text-emerald-200 border-emerald-800"
              : "bg-crimson text-ivory border-crimson/80"
          }`}
        >
          {notification.type === "success" ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{notification.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Fulfillment & Operations
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Order Operations ({total})
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Review customer orders, verify COD payments, confirm batches, and dispatch consignments.
          </p>
        </div>

        <button
          type="button"
          onClick={loadOrders}
          disabled={loading}
          className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors self-start sm:self-auto"
          title="Refresh orders"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Status Filter Bar */}
      <div className="flex items-center gap-2 p-3 bg-ivory-light rounded-xl border border-hairline overflow-x-auto text-xs">
        {[
          { key: "all", label: "All Orders" },
          { key: "pending", label: "Pending Confirmation" },
          { key: "confirmed", label: "Confirmed" },
          { key: "dispatched", label: "Dispatched" },
          { key: "delivered", label: "Delivered" },
          { key: "cancelled", label: "Cancelled" },
        ].map((st) => (
          <button
            key={st.key}
            type="button"
            onClick={() => setStatusFilter(st.key)}
            className={`px-3 py-1.5 rounded-button font-medium transition-colors whitespace-nowrap ${
              statusFilter === st.key
                ? "bg-obsidian text-ivory font-semibold"
                : "bg-ivory text-obsidian-600 hover:bg-ivory-sand border border-hairline"
            }`}
          >
            {st.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-ivory-light rounded-2xl border border-hairline shadow-subtle overflow-hidden">
        {loading ? (
          <div className="py-20 text-center">
            <div className="w-7 h-7 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs text-obsidian-500">Retrieving orders...</p>
          </div>
        ) : orders.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <Package className="w-8 h-8 text-obsidian-300 mx-auto" />
            <p className="text-sm font-medium text-obsidian">No orders in this queue</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline bg-ivory-sand/40 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                  <th className="p-4">Order Ref</th>
                  <th className="p-4">Customer</th>
                  <th className="p-4">Placed On</th>
                  <th className="p-4">Payment</th>
                  <th className="p-4">Grand Total</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {orders.map((ord) => (
                  <tr key={ord.id} className="hover:bg-ivory transition-colors">
                    <td className="p-4 font-serif font-semibold text-obsidian">
                      {ord.order_number}
                    </td>
                    <td className="p-4">
                      <div className="font-medium text-obsidian">
                        {ord.shipping_address?.full_name || ord.customer_email || "Customer"}
                      </div>
                      <div className="text-[11px] text-obsidian-500">
                        {ord.shipping_address?.city || "Nationwide"}
                      </div>
                    </td>
                    <td className="p-4 text-obsidian-600">
                      {new Date(ord.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4">
                      <span className="capitalize font-medium text-obsidian">
                        {ord.payment_method || "COD"}
                      </span>
                      <span className="text-[10px] text-obsidian-500 ml-1">
                        ({ord.payment_status})
                      </span>
                    </td>
                    <td className="p-4 font-mono font-medium text-obsidian">
                      {formatPKR(Number(ord.grand_total))}
                    </td>
                    <td className="p-4">
                      <span
                        className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                          ord.status === "delivered"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : ord.status === "pending"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : ord.status === "cancelled"
                            ? "bg-crimson/10 text-crimson"
                            : "bg-champagne-light text-champagne-dark border border-champagne-dark/20"
                        }`}
                      >
                        {ord.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {ord.status === "pending" && (
                          <button
                            type="button"
                            onClick={() => handleConfirmOrder(ord.id)}
                            className="px-2.5 py-1 rounded bg-obsidian text-ivory text-[10px] font-semibold hover:bg-obsidian-800"
                          >
                            Confirm
                          </button>
                        )}
                        {ord.status !== "cancelled" && ord.status !== "delivered" && (
                          <button
                            type="button"
                            onClick={() => handleCancelOrder(ord.id)}
                            className="px-2 py-1 rounded border border-crimson/30 text-crimson text-[10px] font-medium hover:bg-crimson/5"
                          >
                            Cancel
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setSelectedOrder(ord)}
                          className="p-1 text-obsidian-500 hover:text-obsidian"
                          title="Inspect Order Details"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Order Detail Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-2xl bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-hairline pb-3">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Order Inspection</span>
                <h3 className="font-serif text-xl font-medium text-obsidian">{selectedOrder.order_number}</h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedOrder(null)}
                className="text-xs text-obsidian-500 hover:text-obsidian"
              >
                ✕ Close
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="space-y-1 p-3 bg-ivory-sand/40 rounded-xl">
                <span className="text-[10px] uppercase font-semibold text-obsidian-500">Shipping Destination</span>
                <p className="font-semibold text-obsidian">{selectedOrder.shipping_address?.full_name}</p>
                <p>{selectedOrder.shipping_address?.street_address}</p>
                <p>{selectedOrder.shipping_address?.city}, {selectedOrder.shipping_address?.province}</p>
                <p>Phone: {selectedOrder.shipping_address?.phone}</p>
              </div>

              <div className="space-y-1 p-3 bg-ivory-sand/40 rounded-xl">
                <span className="text-[10px] uppercase font-semibold text-obsidian-500">Financial Snapshot</span>
                <p>Payment: <strong className="capitalize">{selectedOrder.payment_method}</strong> ({selectedOrder.payment_status})</p>
                <p>Subtotal: {formatPKR(Number(selectedOrder.subtotal || 0))}</p>
                <p>Shipping: {formatPKR(Number(selectedOrder.shipping_fee || 0))}</p>
                <p className="font-semibold text-obsidian pt-1">
                  Grand Total: {formatPKR(Number(selectedOrder.grand_total || 0))}
                </p>
              </div>
            </div>

            {/* Line items */}
            <div className="space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-obsidian">Order Items</span>
              <div className="divide-y divide-hairline border border-hairline rounded-xl overflow-hidden bg-ivory text-xs">
                {(selectedOrder.items || []).map((item: any, idx: number) => (
                  <div key={idx} className="p-3 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-obsidian">{item.product_name}</p>
                      <p className="text-[11px] text-obsidian-500">
                        SKU: {item.variant_sku} • Size: {item.size} • Color: {item.color_name} • Qty: {item.quantity}
                      </p>
                    </div>
                    <span className="font-medium font-mono text-obsidian">
                      {formatPKR(Number(item.line_total || item.unit_price * item.quantity))}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-hairline">
              <button
                type="button"
                onClick={() => setSelectedOrder(null)}
                className="px-4 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold"
              >
                Close View
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
