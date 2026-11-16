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
  Send,
  Boxes,
  CheckCircle2,
  MapPin,
  Phone,
  Mail,
  User,
} from "lucide-react";
import { adminApi } from "@/lib/api/admin";
import { formatPKR } from "@/lib/brand";

const COURIER_OPTIONS = [
  { code: "trax", name: "Trax Logistics (Cash on Delivery)" },
  { code: "tcs", name: "TCS Express" },
  { code: "call_courier", name: "Call Courier" },
  { code: "leopards", name: "Leopards Courier Service" },
  { code: "self_dispatch", name: "Direct Atelier Dispatch / Rider" },
];

export default function AdminOrdersPage() {
  const [orders, setOrders] = React.useState<any[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedOrder, setSelectedOrder] = React.useState<any | null>(null);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  // Dispatch modal state
  const [dispatchModalOrder, setDispatchModalOrder] = React.useState<any | null>(null);
  const [courierCode, setCourierCode] = React.useState("trax");
  const [trackingNumber, setTrackingNumber] = React.useState("");
  const [isDispatching, setIsDispatching] = React.useState(false);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadOrders = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getOrders({
        status: statusFilter !== "all" ? (statusFilter === "pending" ? "pending_confirmation" : statusFilter) : undefined,
        limit: 100,
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
      showNotification("Order confirmed. Moved to fulfillment queue.");
      loadOrders();
      if (selectedOrder && selectedOrder.id === id) {
        setSelectedOrder((p: any) => ({ ...p, status: "confirmed" }));
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to confirm order", "error");
    }
  };

  // Handle Mark In-Progress / Processing
  const handleProcessOrder = async (id: number | string) => {
    try {
      await adminApi.updateOrderStatus(id, "processing");
      showNotification("Order marked as Processing in warehouse.");
      loadOrders();
      if (selectedOrder && selectedOrder.id === id) {
        setSelectedOrder((p: any) => ({ ...p, status: "processing" }));
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to process order", "error");
    }
  };

  // Handle Mark Packed
  const handlePackOrder = async (id: number | string) => {
    try {
      await adminApi.updateOrderStatus(id, "packed");
      showNotification("Order packed into luxury gift box and ready for dispatch.");
      loadOrders();
      if (selectedOrder && selectedOrder.id === id) {
        setSelectedOrder((p: any) => ({ ...p, status: "packed" }));
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to pack order", "error");
    }
  };

  // Handle Submit Dispatch
  const handleDispatchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dispatchModalOrder || !trackingNumber.trim()) return;
    setIsDispatching(true);
    try {
      await adminApi.dispatchOrder(dispatchModalOrder.id, courierCode, trackingNumber.trim());
      showNotification(`Order ${dispatchModalOrder.order_number} marked as Shipped via ${courierCode.toUpperCase()} (${trackingNumber})`);
      setDispatchModalOrder(null);
      setTrackingNumber("");
      loadOrders();
      if (selectedOrder && selectedOrder.id === dispatchModalOrder.id) {
        setSelectedOrder((p: any) => ({
          ...p,
          status: "shipped",
          courier_code: courierCode,
          tracking_number: trackingNumber.trim(),
        }));
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to dispatch order", "error");
    } finally {
      setIsDispatching(false);
    }
  };

  // Handle Mark Delivered
  const handleMarkDelivered = async (id: number | string) => {
    if (!confirm("Confirm doorstep delivery & mark COD payment as paid?")) return;
    try {
      await adminApi.updateOrderStatus(id, "delivered");
      showNotification("Order marked as Delivered and Payment marked as Paid.");
      loadOrders();
      if (selectedOrder && selectedOrder.id === id) {
        setSelectedOrder((p: any) => ({ ...p, status: "delivered", payment_status: "paid" }));
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to mark delivered", "error");
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

  const filteredOrders = orders.filter((ord) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const num = (ord.order_number || "").toLowerCase();
    const name = (ord.shipping_address?.full_name || ord.customer_name || "").toLowerCase();
    const city = (ord.shipping_address?.city || "").toLowerCase();
    const phone = (ord.shipping_address?.phone || "").toLowerCase();
    return num.includes(q) || name.includes(q) || city.includes(q) || phone.includes(q);
  });

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
            Complete Order Pipeline
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Order Fulfillment & Dispatch ({total})
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Receive, review customer address, confirm orders, process packaging, book couriers, and complete delivery.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-obsidian-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by order#, name, city..."
              className="pl-9 pr-3 py-2 text-xs rounded-button border border-hairline bg-ivory-light focus:outline-none focus:ring-1 focus:ring-champagne w-60"
            />
          </div>
          <button
            type="button"
            onClick={loadOrders}
            disabled={loading}
            className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors"
            title="Refresh orders"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Status Filter Pipeline */}
      <div className="flex items-center gap-2 p-2 bg-ivory-light rounded-xl border border-hairline overflow-x-auto text-xs">
        {[
          { key: "all", label: "All Orders" },
          { key: "pending", label: "1. Pending Confirmation" },
          { key: "confirmed", label: "2. Confirmed" },
          { key: "processing", label: "3. Processing" },
          { key: "packed", label: "4. Packed" },
          { key: "shipped", label: "5. Dispatched / Shipped" },
          { key: "delivered", label: "6. Delivered (Paid)" },
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
        ) : filteredOrders.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <Package className="w-8 h-8 text-obsidian-300 mx-auto" />
            <p className="text-sm font-medium text-obsidian">No orders in this stage</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline bg-ivory-sand/40 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                  <th className="p-4">Order Ref</th>
                  <th className="p-4">Customer & City</th>
                  <th className="p-4">Placed Date</th>
                  <th className="p-4">Payment</th>
                  <th className="p-4">Grand Total</th>
                  <th className="p-4">Pipeline Status</th>
                  <th className="p-4 text-right">Workflow Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {filteredOrders.map((ord) => (
                  <tr key={ord.id} className="hover:bg-ivory transition-colors">
                    <td className="p-4 font-serif font-semibold text-obsidian">
                      {ord.order_number}
                    </td>
                    <td className="p-4">
                      <div className="font-medium text-obsidian">
                        {ord.shipping_address?.full_name || ord.customer_name || ord.customer_email || "Customer"}
                      </div>
                      <div className="text-[11px] text-obsidian-500">
                        {ord.shipping_address?.city || "Nationwide"} • {ord.shipping_address?.phone || "No phone"}
                      </div>
                    </td>
                    <td className="p-4 text-obsidian-600">
                      {new Date(ord.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4">
                      <span className="capitalize font-medium text-obsidian">
                        {ord.payment_method || "COD"}
                      </span>
                      <span
                        className={`text-[10px] ml-1 px-1.5 py-0.5 rounded ${
                          ord.payment_status === "paid"
                            ? "bg-emerald-100 text-emerald-800 font-semibold"
                            : "text-obsidian-500"
                        }`}
                      >
                        {ord.payment_status}
                      </span>
                    </td>
                    <td className="p-4 font-mono font-medium text-obsidian">
                      {formatPKR(Number(ord.grand_total))}
                    </td>
                    <td className="p-4">
                      <span
                        className={`text-[9px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full ${
                          ord.status === "delivered"
                            ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                            : ord.status === "shipped"
                            ? "bg-sky-100 text-sky-800 border border-sky-300"
                            : ord.status === "packed"
                            ? "bg-purple-100 text-purple-800 border border-purple-300"
                            : ord.status === "processing"
                            ? "bg-blue-100 text-blue-800 border border-blue-300"
                            : ord.status === "confirmed"
                            ? "bg-champagne-light text-champagne-dark border border-champagne-dark/30"
                            : ord.status === "pending" || ord.status === "pending_confirmation"
                            ? "bg-amber-100 text-amber-800 border border-amber-300 animate-pulse"
                            : ord.status === "cancelled"
                            ? "bg-crimson/10 text-crimson"
                            : "bg-ivory-sand text-obsidian"
                        }`}
                      >
                        {ord.status === "pending_confirmation" ? "Pending Confirm" : ord.status}
                      </span>
                      {ord.tracking_number && (
                        <div className="text-[10px] text-obsidian-500 font-mono mt-0.5">
                          {ord.courier_code?.toUpperCase()}: {ord.tracking_number}
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5 flex-wrap">
                        {/* Step 1: Confirm */}
                        {(ord.status === "pending" || ord.status === "pending_confirmation") && (
                          <button
                            type="button"
                            onClick={() => handleConfirmOrder(ord.id)}
                            className="px-2.5 py-1 rounded bg-obsidian text-ivory text-[10px] font-semibold hover:bg-obsidian-800"
                          >
                            Confirm Order
                          </button>
                        )}

                        {/* Step 2: Processing */}
                        {ord.status === "confirmed" && (
                          <button
                            type="button"
                            onClick={() => handleProcessOrder(ord.id)}
                            className="px-2.5 py-1 rounded bg-blue-700 text-ivory text-[10px] font-semibold hover:bg-blue-800"
                          >
                            Process
                          </button>
                        )}

                        {/* Step 3: Pack */}
                        {ord.status === "processing" && (
                          <button
                            type="button"
                            onClick={() => handlePackOrder(ord.id)}
                            className="px-2.5 py-1 rounded bg-purple-700 text-ivory text-[10px] font-semibold hover:bg-purple-800"
                          >
                            Mark Packed
                          </button>
                        )}

                        {/* Step 4: Dispatch / Ship */}
                        {(ord.status === "packed" || ord.status === "confirmed") && (
                          <button
                            type="button"
                            onClick={() => {
                              setDispatchModalOrder(ord);
                              setTrackingNumber(ord.tracking_number || `TRX-${Math.floor(100000 + Math.random() * 900000)}`);
                            }}
                            className="px-2.5 py-1 rounded bg-sky-700 text-ivory text-[10px] font-semibold hover:bg-sky-800 flex items-center gap-1"
                          >
                            <Truck className="w-3 h-3" />
                            <span>Dispatch</span>
                          </button>
                        )}

                        {/* Step 5: Mark Delivered */}
                        {ord.status === "shipped" && (
                          <button
                            type="button"
                            onClick={() => handleMarkDelivered(ord.id)}
                            className="px-2.5 py-1 rounded bg-emerald-700 text-ivory text-[10px] font-semibold hover:bg-emerald-800 flex items-center gap-1"
                          >
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Delivered</span>
                          </button>
                        )}

                        {/* Cancel */}
                        {ord.status !== "cancelled" && ord.status !== "delivered" && (
                          <button
                            type="button"
                            onClick={() => handleCancelOrder(ord.id)}
                            className="px-2 py-1 rounded border border-crimson/30 text-crimson text-[10px] font-medium hover:bg-crimson/5"
                          >
                            Cancel
                          </button>
                        )}

                        {/* Inspect Details */}
                        <button
                          type="button"
                          onClick={() => setSelectedOrder(ord)}
                          className="p-1 text-obsidian-500 hover:text-obsidian"
                          title="Inspect Order Details & Address"
                        >
                          <Eye className="w-4 h-4" />
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

      {/* Dispatch Modal */}
      {dispatchModalOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4">
            <div className="flex items-start justify-between border-b border-hairline pb-3">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">
                  Consignment Dispatch
                </span>
                <h3 className="font-serif text-xl font-medium text-obsidian">
                  {dispatchModalOrder.order_number}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setDispatchModalOrder(null)}
                className="text-xs text-obsidian-500 hover:text-obsidian"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-3 bg-ivory-sand/40 rounded-xl text-xs space-y-1">
              <p className="font-semibold text-obsidian">
                Recipient: {dispatchModalOrder.shipping_address?.full_name}
              </p>
              <p className="text-obsidian-600">
                {dispatchModalOrder.shipping_address?.street_address}, {dispatchModalOrder.shipping_address?.city}
              </p>
              <p className="font-medium text-obsidian">
                COD Amount to Collect: {formatPKR(Number(dispatchModalOrder.grand_total))}
              </p>
            </div>

            <form onSubmit={handleDispatchSubmit} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="font-semibold uppercase text-obsidian">Courier Service</label>
                <select
                  value={courierCode}
                  onChange={(e) => setCourierCode(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-white"
                >
                  {COURIER_OPTIONS.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold uppercase text-obsidian">Courier Tracking / Airway Bill (AWB) #</label>
                <input
                  type="text"
                  required
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  placeholder="e.g. TRX-90281273"
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-white font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setDispatchModalOrder(null)}
                  className="px-4 py-2 rounded-button border border-hairline text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDispatching}
                  className="px-4 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800 disabled:opacity-50"
                >
                  {isDispatching ? "Saving..." : "Confirm Shipment & Booking"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Order Detail & Address Inspection Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-2xl bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-hairline pb-3">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">
                  Full Order & Delivery Dossier
                </span>
                <h3 className="font-serif text-xl font-medium text-obsidian">
                  {selectedOrder.order_number}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedOrder(null)}
                className="text-xs text-obsidian-500 hover:text-obsidian"
              >
                ✕ Close
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-2 p-3 bg-ivory-sand/40 rounded-xl border border-hairline">
                <div className="flex items-center gap-1.5 text-obsidian font-semibold uppercase text-[10px] tracking-wider">
                  <MapPin className="w-3.5 h-3.5 text-champagne-dark" />
                  <span>Verified Shipping Destination</span>
                </div>
                <p className="font-semibold text-obsidian text-sm">
                  {selectedOrder.shipping_address?.full_name || selectedOrder.customer_name}
                </p>
                <p className="text-obsidian-700">
                  {selectedOrder.shipping_address?.street_address}
                </p>
                {selectedOrder.shipping_address?.apartment_suite && (
                  <p className="text-obsidian-600">{selectedOrder.shipping_address?.apartment_suite}</p>
                )}
                <p className="text-obsidian-700 font-medium">
                  {selectedOrder.shipping_address?.city}, {selectedOrder.shipping_address?.province || "Pakistan"}{" "}
                  {selectedOrder.shipping_address?.postal_code && `(${selectedOrder.shipping_address?.postal_code})`}
                </p>
                <div className="pt-1 space-y-0.5 text-obsidian-600">
                  <p className="flex items-center gap-1">
                    <Phone className="w-3 h-3 text-obsidian-400" />
                    <strong>{selectedOrder.shipping_address?.phone || selectedOrder.customer_phone || "Not provided"}</strong>
                  </p>
                  <p className="flex items-center gap-1">
                    <Mail className="w-3 h-3 text-obsidian-400" />
                    <span>{selectedOrder.customer_email || "Customer"}</span>
                  </p>
                </div>
                {selectedOrder.customer_note && (
                  <div className="mt-2 p-2 rounded bg-amber-50 border border-amber-200 text-amber-900 text-[11px]">
                    <strong>Rider Note:</strong> {selectedOrder.customer_note}
                  </div>
                )}
              </div>

              <div className="space-y-2 p-3 bg-ivory-sand/40 rounded-xl border border-hairline">
                <div className="flex items-center gap-1.5 text-obsidian font-semibold uppercase text-[10px] tracking-wider">
                  <Package className="w-3.5 h-3.5 text-champagne-dark" />
                  <span>Fulfillment & Payment Snapshot</span>
                </div>
                <p>Status: <strong className="uppercase">{selectedOrder.status}</strong></p>
                <p>Payment: <strong className="capitalize">{selectedOrder.payment_method}</strong> ({selectedOrder.payment_status})</p>
                {selectedOrder.tracking_number && (
                  <p className="font-mono text-obsidian font-semibold bg-white p-1 rounded border">
                    AWB: {selectedOrder.courier_code?.toUpperCase()} #{selectedOrder.tracking_number}
                  </p>
                )}
                <div className="pt-2 border-t border-hairline space-y-1">
                  <div className="flex justify-between">
                    <span>Subtotal:</span>
                    <span className="font-mono">{formatPKR(Number(selectedOrder.subtotal || 0))}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Shipping Fee:</span>
                    <span className="font-mono">{formatPKR(Number(selectedOrder.shipping_fee || 0))}</span>
                  </div>
                  <div className="flex justify-between font-semibold text-obsidian pt-1 border-t border-hairline text-sm">
                    <span>Grand Total:</span>
                    <span className="font-mono text-champagne-dark">{formatPKR(Number(selectedOrder.grand_total || 0))}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Line items */}
            <div className="space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-obsidian">Order Line Items</span>
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

            {/* Workflow Quick Action Buttons */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-hairline">
              <div className="flex items-center gap-2">
                {(selectedOrder.status === "pending" || selectedOrder.status === "pending_confirmation") && (
                  <button
                    type="button"
                    onClick={() => handleConfirmOrder(selectedOrder.id)}
                    className="px-3 py-1.5 rounded-button bg-obsidian text-ivory text-xs font-semibold"
                  >
                    Confirm Order
                  </button>
                )}
                {selectedOrder.status === "confirmed" && (
                  <button
                    type="button"
                    onClick={() => handleProcessOrder(selectedOrder.id)}
                    className="px-3 py-1.5 rounded-button bg-blue-700 text-ivory text-xs font-semibold"
                  >
                    Mark Processing
                  </button>
                )}
                {selectedOrder.status === "processing" && (
                  <button
                    type="button"
                    onClick={() => handlePackOrder(selectedOrder.id)}
                    className="px-3 py-1.5 rounded-button bg-purple-700 text-ivory text-xs font-semibold"
                  >
                    Mark Packed
                  </button>
                )}
                {(selectedOrder.status === "packed" || selectedOrder.status === "confirmed") && (
                  <button
                    type="button"
                    onClick={() => {
                      setDispatchModalOrder(selectedOrder);
                      setTrackingNumber(selectedOrder.tracking_number || `TRX-${Math.floor(100000 + Math.random() * 900000)}`);
                    }}
                    className="px-3 py-1.5 rounded-button bg-sky-700 text-ivory text-xs font-semibold"
                  >
                    Dispatch / Ship
                  </button>
                )}
                {selectedOrder.status === "shipped" && (
                  <button
                    type="button"
                    onClick={() => handleMarkDelivered(selectedOrder.id)}
                    className="px-3 py-1.5 rounded-button bg-emerald-700 text-ivory text-xs font-semibold"
                  >
                    Mark Delivered (Paid)
                  </button>
                )}
              </div>

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
