"use client";

import * as React from "react";
import { ShieldAlert, RefreshCw, CheckCircle, AlertCircle } from "lucide-react";
import { adminApi, AdminAuditLog } from "@/lib/api/admin";

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = React.useState<AdminAuditLog[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  const loadLogs = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getAuditLogs({ limit: 50 });
      setLogs(res.items || []);
    } catch (err: any) {
      setNotification({ text: err.message || "Failed to load audit logs", type: "error" });
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Security Governance
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            System Audit Trail
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Immutable administrative activity logs, sensitive state changes, and staff operations.
          </p>
        </div>
        <button
          type="button"
          onClick={loadLogs}
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
            <p className="text-xs text-obsidian-500">Querying immutable audit logs...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <ShieldAlert className="w-8 h-8 text-obsidian-300 mx-auto" />
            <p className="text-sm font-medium text-obsidian">No audit events recorded yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline bg-ivory-sand/40 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                  <th className="p-4">Timestamp (UTC)</th>
                  <th className="p-4">Actor</th>
                  <th className="p-4">Action</th>
                  <th className="p-4">Entity</th>
                  <th className="p-4">Entity ID</th>
                  <th className="p-4">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-ivory">
                    <td className="p-4 text-obsidian-500 font-mono text-[11px]">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="p-4 font-medium text-obsidian">
                      {log.actor_email || `User #${log.actor_id || "System"}`}
                    </td>
                    <td className="p-4">
                      <span className="font-mono text-[11px] font-semibold text-champagne-dark">
                        {log.action}
                      </span>
                    </td>
                    <td className="p-4 uppercase text-[10px] text-obsidian-600 font-medium">
                      {log.entity_type}
                    </td>
                    <td className="p-4 font-mono text-obsidian-500 text-[11px]">
                      {log.entity_id || "—"}
                    </td>
                    <td className="p-4 font-mono text-obsidian-400 text-[11px]">
                      {log.ip_address || "127.0.0.1"}
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
