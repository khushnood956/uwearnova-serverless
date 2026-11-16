"use client";

import * as React from "react";
import {
  Sliders,
  DollarSign,
  CreditCard,
  Banknote,
  Building,
  Package,
  Layers,
  Save,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Tag,
  Percent,
} from "lucide-react";
import { settingsApi, DynamicStoreSettings, DEFAULT_STORE_SETTINGS, StoreBundle } from "@/lib/api/settings";
import { discountsApi, CouponItem } from "@/lib/api/discounts";
import { formatPKR } from "@/lib/brand";

export default function AdminSettingsPage() {
  const [settings, setSettings] = React.useState<DynamicStoreSettings>(DEFAULT_STORE_SETTINGS);
  const [coupons, setCoupons] = React.useState<CouponItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  // New Coupon Form
  const [newCode, setNewCode] = React.useState("");
  const [newType, setNewType] = React.useState<"percentage" | "fixed_amount">("percentage");
  const [newValue, setNewValue] = React.useState<string>("10");
  const [newMinOrder, setNewMinOrder] = React.useState<string>("2000");
  const [couponCreating, setCouponCreating] = React.useState(false);

  // New Bundle Form
  const [bundleName, setBundleName] = React.useState("");
  const [bundleDesc, setBundleDesc] = React.useState("");
  const [bundleCount, setBundleCount] = React.useState("2");
  const [bundleDiscount, setBundleDiscount] = React.useState("15");

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadData = React.useCallback(async () => {
    setLoading(true);
    try {
      const [s, c] = await Promise.all([
        settingsApi.getSettings(),
        discountsApi.getCoupons(),
      ]);
      setSettings(s);
      setCoupons(c);
    } catch (err: any) {
      showNotification(err.message || "Failed to load store settings", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await settingsApi.updateSettings(settings);
      showNotification("Store rates & payment options saved successfully!");
    } catch (err: any) {
      showNotification(err.message || "Failed to update settings", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCode.trim()) return;
    setCouponCreating(true);
    try {
      const created = await discountsApi.createCoupon({
        code: newCode.trim(),
        discount_type: newType,
        discount_value: Number(newValue),
        minimum_order_amount: Number(newMinOrder) || 0,
      });
      setCoupons((p) => [created, ...p]);
      setNewCode("");
      setNewValue("10");
      setNewMinOrder("2000");
      showNotification(`Promo code ${created.code} published!`);
    } catch (err: any) {
      showNotification(err.message || "Failed to create promo code", "error");
    } finally {
      setCouponCreating(false);
    }
  };

  const handleToggleCoupon = async (id: number, currentActive: boolean) => {
    try {
      await discountsApi.toggleCouponStatus(id, !currentActive);
      setCoupons((p) => p.map((c) => (c.id === id ? { ...c, is_active: !currentActive } : c)));
      showNotification("Coupon status updated.");
    } catch (err: any) {
      showNotification(err.message || "Failed to toggle coupon", "error");
    }
  };

  const handleDeleteCoupon = async (id: number) => {
    if (!confirm("Delete this promo voucher permanently?")) return;
    try {
      await discountsApi.deleteCoupon(id);
      setCoupons((p) => p.filter((c) => c.id !== id));
      showNotification("Coupon deleted.");
    } catch (err: any) {
      showNotification(err.message || "Failed to delete coupon", "error");
    }
  };

  const handleAddBundle = (e: React.FormEvent) => {
    e.preventDefault();
    if (!bundleName.trim()) return;
    const newBundle: StoreBundle = {
      id: `bnd_${Date.now()}`,
      name: bundleName.trim(),
      description: bundleDesc.trim(),
      badge: "Curated Bundle",
      item_count: Number(bundleCount) || 2,
      discount_percentage: Number(bundleDiscount) || 15,
      is_active: true,
    };
    setSettings((p) => ({
      ...p,
      bundles: [...p.bundles, newBundle],
    }));
    setBundleName("");
    setBundleDesc("");
    showNotification("Bundle package added to configuration (remember to click Save Changes).");
  };

  const handleRemoveBundle = (id: string) => {
    setSettings((p) => ({
      ...p,
      bundles: p.bundles.filter((b) => b.id !== id),
    }));
  };

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Toast */}
      {notification && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-card text-xs font-medium flex items-center gap-2 border animate-in slide-in-from-bottom-2 ${
            notification.type === "success"
              ? "bg-emerald-950 text-emerald-200 border-emerald-800"
              : "bg-crimson text-ivory border-crimson/80"
          }`}
        >
          {notification.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{notification.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Store Governance & Dynamic Tariffs
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Rates, Payment Methods & Discounts
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Live controls for nationwide delivery fee, payment gateways, active promo vouchers, and bundle discounts.
          </p>
        </div>

        <button
          type="button"
          onClick={handleSaveSettings}
          disabled={saving || loading}
          className="px-5 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 disabled:opacity-50 transition-colors flex items-center gap-2 shadow-subtle self-start sm:self-auto"
        >
          <Save className="w-4 h-4 text-champagne" />
          <span>{saving ? "Saving Changes..." : "Save Configuration"}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* 1. Dynamic Delivery & Shipping Tariff */}
        <div className="p-6 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-hairline">
            <DollarSign className="w-5 h-5 text-champagne-dark" />
            <h2 className="font-serif text-xl font-medium text-obsidian">Delivery & Shipping Fees</h2>
          </div>

          <div className="space-y-4 text-xs">
            <div className="space-y-1">
              <label className="font-semibold text-obsidian uppercase tracking-wider">
                Standard Courier Delivery Rate (PKR)
              </label>
              <input
                type="number"
                min={0}
                step={50}
                value={settings.delivery_fee}
                onChange={(e) => setSettings((p) => ({ ...p, delivery_fee: Number(e.target.value) || 0 }))}
                className="w-full px-3.5 py-2.5 rounded-lg border border-hairline bg-white font-mono text-sm"
              />
              <p className="text-[11px] text-obsidian-500 font-light">
                Applied automatically to all domestic customer orders at checkout (e.g. 200, 350, 500).
              </p>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-obsidian uppercase tracking-wider">
                Free Shipping Threshold (PKR)
              </label>
              <input
                type="number"
                min={0}
                step={500}
                value={settings.free_shipping_threshold}
                onChange={(e) => setSettings((p) => ({ ...p, free_shipping_threshold: Number(e.target.value) || 0 }))}
                className="w-full px-3.5 py-2.5 rounded-lg border border-hairline bg-white font-mono text-sm"
              />
              <p className="text-[11px] text-obsidian-500 font-light">
                Orders with subtotal equal or above this amount automatically receive complimentary free delivery.
              </p>
            </div>
          </div>
        </div>

        {/* 2. Payment Gateway Controls */}
        <div className="p-6 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-hairline">
            <CreditCard className="w-5 h-5 text-champagne-dark" />
            <h2 className="font-serif text-xl font-medium text-obsidian">Payment Methods Available to Clients</h2>
          </div>

          <div className="space-y-4 text-xs">
            {/* COD Switch */}
            <div className="p-3.5 rounded-xl border border-hairline bg-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Banknote className="w-5 h-5 text-champagne-dark" />
                <div>
                  <p className="font-semibold text-obsidian">Cash on Delivery (COD)</p>
                  <p className="text-[11px] text-obsidian-500 font-light">Pay cash to delivery rider at doorstep</p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.payment_methods.cod.enabled}
                  onChange={(e) =>
                    setSettings((p) => ({
                      ...p,
                      payment_methods: {
                        ...p.payment_methods,
                        cod: { ...p.payment_methods.cod, enabled: e.target.checked },
                      },
                    }))
                  }
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-obsidian-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600" />
              </label>
            </div>

            {/* Card Switch */}
            <div className="p-3.5 rounded-xl border border-hairline bg-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CreditCard className="w-5 h-5 text-champagne-dark" />
                <div>
                  <p className="font-semibold text-obsidian">Credit / Debit Card (Online Gateway)</p>
                  <p className="text-[11px] text-obsidian-500 font-light">Visa, MasterCard & PayPak integration</p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.payment_methods.card.enabled}
                  onChange={(e) =>
                    setSettings((p) => ({
                      ...p,
                      payment_methods: {
                        ...p.payment_methods,
                        card: { ...p.payment_methods.card, enabled: e.target.checked },
                      },
                    }))
                  }
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-obsidian-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600" />
              </label>
            </div>

            {/* Bank Transfer Switch */}
            <div className="p-3.5 rounded-xl border border-hairline bg-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Building className="w-5 h-5 text-champagne-dark" />
                <div>
                  <p className="font-semibold text-obsidian">Direct Bank Transfer / IBFT</p>
                  <p className="text-[11px] text-obsidian-500 font-light">Direct account deposits</p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.payment_methods.bank_transfer.enabled}
                  onChange={(e) =>
                    setSettings((p) => ({
                      ...p,
                      payment_methods: {
                        ...p.payment_methods,
                        bank_transfer: { ...p.payment_methods.bank_transfer, enabled: e.target.checked },
                      },
                    }))
                  }
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-obsidian-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600" />
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Promo Codes & Discount Vouchers */}
      <div className="p-6 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-hairline pb-4">
          <div className="flex items-center gap-2">
            <Tag className="w-5 h-5 text-champagne-dark" />
            <div>
              <h2 className="font-serif text-xl font-medium text-obsidian">
                Promo Codes & Discount Vouchers ({coupons.length})
              </h2>
              <p className="text-xs text-obsidian-500 font-light">
                Create promotional discount vouchers that customers can enter and redeem during checkout.
              </p>
            </div>
          </div>
        </div>

        {/* Create Code Form */}
        <form onSubmit={handleCreateCoupon} className="p-4 rounded-xl bg-ivory-sand/40 border border-hairline grid grid-cols-1 sm:grid-cols-5 gap-3 text-xs items-end">
          <div className="space-y-1">
            <label className="font-semibold uppercase text-obsidian">Promo Code</label>
            <input
              type="text"
              required
              value={newCode}
              onChange={(e) => setNewCode(e.target.value.toUpperCase())}
              placeholder="e.g. SUMMER25"
              className="w-full px-3 py-2 rounded-lg border border-hairline bg-white font-mono uppercase font-semibold"
            />
          </div>

          <div className="space-y-1">
            <label className="font-semibold uppercase text-obsidian">Discount Type</label>
            <select
              value={newType}
              onChange={(e) => setNewType(e.target.value as any)}
              className="w-full px-3 py-2 rounded-lg border border-hairline bg-white"
            >
              <option value="percentage">Percentage (%)</option>
              <option value="fixed_amount">Fixed Amount (PKR)</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="font-semibold uppercase text-obsidian">Value</label>
            <input
              type="number"
              required
              min={1}
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              placeholder="e.g. 15"
              className="w-full px-3 py-2 rounded-lg border border-hairline bg-white font-mono"
            />
          </div>

          <div className="space-y-1">
            <label className="font-semibold uppercase text-obsidian">Min Order (PKR)</label>
            <input
              type="number"
              min={0}
              value={newMinOrder}
              onChange={(e) => setNewMinOrder(e.target.value)}
              placeholder="2000"
              className="w-full px-3 py-2 rounded-lg border border-hairline bg-white font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={couponCreating}
            className="w-full py-2.5 rounded-lg bg-obsidian text-ivory font-semibold text-xs hover:bg-obsidian-800 disabled:opacity-50 flex items-center justify-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Promo</span>
          </button>
        </form>

        {/* Existing Coupons Table */}
        <div className="border border-hairline rounded-xl overflow-hidden bg-white text-xs">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-hairline bg-ivory-sand/30 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                <th className="p-3">Coupon Code</th>
                <th className="p-3">Discount</th>
                <th className="p-3">Min Order</th>
                <th className="p-3">Status</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {coupons.map((c) => (
                <tr key={c.id} className="hover:bg-ivory-light">
                  <td className="p-3 font-mono font-bold text-obsidian">{c.code}</td>
                  <td className="p-3">
                    {c.discount_type === "percentage" ? `${c.discount_value}% OFF` : `Rs. ${c.discount_value} OFF`}
                  </td>
                  <td className="p-3 font-mono">
                    {c.minimum_order_amount > 0 ? formatPKR(c.minimum_order_amount) : "No minimum"}
                  </td>
                  <td className="p-3">
                    <span
                      className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full ${
                        c.is_active
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-obsidian/10 text-obsidian-500"
                      }`}
                    >
                      {c.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td className="p-3 text-right space-x-2">
                    <button
                      type="button"
                      onClick={() => handleToggleCoupon(c.id, c.is_active)}
                      className="text-xs text-obsidian-600 hover:underline"
                    >
                      {c.is_active ? "Disable" : "Enable"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteCoupon(c.id)}
                      className="text-xs text-crimson hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Bundles & Capsule Deals */}
      <div className="p-6 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-6">
        <div className="flex items-center gap-2 border-b border-hairline pb-4">
          <Layers className="w-5 h-5 text-champagne-dark" />
          <div>
            <h2 className="font-serif text-xl font-medium text-obsidian">Curated Bundle Offers</h2>
            <p className="text-xs text-obsidian-500 font-light">
              Configure bundle deals (e.g. Buy 2 linen pieces get 15% off, or 3-piece ceremonial sets).
            </p>
          </div>
        </div>

        {/* Existing Bundles List */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {settings.bundles.map((b) => (
            <div key={b.id} className="p-4 rounded-xl border border-hairline bg-white text-xs space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark">
                  {b.badge || "Bundle"}
                </span>
                <button
                  type="button"
                  onClick={() => handleRemoveBundle(b.id)}
                  className="p-1 text-crimson hover:text-crimson/80"
                  title="Remove bundle"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              <h3 className="font-serif text-base font-semibold text-obsidian">{b.name}</h3>
              <p className="text-obsidian-600 font-light text-[11px]">{b.description}</p>
              <div className="pt-1 flex items-center justify-between text-obsidian font-semibold border-t border-hairline">
                <span>Items: {b.item_count}</span>
                <span className="text-emerald-700 font-mono">{b.discount_percentage}% OFF</span>
              </div>
            </div>
          ))}
        </div>

        {/* Add Bundle Mini-Form */}
        <form onSubmit={handleAddBundle} className="p-4 rounded-xl bg-ivory-sand/40 border border-hairline space-y-3 text-xs">
          <span className="font-semibold text-obsidian uppercase tracking-wider block">Add New Bundle Configuration</span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              required
              value={bundleName}
              onChange={(e) => setBundleName(e.target.value)}
              placeholder="Bundle title (e.g. Wedding Season Duo)"
              className="px-3 py-2 rounded-lg border border-hairline bg-white"
            />
            <input
              type="text"
              value={bundleDesc}
              onChange={(e) => setBundleDesc(e.target.value)}
              placeholder="Short description / inclusions"
              className="px-3 py-2 rounded-lg border border-hairline bg-white"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-[10px] text-obsidian-500 font-semibold uppercase">Piece Count</label>
              <input
                type="number"
                min={2}
                value={bundleCount}
                onChange={(e) => setBundleCount(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-hairline bg-white"
              />
            </div>
            <div>
              <label className="text-[10px] text-obsidian-500 font-semibold uppercase">Discount (%)</label>
              <input
                type="number"
                min={5}
                max={50}
                value={bundleDiscount}
                onChange={(e) => setBundleDiscount(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-hairline bg-white"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                className="w-full py-2 rounded-lg bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800"
              >
                + Add Bundle
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
