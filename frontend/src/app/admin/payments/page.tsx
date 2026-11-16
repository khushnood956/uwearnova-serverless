"use client";

import * as React from "react";
import { CreditCard, CheckCircle, AlertCircle, RefreshCw, DollarSign } from "lucide-react";
import { adminApi } from "@/lib/api/admin";
import { formatPKR } from "@/lib/brand";

export default function AdminPaymentsPage() {
  const [payments, setPayments] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [collectModalPayment, setCollectModalPayment] = React.useState<any | null>(null);
  const [collectAmount, setCollectAmount] = React.useState<number>(0);
  const [collectNotes, setCollectNotes] = React.useState("");
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadPayments = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getPayments({ limit: 50 });
      setPayments(res.items || []);
    } catch (err: any) {
      showNotification(err.message || "Failed to load payments", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadPayments();
  }, [loadPayments]);

  const handleCollectCash = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!collectModalPayment) return;
    try {
      await adminApi.collectCodCash(collectModalPayment.id, collectAmount, collectNotes);
      showNotification(`Recorded cash collection of ${formatPKR(collectAmount)}.`);
      setCollectModalPayment(null);
      loadPayments();
    } catch (err: any) {
      showNotification(err.message || "Failed to record collection", "error");
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

      <div className="flex items-center justify-between pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Finance & Remittance
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Payments & COD Reconciliation
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Monitor domestic bank cards and reconcile Cash on Delivery remittances from courier partners.
          </p>
        </div>
        <button
          type="button"
          onClick={loadPayments}
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
            <p className="text-xs text-obsidian-500">Querying payment ledger...</p>
          </div>
        ) : payments.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <CreditCard className="w-8 h-8 text-obsidian-300 mx-auto" />
            <p className="text-sm font-medium text-obsidian">No payment records found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline bg-ivory-sand/40 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                  <th className="p-4">Payment Ref</th>
                  <th className="p-4">Order ID</th>
                  <th className="p-4">Method</th>
                  <th className="p-4">Expected Amount</th>
                  <th className="p-4">Collected Amount</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {payments.map((p) => (
                  <tr key={p.id} className="hover:bg-ivory">
                    <td className="p-4 font-mono font-medium text-obsidian">{p.payment_reference || `PAY-${p.id}`}</td>
                    <td className="p-4 font-serif text-obsidian">Order #{p.order_id}</td>
                    <td className="p-4 capitalize font-medium text-obsidian">{p.payment_method}</td>
                    <td className="p-4 font-mono text-obsidian">{formatPKR(Number(p.amount))}</td>
                    <td className="p-4 font-mono text-emerald-700 font-medium">{formatPKR(Number(p.amount_collected || 0))}</td>
                    <td className="p-4">
                      <span className="text-[9px] uppercase font-bold px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark">
                        {p.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      {p.payment_method === "cod" && p.status !== "completed" && (
                        <button
                          type="button"
                          onClick={() => {
                            setCollectModalPayment(p);
                            setCollectAmount(Number(p.amount) - Number(p.amount_collected || 0));
                            setCollectNotes("");
                          }}
                          className="px-2.5 py-1 rounded bg-obsidian text-ivory text-[10px] font-semibold"
                        >
                          Collect Cash
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

      {/* Collect Modal */}
      {collectModalPayment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4">
            <h3 className="font-serif text-xl font-medium text-obsidian">Collect COD Cash Remittance</h3>
            <form onSubmit={handleCollectCash} className="space-y-3 text-xs">
              <div>
                <label className="text-[11px] font-semibold uppercase text-obsidian">Amount to Remit (PKR)</label>
                <input
                  type="number"
                  value={collectAmount}
                  onChange={(e) => setCollectAmount(Number(e.target.value))}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light font-mono mt-1"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold uppercase text-obsidian">Courier Manifest Note</label>
                <textarea
                  value={collectNotes}
                  onChange={(e) => setCollectNotes(e.target.value)}
                  placeholder="Trax/Leopards batch manifest reference..."
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-ivory-light mt-1"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setCollectModalPayment(null)}
                  className="px-4 py-2 rounded-button text-xs text-obsidian"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold"
                >
                  Confirm Remittance
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
