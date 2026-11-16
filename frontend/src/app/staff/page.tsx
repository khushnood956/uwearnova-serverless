"use client";

import * as React from "react";
import {
  ClipboardList,
  Package,
  Truck,
  Boxes,
  Headphones,
  CheckCircle,
  AlertCircle,
  Clock,
  RefreshCw,
  Send,
  Plus,
} from "lucide-react";
import { staffApi, StaffDashboardSummary, StaffTask } from "@/lib/api/staff";

export default function StaffDashboardPage() {
  const [summary, setSummary] = React.useState<StaffDashboardSummary | null>(null);
  const [tasks, setTasks] = React.useState<StaffTask[]>([]);
  const [activeQueue, setActiveQueue] = React.useState<"tasks" | "orders" | "fulfillment" | "inventory" | "support">("tasks");
  const [loading, setLoading] = React.useState(true);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  // Quick Action Form States
  const [dispatchTrackingNum, setDispatchTrackingNum] = React.useState("");
  const [dispatchShipmentId, setDispatchShipmentId] = React.useState("");

  const [intakeVariantId, setIntakeVariantId] = React.useState("");
  const [intakeQty, setIntakeQty] = React.useState("");
  const [intakeNote, setIntakeNote] = React.useState("");

  const [ticketId, setTicketId] = React.useState("");
  const [ticketReplyMsg, setTicketReplyMsg] = React.useState("");

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadStaffData = React.useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, tasksRes] = await Promise.allSettled([
        staffApi.getDashboardSummary(),
        staffApi.getMyTasks(),
      ]);

      if (sumRes.status === "fulfilled") {
        setSummary(sumRes.value);
      }
      if (tasksRes.status === "fulfilled") {
        setTasks(tasksRes.value.items || []);
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to load staff work queue", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadStaffData();
  }, [loadStaffData]);

  // Complete a Task
  const handleCompleteTask = async (taskId: number) => {
    try {
      await staffApi.updateTaskStatus(taskId, "completed");
      showNotification("Task marked as completed.");
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: "completed" as const } : t))
      );
    } catch (err: any) {
      showNotification(err.message || "Failed to update task", "error");
    }
  };

  // Dispatch Shipment
  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dispatchShipmentId || !dispatchTrackingNum) return;
    try {
      await staffApi.dispatchShipment(dispatchShipmentId, dispatchTrackingNum);
      showNotification(`Consignment ${dispatchTrackingNum} booked & dispatched!`);
      setDispatchShipmentId("");
      setDispatchTrackingNum("");
      loadStaffData();
    } catch (err: any) {
      showNotification(err.message || "Failed to dispatch consignment", "error");
    }
  };

  // Receive Stock
  const handleReceiveStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!intakeVariantId || !intakeQty) return;
    try {
      await staffApi.receiveStock(Number(intakeVariantId), Number(intakeQty), intakeNote);
      showNotification(`Recorded intake of ${intakeQty} unit(s) into warehouse inventory.`);
      setIntakeVariantId("");
      setIntakeQty("");
      setIntakeNote("");
      loadStaffData();
    } catch (err: any) {
      showNotification(err.message || "Failed to record stock intake", "error");
    }
  };

  // Reply Support Ticket
  const handleReplyTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketId || !ticketReplyMsg) return;
    try {
      await staffApi.replySupportTicket(ticketId, ticketReplyMsg);
      showNotification(`Support response sent to customer.`);
      setTicketId("");
      setTicketReplyMsg("");
      loadStaffData();
    } catch (err: any) {
      showNotification(err.message || "Failed to reply to ticket", "error");
    }
  };

  return (
    <div className="space-y-8">
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
            Authorized Workstation
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Operational Work Queues
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Role-tailored operations for order confirmation, fulfillment packing, inventory intake, and customer support.
          </p>
        </div>

        <button
          type="button"
          onClick={loadStaffData}
          disabled={loading}
          className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors self-start sm:self-auto"
          title="Refresh queue"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Role-tailored summary metric cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
          <span className="text-[10px] uppercase font-semibold text-obsidian-400">Assigned Tasks</span>
          <p className="font-serif text-2xl font-semibold text-obsidian mt-1">
            {summary?.assigned_tasks_count ?? tasks.filter((t) => t.status !== "completed").length}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
          <span className="text-[10px] uppercase font-semibold text-amber-700">Orders to Confirm</span>
          <p className="font-serif text-2xl font-semibold text-amber-800 mt-1">
            {summary?.pending_orders_count ?? 0}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
          <span className="text-[10px] uppercase font-semibold text-champagne-dark">Shipments to Pack</span>
          <p className="font-serif text-2xl font-semibold text-obsidian mt-1">
            {summary?.pending_fulfillments_count ?? 0}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
          <span className="text-[10px] uppercase font-semibold text-crimson">Low Stock Deficits</span>
          <p className="font-serif text-2xl font-semibold text-crimson mt-1">
            {summary?.low_stock_alerts_count ?? 0}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
          <span className="text-[10px] uppercase font-semibold text-obsidian-500">Support Tickets</span>
          <p className="font-serif text-2xl font-semibold text-obsidian mt-1">
            {summary?.open_support_cases_count ?? 0}
          </p>
        </div>
      </div>

      {/* Queue Selection Tabs */}
      <div className="flex items-center gap-2 p-1.5 bg-ivory-sand/60 rounded-xl border border-hairline overflow-x-auto text-xs">
        {[
          { key: "tasks", label: "My Assigned Tasks", icon: ClipboardList, badge: tasks.filter((t) => t.status !== "completed").length },
          { key: "fulfillment", label: "Fulfillment & Dispatch", icon: Truck },
          { key: "inventory", label: "Warehouse Stock Intake", icon: Boxes },
          { key: "support", label: "Customer Inquiries", icon: Headphones },
        ].map((q) => {
          const Icon = q.icon;
          const isActive = activeQueue === q.key;
          return (
            <button
              key={q.key}
              type="button"
              onClick={() => setActiveQueue(q.key as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                isActive
                  ? "bg-obsidian text-ivory font-semibold shadow-subtle"
                  : "text-obsidian-700 hover:text-obsidian hover:bg-ivory"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{q.label}</span>
              {q.badge !== undefined && q.badge > 0 && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${isActive ? "bg-champagne text-obsidian font-bold" : "bg-ivory text-obsidian"}`}>
                  {q.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="bg-ivory-light rounded-2xl border border-hairline p-6 shadow-subtle min-h-[400px]">
        {/* 1. TASKS QUEUE */}
        {activeQueue === "tasks" && (
          <div className="space-y-4">
            <h2 className="font-serif text-xl font-medium text-obsidian">My Assigned Operational Work</h2>
            {tasks.length === 0 ? (
              <div className="py-16 text-center text-obsidian-500 space-y-1">
                <CheckCircle className="w-8 h-8 text-emerald-600 mx-auto" />
                <p className="text-sm font-medium text-obsidian">No pending tasks assigned</p>
                <p className="text-xs">All items assigned to your workstation are completed.</p>
              </div>
            ) : (
              <div className="divide-y divide-hairline border border-hairline rounded-xl overflow-hidden bg-ivory">
                {tasks.map((task) => (
                  <div key={task.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-obsidian">{task.title}</span>
                        <span
                          className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full ${
                            task.priority === "urgent" || task.priority === "high"
                              ? "bg-crimson/10 text-crimson"
                              : "bg-ivory-sand text-obsidian"
                          }`}
                        >
                          {task.priority}
                        </span>
                        <span
                          className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full ${
                            task.status === "completed" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {task.status}
                        </span>
                      </div>
                      {task.description && <p className="text-obsidian-600 font-light mt-1">{task.description}</p>}
                    </div>

                    {task.status !== "completed" && (
                      <button
                        type="button"
                        onClick={() => handleCompleteTask(task.id)}
                        className="px-3 py-1.5 rounded-button bg-obsidian text-ivory text-[11px] font-semibold hover:bg-obsidian-800 self-start sm:self-auto"
                      >
                        Mark Completed
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 2. FULFILLMENT & DISPATCH QUEUE */}
        {activeQueue === "fulfillment" && (
          <div className="space-y-6 max-w-xl">
            <div>
              <h2 className="font-serif text-xl font-medium text-obsidian">Dispatch & Booking Execution</h2>
              <p className="text-xs text-obsidian-500 font-light mt-1">
                Assign live consignment tracking number from courier (Trax, Call Courier, TCS, Leopards) and flag order as dispatched.
              </p>
            </div>

            <form onSubmit={handleDispatch} className="space-y-4 p-5 rounded-xl bg-ivory border border-hairline">
              <div className="space-y-1 text-xs">
                <label className="font-semibold uppercase text-obsidian">Shipment Record ID</label>
                <input
                  type="text"
                  value={dispatchShipmentId}
                  onChange={(e) => setDispatchShipmentId(e.target.value)}
                  placeholder="e.g. 1"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light font-mono"
                />
              </div>

              <div className="space-y-1 text-xs">
                <label className="font-semibold uppercase text-obsidian">Courier Tracking Consignment Number</label>
                <input
                  type="text"
                  value={dispatchTrackingNum}
                  onChange={(e) => setDispatchTrackingNum(e.target.value)}
                  placeholder="e.g. TRX-99281726"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light font-mono"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800"
              >
                Book & Dispatch Consignment
              </button>
            </form>
          </div>
        )}

        {/* 3. WAREHOUSE STOCK INTAKE */}
        {activeQueue === "inventory" && (
          <div className="space-y-6 max-w-xl">
            <div>
              <h2 className="font-serif text-xl font-medium text-obsidian">Warehouse Stock Intake</h2>
              <p className="text-xs text-obsidian-500 font-light mt-1">
                Receive completed garment production batches into active stock inventory.
              </p>
            </div>

            <form onSubmit={handleReceiveStock} className="space-y-4 p-5 rounded-xl bg-ivory border border-hairline">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="space-y-1">
                  <label className="font-semibold uppercase text-obsidian">Product SKU Variant ID</label>
                  <input
                    type="number"
                    value={intakeVariantId}
                    onChange={(e) => setIntakeVariantId(e.target.value)}
                    placeholder="Variant ID"
                    required
                    className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-semibold uppercase text-obsidian">Quantity Received</label>
                  <input
                    type="number"
                    min={1}
                    value={intakeQty}
                    onChange={(e) => setIntakeQty(e.target.value)}
                    placeholder="e.g. 50"
                    required
                    className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light font-mono"
                  />
                </div>
              </div>

              <div className="space-y-1 text-xs">
                <label className="font-semibold uppercase text-obsidian">Production Batch Reference / Note</label>
                <input
                  type="text"
                  value={intakeNote}
                  onChange={(e) => setIntakeNote(e.target.value)}
                  placeholder="e.g. Sialkot atelier batch 4B — 100% linen weave"
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800"
              >
                Confirm Inventory Intake
              </button>
            </form>
          </div>
        )}

        {/* 4. CUSTOMER SUPPORT QUEUE */}
        {activeQueue === "support" && (
          <div className="space-y-6 max-w-xl">
            <div>
              <h2 className="font-serif text-xl font-medium text-obsidian">Customer Support Inquiries</h2>
              <p className="text-xs text-obsidian-500 font-light mt-1">
                Transmit authorized concierge replies to customer support cases.
              </p>
            </div>

            <form onSubmit={handleReplyTicket} className="space-y-4 p-5 rounded-xl bg-ivory border border-hairline">
              <div className="space-y-1 text-xs">
                <label className="font-semibold uppercase text-obsidian">Ticket Case ID</label>
                <input
                  type="number"
                  value={ticketId}
                  onChange={(e) => setTicketId(e.target.value)}
                  placeholder="Ticket ID"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light font-mono"
                />
              </div>

              <div className="space-y-1 text-xs">
                <label className="font-semibold uppercase text-obsidian">Concierge Response Message</label>
                <textarea
                  value={ticketReplyMsg}
                  onChange={(e) => setTicketReplyMsg(e.target.value)}
                  rows={3}
                  placeholder="Dear client, your doorstep exchange has been approved..."
                  required
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 flex items-center justify-center gap-2"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Transmit Response to Customer</span>
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
