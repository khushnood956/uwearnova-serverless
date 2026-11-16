"use client";

import * as React from "react";
import Link from "next/link";
import {
  ShoppingBag,
  Plus,
  Search,
  Filter,
  CheckCircle,
  AlertCircle,
  Archive,
  ArrowUpRight,
  Trash2,
  RefreshCw,
  ExternalLink,
  Pencil,
  Image as ImageIcon,
} from "lucide-react";
import { adminApi } from "@/lib/api/admin";
import { Product } from "@/lib/api/types";
import { formatPKR } from "@/lib/brand";

export default function AdminProductsListPage() {
  const [products, setProducts] = React.useState<Product[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [selectedIds, setSelectedIds] = React.useState<number[]>([]);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadProducts = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getProducts({
        search: search || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        limit: 50,
      });
      setProducts(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      showNotification(err.message || "Failed to load products", "error");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  React.useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  // Handle Archive / Publish toggle
  const handleToggleStatus = async (product: Product) => {
    try {
      if (product.status === "active") {
        await adminApi.archiveProduct(product.id);
        showNotification(`Product "${product.name}" archived.`);
      } else {
        await adminApi.publishProduct(product.id);
        showNotification(`Product "${product.name}" published to storefront.`);
      }
      loadProducts();
    } catch (err: any) {
      showNotification(err.message || "Failed to update product status", "error");
    }
  };

  // Handle Delete
  const handleDelete = async (id: number | string, name: string) => {
    if (!confirm(`Are you sure you want to delete product "${name}"?`)) return;
    try {
      await adminApi.deleteProduct(id);
      showNotification(`Product "${name}" deleted.`);
      loadProducts();
    } catch (err: any) {
      showNotification(err.message || "Failed to delete product", "error");
    }
  };

  // Bulk status update
  const handleBulkStatus = async (newStatus: "draft" | "active" | "archived") => {
    if (selectedIds.length === 0) return;
    try {
      await adminApi.bulkUpdateStatus(selectedIds, newStatus);
      showNotification(`Updated ${selectedIds.length} product(s) to ${newStatus}.`);
      setSelectedIds([]);
      loadProducts();
    } catch (err: any) {
      showNotification(err.message || "Bulk operation failed", "error");
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === products.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(products.map((p) => p.id));
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
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
            Product Administration
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Catalogue & SKU Inventory ({total})
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            View, search, filter, and modify garments and leather goods across the store catalogue.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadProducts}
            disabled={loading}
            className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors"
            title="Refresh catalogue"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <Link
            href="/admin/products/new"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add Product</span>
          </Link>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-ivory-light border border-hairline">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-obsidian-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by product name, slug, or SKU..."
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
          />
        </div>

        {/* Status Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-xs">
          {[
            { key: "all", label: "All Statuses" },
            { key: "active", label: "Active" },
            { key: "draft", label: "Draft" },
            { key: "archived", label: "Archived" },
          ].map((st) => (
            <button
              key={st.key}
              type="button"
              onClick={() => setStatusFilter(st.key)}
              className={`px-3 py-1.5 rounded-button font-medium transition-colors ${
                statusFilter === st.key
                  ? "bg-obsidian text-ivory font-semibold"
                  : "bg-ivory text-obsidian-600 hover:bg-ivory-sand border border-hairline"
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      {/* Bulk Action Bar (when rows are selected) */}
      {selectedIds.length > 0 && (
        <div className="p-3 bg-champagne-light rounded-xl border border-champagne flex items-center justify-between text-xs text-obsidian animate-in fade-in">
          <span>
            Selected <strong>{selectedIds.length}</strong> piece(s)
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleBulkStatus("active")}
              className="px-3 py-1 rounded bg-obsidian text-ivory font-semibold text-[11px]"
            >
              Bulk Publish
            </button>
            <button
              type="button"
              onClick={() => handleBulkStatus("archived")}
              className="px-3 py-1 rounded bg-ivory text-obsidian border border-hairline text-[11px]"
            >
              Bulk Archive
            </button>
            <button
              type="button"
              onClick={() => setSelectedIds([])}
              className="text-[11px] text-obsidian-500 hover:underline px-2"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Products Table */}
      <div className="bg-ivory-light rounded-2xl border border-hairline shadow-subtle overflow-hidden">
        {loading ? (
          <div className="py-20 text-center">
            <div className="w-7 h-7 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs text-obsidian-500">Querying product catalogue...</p>
          </div>
        ) : products.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <ShoppingBag className="w-8 h-8 text-obsidian-300 mx-auto" />
            <p className="text-sm font-medium text-obsidian">No products matched your criteria</p>
            <Link
              href="/admin/products/new"
              className="text-xs text-champagne-dark font-medium underline inline-block"
            >
              Create first product
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline bg-ivory-sand/40 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                  <th className="p-4 w-10">
                    <input
                      type="checkbox"
                      checked={selectedIds.length === products.length && products.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded border-hairline"
                    />
                  </th>
                  <th className="p-4">Piece Title & Details</th>
                  <th className="p-4">Department / Line</th>
                  <th className="p-4">Retail Price</th>
                  <th className="p-4">Variants & Stock</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {products.map((p) => {
                  const isChecked = selectedIds.includes(p.id);
                  const totalInventory = (p.variants || []).reduce(
                    (sum, v) => sum + (v.inventory_count || 0),
                    0
                  );

                  return (
                    <tr
                      key={p.id}
                      className={`hover:bg-ivory transition-colors ${isChecked ? "bg-champagne-light/30" : ""}`}
                    >
                      <td className="p-4">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleSelect(p.id)}
                          className="rounded border-hairline"
                        />
                      </td>

                      <td className="p-4">
                        <Link
                          href={`/admin/products/${p.id}/edit`}
                          className="font-serif text-sm font-medium text-obsidian hover:text-champagne-dark hover:underline block"
                        >
                          {p.name}
                        </Link>
                        <div className="font-mono text-obsidian-400 text-[11px]">/{p.slug}</div>
                      </td>

                      <td className="p-4 text-obsidian-700">
                        {p.category?.name || "General"}
                      </td>

                      <td className="p-4 font-mono font-medium text-obsidian">
                        {formatPKR(Number(p.price))}
                      </td>

                      <td className="p-4">
                        <span className="font-medium text-obsidian">{p.variants?.length || 0} variant(s)</span>
                        <div className="text-[11px] text-obsidian-500">{totalInventory} units in stock</div>
                      </td>

                      <td className="p-4">
                        <span
                          className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                            p.status === "active"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : p.status === "draft"
                              ? "bg-amber-50 text-amber-700 border border-amber-200"
                              : "bg-obsidian/10 text-obsidian"
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>

                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            href={`/admin/products/${p.id}/edit`}
                            className="p-1 text-obsidian-600 hover:text-champagne-dark"
                            title="Edit product details & images"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </Link>
                          <Link
                            href={`/product/${p.slug}`}
                            target="_blank"
                            className="p-1 text-obsidian-400 hover:text-obsidian"
                            title="Preview on storefront"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </Link>
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(p)}
                            className="p-1 text-obsidian-500 hover:text-champagne-dark"
                            title={p.status === "active" ? "Archive product" : "Publish product"}
                          >
                            <Archive className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(p.id, p.name)}
                            className="p-1 text-crimson hover:text-crimson/80"
                            title="Delete piece"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
