"use client";

import * as React from "react";
import { Users, Search, CheckCircle, AlertCircle, RefreshCw, Shield, Ban } from "lucide-react";
import { adminApi } from "@/lib/api/admin";

export default function AdminCustomersPage() {
  const [customers, setCustomers] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = React.useState("");
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadCustomers = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getCustomers({ search: search || undefined, limit: 50 });
      setCustomers(res.items || []);
    } catch (err: any) {
      showNotification(err.message || "Failed to load customers", "error");
    } finally {
      setLoading(false);
    }
  }, [search]);

  React.useEffect(() => {
    loadCustomers();
  }, [loadCustomers]);

  const handleStatusChange = async (id: number | string, newStatus: "active" | "suspended" | "banned") => {
    const reason = prompt(`Reason for setting status to ${newStatus}:`);
    if (!reason) return;
    try {
      await adminApi.updateCustomerStatus(id, newStatus, reason);
      showNotification(`Customer status updated to ${newStatus}.`);
      loadCustomers();
    } catch (err: any) {
      showNotification(err.message || "Failed to update customer status", "error");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl">
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

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Client Directory
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Registered Customers
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Customer directory, account status management, and verification controls.
          </p>
        </div>
        <button
          type="button"
          onClick={loadCustomers}
          disabled={loading}
          className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="p-4 bg-ivory-light rounded-xl border border-hairline max-w-md">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-obsidian-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by customer name, email, or phone..."
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-hairline bg-ivory"
          />
        </div>
      </div>

      <div className="bg-ivory-light rounded-2xl border border-hairline shadow-subtle overflow-hidden">
        {loading ? (
          <div className="py-20 text-center">
            <div className="w-7 h-7 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs text-obsidian-500">Querying customer accounts...</p>
          </div>
        ) : customers.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <Users className="w-8 h-8 text-obsidian-300 mx-auto" />
            <p className="text-sm font-medium text-obsidian">No customers found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline bg-ivory-sand/40 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                  <th className="p-4">Customer Name</th>
                  <th className="p-4">Email ID</th>
                  <th className="p-4">Phone</th>
                  <th className="p-4">Registered On</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {customers.map((c) => (
                  <tr key={c.id} className="hover:bg-ivory">
                    <td className="p-4 font-medium text-obsidian">
                      {c.first_name ? `${c.first_name} ${c.last_name || ""}`.trim() : "Customer"}
                    </td>
                    <td className="p-4 text-obsidian-600 font-mono text-[11px]">{c.email}</td>
                    <td className="p-4 text-obsidian-600">{c.phone || "—"}</td>
                    <td className="p-4 text-obsidian-500">{new Date(c.created_at).toLocaleDateString()}</td>
                    <td className="p-4">
                      <span
                        className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full ${
                          c.status === "active"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-crimson/10 text-crimson"
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      {c.status === "active" ? (
                        <button
                          type="button"
                          onClick={() => handleStatusChange(c.id, "suspended")}
                          className="px-2 py-1 rounded border border-amber-300 text-amber-700 hover:bg-amber-50 text-[10px] font-semibold"
                        >
                          Suspend
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleStatusChange(c.id, "active")}
                          className="px-2 py-1 rounded bg-obsidian text-ivory text-[10px] font-semibold"
                        >
                          Reactivate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
