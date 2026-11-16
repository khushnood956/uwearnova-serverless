"use client";

import * as React from "react";
import { RotateCcw, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";
import { adminApi } from "@/lib/api/admin";
import { formatPKR } from "@/lib/brand";

export default function AdminReturnsPage() {
  const [returns, setReturns] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadReturns = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getReturns({ limit: 50 });
      setReturns(res.items || []);
    } catch (err: any) {
      showNotification(err.message || "Failed to load returns", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadReturns();
  }, [loadReturns]);

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

      <div className="flex items-center justify-between pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Policy & Resolution
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Returns, Exchanges & Refunds
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Review customer doorstep exchange requests, warehouse inspection checkpoints, and refund executions.
          </p>
        </div>
        <button
          type="button"
          onClick={loadReturns}
          disabled={loading}
          className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="bg-ivory-light rounded-2xl border border-hairline shadow-subtle overflow-hidden">
        {loading ? (
          <div className="py-20 text-center">
            <div className="w-7 h-7 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs text-obsidian-500">Querying return requests...</p>
          </div>
        ) : returns.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <RotateCcw className="w-8 h-8 text-obsidian-300 mx-auto" />
            <p className="text-sm font-medium text-obsidian">No return requests on record</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline bg-ivory-sand/40 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                  <th className="p-4">Return ID</th>
                  <th className="p-4">Order Ref</th>
                  <th className="p-4">Type</th>
                  <th className="p-4">Reason</th>
                  <th className="p-4">Requested On</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Refund Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {returns.map((r) => (
                  <tr key={r.id} className="hover:bg-ivory">
                    <td className="p-4 font-mono font-medium text-obsidian">{r.return_number || `RET-${r.id}`}</td>
                    <td className="p-4 font-serif text-obsidian">{r.order_number || `Order #${r.order_id}`}</td>
                    <td className="p-4 uppercase font-semibold text-[10px] text-champagne-dark">{r.request_type}</td>
                    <td className="p-4 text-obsidian-700">{r.reason || "Size swap"}</td>
                    <td className="p-4 text-obsidian-500">{new Date(r.created_at).toLocaleDateString()}</td>
                    <td className="p-4">
                      <span className="text-[9px] uppercase font-bold px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark">
                        {r.status}
                      </span>
                    </td>
                    <td className="p-4 text-obsidian-600 capitalize">
                      {r.refund_status || "Pending Review"}
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
