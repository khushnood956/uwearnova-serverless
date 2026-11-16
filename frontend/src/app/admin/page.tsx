"use client";

import * as React from "react";
import Link from "next/link";
import {
  DollarSign,
  ShoppingBag,
  Package,
  AlertTriangle,
  Users,
  FolderTree,
  CreditCard,
  Plus,
  RefreshCw,
} from "lucide-react";
import { adminApi, AdminReportsOverview } from "@/lib/api/admin";
import { formatPKR } from "@/lib/brand";

export default function AdminOverviewPage() {
  const [overview, setOverview] = React.useState<AdminReportsOverview | null>(null);
  const [loading, setLoading] = React.useState(true);

  const fetchOverview = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.getOverview();
      setOverview(data);
    } catch (err) {
      console.warn("Failed to load store overview:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  return (
    <div className="space-y-8 max-w-7xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Executive Summary
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl font-medium text-obsidian tracking-tight mt-1">
            Store Performance & Operations
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Real-time financial, inventory, and order fulfillment metrics across nationwide Pakistan operations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchOverview}
            disabled={loading}
            className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors"
            title="Refresh metrics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <Link
            href="/admin/products/new"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Product</span>
          </Link>
        </div>
      </div>

      {/* Financial Distinction Cards */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-obsidian-500">
          Financial & Revenue Distinction (PKR)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-obsidian-400 font-semibold">Gross Order Value</span>
            <p className="font-serif text-2xl font-semibold text-obsidian">
              {overview ? formatPKR(Number(overview.gross_sales)) : "..."}
            </p>
            <p className="text-[11px] text-obsidian-500 font-light">Total value of all submitted orders</p>
          </div>

          <div className="p-5 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-emerald-600 font-semibold">Recognized Revenue</span>
            <p className="font-serif text-2xl font-semibold text-emerald-700">
              {overview ? formatPKR(Number(overview.net_revenue)) : "..."}
            </p>
            <p className="text-[11px] text-obsidian-500 font-light">Delivered & confirmed revenue</p>
          </div>

          <div className="p-5 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-champagne-dark font-semibold">Collected Payments</span>
            <p className="font-serif text-2xl font-semibold text-obsidian">
              {overview ? formatPKR(Number(overview.collected_payments)) : "..."}
            </p>
            <p className="text-[11px] text-obsidian-500 font-light">Cash collected & settled cards</p>
          </div>

          <div className="p-5 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-amber-600 font-semibold">Outstanding COD</span>
            <p className="font-serif text-2xl font-semibold text-amber-700">
              {overview ? formatPKR(Number(overview.outstanding_cod)) : "..."}
            </p>
            <p className="text-[11px] text-obsidian-500 font-light">Cash in transit with courier partners</p>
          </div>
        </div>
      </div>

      {/* Operational Metrics Cards */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-obsidian-500">
          Operational Volume & Inventory Health
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
            <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Total Orders</span>
            <p className="font-serif text-xl font-medium text-obsidian mt-1">{overview ? overview.total_orders : "..."}</p>
          </div>
          <div className="p-4 rounded-xl bg-ivory-light border border-amber-200 bg-amber-50/30">
            <span className="text-[10px] uppercase tracking-wider text-amber-700 font-semibold">Pending Orders</span>
            <p className="font-serif text-xl font-medium text-amber-800 mt-1">{overview ? overview.pending_orders : "..."}</p>
          </div>
          <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
            <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Completed Orders</span>
            <p className="font-serif text-xl font-medium text-obsidian mt-1">{overview ? overview.completed_orders : "..."}</p>
          </div>
          <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
            <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Active Products</span>
            <p className="font-serif text-xl font-medium text-obsidian mt-1">{overview ? overview.active_products_count : "..."}</p>
          </div>
          <div className="p-4 rounded-xl bg-ivory-light border border-crimson/20 bg-crimson/5">
            <span className="text-[10px] uppercase tracking-wider text-crimson font-semibold">Low-Stock SKUs</span>
            <p className="font-serif text-xl font-medium text-crimson mt-1">{overview ? overview.low_stock_items_count : "..."}</p>
          </div>
          <div className="p-4 rounded-xl bg-ivory-light border border-hairline">
            <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Customers</span>
            <p className="font-serif text-xl font-medium text-obsidian mt-1">{overview ? overview.total_customers : "..."}</p>
          </div>
        </div>
      </div>

      {/* Quick Administration Hub */}
      <div className="space-y-4 pt-4 border-t border-hairline">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-obsidian-500">
          Management Workspaces
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link
            href="/admin/categories"
            className="p-5 rounded-2xl bg-ivory-light border border-hairline hover:border-champagne hover:shadow-card transition-all group flex flex-col justify-between"
          >
            <div>
              <FolderTree className="w-6 h-6 text-champagne-dark mb-3" />
              <h3 className="font-serif text-base font-medium text-obsidian group-hover:text-champagne-dark transition-colors">
                Departments & Category Hierarchy
              </h3>
              <p className="text-xs text-obsidian-600 font-light mt-1">
                Configure active lines (Men, Women, Kids), manage Coming Soon states (Footwear, Accessories, Perfumes), and arrange subcategories.
              </p>
            </div>
            <span className="text-xs text-champagne-dark font-medium mt-4 inline-flex items-center gap-1">
              Manage Hierarchy →
            </span>
          </Link>

          <Link
            href="/admin/products"
            className="p-5 rounded-2xl bg-ivory-light border border-hairline hover:border-champagne hover:shadow-card transition-all group flex flex-col justify-between"
          >
            <div>
              <ShoppingBag className="w-6 h-6 text-champagne-dark mb-3" />
              <h3 className="font-serif text-base font-medium text-obsidian group-hover:text-champagne-dark transition-colors">
                Product Catalogue & Variants
              </h3>
              <p className="text-xs text-obsidian-600 font-light mt-1">
                Create pieces with inline subcategory creation, adjust inventory counts, manage sizes and color variants.
              </p>
            </div>
            <span className="text-xs text-champagne-dark font-medium mt-4 inline-flex items-center gap-1">
              Browse Catalogue →
            </span>
          </Link>

          <Link
            href="/admin/orders"
            className="p-5 rounded-2xl bg-ivory-light border border-hairline hover:border-champagne hover:shadow-card transition-all group flex flex-col justify-between"
          >
            <div>
              <Package className="w-6 h-6 text-champagne-dark mb-3" />
              <h3 className="font-serif text-base font-medium text-obsidian group-hover:text-champagne-dark transition-colors">
                Order Fulfillment & Status
              </h3>
              <p className="text-xs text-obsidian-600 font-light mt-1">
                Confirm pending customer submissions, track dispatched shipments, and review courier delivery reconciliation.
              </p>
            </div>
            <span className="text-xs text-champagne-dark font-medium mt-4 inline-flex items-center gap-1">
              Process Orders →
            </span>
          </Link>
        </div>
      </div>
    </div>
  );
}
