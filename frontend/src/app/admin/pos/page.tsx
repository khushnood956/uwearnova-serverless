"use client";

import * as React from "react";
import Link from "next/link";
import {
  Store,
  Receipt,
  PlusCircle,
  Search,
  ShoppingCart,
  Trash2,
  Plus,
  Minus,
  CheckCircle2,
  AlertCircle,
  CreditCard,
  Banknote,
  Building,
  RotateCcw,
  Printer,
  X,
  Package,
  Calendar,
  User as UserIcon,
  Phone,
} from "lucide-react";
import { adminApi } from "@/lib/api/admin";
import { catalogApi } from "@/lib/api/catalog";
import { formatPKR, BRAND_CONFIG } from "@/lib/brand";

interface CartLineItem {
  variant_id: number;
  product_id: number;
  product_name: string;
  sku: string;
  size: string;
  color_name: string;
  unit_price: number;
  quantity: number;
  max_stock: number;
  image_url?: string;
}

export default function PosOfflineSalesPage() {
  const [activeTab, setActiveTab] = React.useState<"pos" | "history">("pos");

  // Catalog products for POS picker
  const [products, setProducts] = React.useState<any[]>([]);
  const [productSearch, setProductSearch] = React.useState("");
  const [catalogLoading, setCatalogLoading] = React.useState(true);

  // Cart / Register state
  const [cartItems, setCartItems] = React.useState<CartLineItem[]>([]);
  const [paymentMethod, setPaymentMethod] = React.useState<"cash" | "pos_card" | "bank_transfer">("cash");
  const [discountAmount, setDiscountAmount] = React.useState<string>("0");
  const [customerName, setCustomerName] = React.useState("");
  const [customerPhone, setCustomerPhone] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Completed receipt modal state
  const [activeReceipt, setActiveReceipt] = React.useState<any | null>(null);

  // Sales history state
  const [salesHistory, setSalesHistory] = React.useState<any[]>([]);
  const [historyTotal, setHistoryTotal] = React.useState(0);
  const [historySummary, setHistorySummary] = React.useState<any>({
    total_sales_count: 0,
    total_revenue: "0",
    total_units_sold: 0,
    cash_revenue: "0",
    card_revenue: "0",
  });
  const [historySearch, setHistorySearch] = React.useState("");
  const [historyMethodFilter, setHistoryMethodFilter] = React.useState("");
  const [historyLoading, setHistoryLoading] = React.useState(false);

  // Notifications
  const [toast, setToast] = React.useState<{ message: string; type: "success" | "error" } | null>(null);

  const showToast = (message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Fetch product catalog for POS
  const loadCatalog = React.useCallback(async () => {
    setCatalogLoading(true);
    try {
      const res = await catalogApi.getProducts({ limit: 100 });
      setProducts(res.items || []);
    } catch (err: any) {
      showToast(err.message || "Failed to load products for register", "error");
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  // Fetch sales history
  const loadSalesHistory = React.useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await adminApi.getOfflineSales({
        search: historySearch || undefined,
        payment_method: historyMethodFilter || undefined,
        limit: 50,
      });
      setSalesHistory(res.items || []);
      setHistoryTotal(res.total || 0);
      setHistorySummary(res.summary || {});
    } catch (err: any) {
      showToast(err.message || "Failed to load offline sales history", "error");
    } finally {
      setHistoryLoading(false);
    }
  }, [historySearch, historyMethodFilter]);

  React.useEffect(() => {
    loadCatalog();
    loadSalesHistory();
  }, [loadCatalog, loadSalesHistory]);

  // Cart operations
  const addToCart = (product: any, variant: any) => {
    if (variant.inventory_count <= 0) {
      showToast(`SKU ${variant.sku} is out of stock!`, "error");
      return;
    }

    setCartItems((prev) => {
      const existingIndex = prev.findIndex((item) => item.variant_id === variant.id);
      if (existingIndex > -1) {
        const item = prev[existingIndex];
        if (item.quantity + 1 > variant.inventory_count) {
          showToast(`Cannot add more than ${variant.inventory_count} units on hand.`, "error");
          return prev;
        }
        const updated = [...prev];
        updated[existingIndex] = { ...item, quantity: item.quantity + 1 };
        return updated;
      }

      const primaryImg = product.images?.find((img: any) => img.is_primary)?.image_url || product.images?.[0]?.image_url;
      const unitPrice = variant.price ? Number(variant.price) : Number(product.price);

      return [
        ...prev,
        {
          variant_id: variant.id,
          product_id: product.id,
          product_name: product.name,
          sku: variant.sku,
          size: variant.size,
          color_name: variant.color_name,
          unit_price: unitPrice,
          quantity: 1,
          max_stock: variant.inventory_count,
          image_url: primaryImg,
        },
      ];
    });
  };

  const updateQuantity = (variant_id: number, delta: number) => {
    setCartItems((prev) =>
      prev
        .map((item) => {
          if (item.variant_id === variant_id) {
            const nextQty = item.quantity + delta;
            if (nextQty > item.max_stock) {
              showToast(`Only ${item.max_stock} units available in stock.`, "error");
              return item;
            }
            return { ...item, quantity: nextQty };
          }
          return item;
        })
        .filter((item) => item.quantity > 0)
    );
  };

  const removeFromCart = (variant_id: number) => {
    setCartItems((prev) => prev.filter((item) => item.variant_id !== variant_id));
  };

  const clearRegister = () => {
    setCartItems([]);
    setDiscountAmount("0");
    setCustomerName("");
    setCustomerPhone("");
    setNotes("");
  };

  // Calculations
  const subtotal = cartItems.reduce((acc, item) => acc + item.unit_price * item.quantity, 0);
  const discountVal = Math.max(0, Number(discountAmount) || 0);
  const totalPayable = Math.max(0, subtotal - discountVal);

  // Submit sale
  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cartItems.length === 0) {
      showToast("Please add at least one piece to the register cart.", "error");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        customer_name: customerName.trim() || undefined,
        customer_phone: customerPhone.trim() || undefined,
        payment_method: paymentMethod,
        discount_amount: discountVal,
        tax_amount: 0,
        notes: notes.trim() || undefined,
        items: cartItems.map((item) => ({
          variant_id: item.variant_id,
          quantity: item.quantity,
          unit_price_override: item.unit_price,
        })),
      };

      const result = await adminApi.createOfflineSale(payload);
      showToast(`Sale recorded successfully! Receipt #${result.receipt_number}`);
      setActiveReceipt(result);
      clearRegister();
      loadCatalog(); // Refresh stock counts
      loadSalesHistory(); // Refresh history
    } catch (err: any) {
      showToast(err.message || "Failed to process offline sale", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Void a sale
  const handleVoidSale = async (saleId: number, receiptNum: string) => {
    if (!confirm(`Are you sure you want to VOID receipt #${receiptNum}? This will restore all stock items to the database inventory.`)) {
      return;
    }

    try {
      await adminApi.voidOfflineSale(saleId);
      showToast(`Receipt #${receiptNum} voided and stock restored.`);
      loadSalesHistory();
      loadCatalog();
    } catch (err: any) {
      showToast(err.message || "Could not void sale", "error");
    }
  };

  // Filter products for display
  const filteredProducts = products.filter((p) => {
    const term = productSearch.toLowerCase().trim();
    if (!term) return true;
    return (
      p.name?.toLowerCase().includes(term) ||
      p.slug?.toLowerCase().includes(term) ||
      p.variants?.some((v: any) => v.sku?.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-card text-xs font-medium flex items-center gap-2 border animate-in slide-in-from-bottom-2 ${
            toast.type === "success"
              ? "bg-emerald-950 text-emerald-200 border-emerald-800"
              : "bg-crimson text-ivory border-crimson/80"
          }`}
        >
          {toast.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-champagne-dark mb-1">
            <Store className="w-4 h-4" />
            <span>Storefront Retail & Counter Register</span>
          </div>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight">
            Offline Sales & POS
          </h1>
          <p className="text-xs text-obsidian-600 font-light mt-0.5">
            Ring up walk-in customers at the physical boutique, deduct real-time stock, and generate invoices.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-ivory-sand p-1 rounded-xl border border-hairline shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab("pos")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "pos"
                ? "bg-obsidian text-ivory shadow-subtle"
                : "text-obsidian-600 hover:text-obsidian"
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Sale (Register)</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab("history");
              loadSalesHistory();
            }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "history"
                ? "bg-obsidian text-ivory shadow-subtle"
                : "text-obsidian-600 hover:text-obsidian"
            }`}
          >
            <Receipt className="w-3.5 h-3.5" />
            <span>Sales History ({historyTotal})</span>
          </button>
        </div>
      </div>

      {/* Top Metrics Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-ivory-light border border-hairline shadow-subtle space-y-1">
          <span className="text-[10px] font-semibold text-obsidian-500 uppercase tracking-wider">
            Total In-Store Revenue
          </span>
          <p className="font-serif text-2xl font-medium text-obsidian">
            {formatPKR(Number(historySummary.total_revenue) || 0)}
          </p>
          <span className="text-[10px] text-emerald-700 font-medium">Completed shop transactions</span>
        </div>

        <div className="p-4 rounded-xl bg-ivory-light border border-hairline shadow-subtle space-y-1">
          <span className="text-[10px] font-semibold text-obsidian-500 uppercase tracking-wider">
            Total Walk-in Orders
          </span>
          <p className="font-serif text-2xl font-medium text-obsidian">
            {historySummary.total_sales_count || 0}
          </p>
          <span className="text-[10px] text-obsidian-500 font-light">POS counter receipts</span>
        </div>

        <div className="p-4 rounded-xl bg-ivory-light border border-hairline shadow-subtle space-y-1">
          <span className="text-[10px] font-semibold text-obsidian-500 uppercase tracking-wider">
            Physical Units Sold
          </span>
          <p className="font-serif text-2xl font-medium text-obsidian">
            {historySummary.total_units_sold || 0}
          </p>
          <span className="text-[10px] text-obsidian-500 font-light">Garments & pieces</span>
        </div>

        <div className="p-4 rounded-xl bg-ivory-light border border-hairline shadow-subtle space-y-1">
          <span className="text-[10px] font-semibold text-obsidian-500 uppercase tracking-wider">
            Tender Split (Cash / Card)
          </span>
          <p className="font-serif text-lg font-medium text-obsidian truncate">
            {formatPKR(Number(historySummary.cash_revenue) || 0)} / {formatPKR(Number(historySummary.card_revenue) || 0)}
          </p>
          <span className="text-[10px] text-obsidian-500 font-light">Cash vs POS Terminal</span>
        </div>
      </div>

      {/* TAB 1: POS REGISTER */}
      {activeTab === "pos" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Product Selection Grid */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between gap-4">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-obsidian-400" />
                <input
                  type="text"
                  placeholder="Search catalogue by piece title or SKU..."
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-xs rounded-xl border border-hairline bg-ivory-light focus:ring-1 focus:ring-champagne"
                />
              </div>
              <span className="text-xs text-obsidian-500 shrink-0">
                {filteredProducts.length} Piece{filteredProducts.length === 1 ? "" : "s"}
              </span>
            </div>

            {/* Catalog List */}
            {catalogLoading ? (
              <div className="p-12 text-center text-xs text-obsidian-400">Loading catalogue...</div>
            ) : filteredProducts.length === 0 ? (
              <div className="p-12 text-center text-xs text-obsidian-500 bg-ivory-light rounded-2xl border border-hairline">
                No matching products found. Check your search term or add products in Catalogue.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[640px] overflow-y-auto pr-1">
                {filteredProducts.map((p) => {
                  const primaryImg = p.images?.find((img: any) => img.is_primary)?.image_url || p.images?.[0]?.image_url;
                  return (
                    <div
                      key={p.id}
                      className="p-3 rounded-xl bg-ivory-light border border-hairline shadow-subtle flex flex-col justify-between space-y-3"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-14 h-16 rounded-lg bg-ivory-sand overflow-hidden shrink-0 border border-hairline relative">
                          {primaryImg ? (
                            <img src={primaryImg} alt={p.name} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-obsidian-300">
                              <Package className="w-5 h-5" />
                            </div>
                          )}
                        </div>
                        <div className="space-y-0.5 min-w-0">
                          <h4 className="text-xs font-semibold text-obsidian truncate" title={p.name}>
                            {p.name}
                          </h4>
                          <p className="text-[11px] text-obsidian-500 font-mono">
                            {formatPKR(Number(p.price))}
                          </p>
                          <span className="text-[9px] uppercase tracking-wider font-medium text-champagne-dark">
                            {p.category?.name || "Apparel"}
                          </span>
                        </div>
                      </div>

                      {/* Variant Buttons */}
                      <div className="space-y-1 pt-2 border-t border-hairline">
                        <span className="text-[10px] text-obsidian-500 font-medium uppercase tracking-wider block">
                          Select Variant / Size:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {p.variants?.map((v: any) => {
                            const isOutOfStock = v.inventory_count <= 0;
                            return (
                              <button
                                key={v.id}
                                type="button"
                                onClick={() => addToCart(p, v)}
                                disabled={isOutOfStock}
                                title={`${v.sku} - ${v.color_name}`}
                                className={`px-2.5 py-1 rounded-md text-[11px] font-medium border transition-colors flex items-center gap-1.5 ${
                                  isOutOfStock
                                    ? "bg-ivory-sand text-obsidian-300 border-hairline line-through cursor-not-allowed"
                                    : "bg-ivory hover:bg-champagne-light/40 border-hairline text-obsidian hover:border-champagne"
                                }`}
                              >
                                <span>{v.size}</span>
                                <span className="text-[9px] text-obsidian-400 font-mono">
                                  ({v.inventory_count})
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Column: Register Receipt & Checkout */}
          <div className="lg:col-span-5 bg-ivory-light border border-hairline rounded-2xl p-5 shadow-card space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-hairline">
              <div className="flex items-center gap-2">
                <ShoppingCart className="w-4 h-4 text-obsidian" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-obsidian">
                  Current Register Cart
                </h3>
              </div>
              {cartItems.length > 0 && (
                <button
                  type="button"
                  onClick={clearRegister}
                  className="text-[11px] text-crimson hover:underline"
                >
                  Clear Cart
                </button>
              )}
            </div>

            {/* Cart Items List */}
            {cartItems.length === 0 ? (
              <div className="py-12 text-center text-xs text-obsidian-400 space-y-2">
                <ShoppingCart className="w-8 h-8 mx-auto text-obsidian-300" />
                <p>Register cart is empty.</p>
                <p className="text-[11px] text-obsidian-500">
                  Select variants from the catalogue on the left to add items to this sale.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
                {cartItems.map((item) => (
                  <div
                    key={item.variant_id}
                    className="p-2.5 rounded-xl bg-ivory border border-hairline flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="min-w-0 space-y-0.5">
                      <p className="font-semibold text-obsidian truncate">{item.product_name}</p>
                      <p className="text-[10px] text-obsidian-500">
                        {item.size} &bull; {item.color_name} &bull; <span className="font-mono">{item.sku}</span>
                      </p>
                      <p className="text-[11px] font-mono text-obsidian-700">
                        {formatPKR(item.unit_price)} &times; {item.quantity} ={" "}
                        <strong className="text-obsidian">{formatPKR(item.unit_price * item.quantity)}</strong>
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <div className="flex items-center border border-hairline rounded-lg bg-ivory-light">
                        <button
                          type="button"
                          onClick={() => updateQuantity(item.variant_id, -1)}
                          className="p-1 hover:bg-ivory-sand rounded-l-lg"
                        >
                          <Minus className="w-3 h-3 text-obsidian" />
                        </button>
                        <span className="w-6 text-center font-mono font-semibold text-xs">
                          {item.quantity}
                        </span>
                        <button
                          type="button"
                          onClick={() => updateQuantity(item.variant_id, 1)}
                          className="p-1 hover:bg-ivory-sand rounded-r-lg"
                        >
                          <Plus className="w-3 h-3 text-obsidian" />
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFromCart(item.variant_id)}
                        className="p-1 text-crimson hover:bg-crimson/10 rounded-lg"
                        title="Remove line"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Form Fields: Tender & Customer */}
            <form onSubmit={handleCheckout} className="space-y-4 pt-3 border-t border-hairline">
              {/* Payment Tender Method */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-semibold text-obsidian uppercase tracking-wider block">
                  Payment Tender
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setPaymentMethod("cash")}
                    className={`py-2 px-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                      paymentMethod === "cash"
                        ? "bg-obsidian text-ivory border-obsidian"
                        : "bg-ivory text-obsidian-600 border-hairline hover:bg-ivory-sand"
                    }`}
                  >
                    <Banknote className="w-3.5 h-3.5" />
                    <span>Cash</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPaymentMethod("pos_card")}
                    className={`py-2 px-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                      paymentMethod === "pos_card"
                        ? "bg-obsidian text-ivory border-obsidian"
                        : "bg-ivory text-obsidian-600 border-hairline hover:bg-ivory-sand"
                    }`}
                  >
                    <CreditCard className="w-3.5 h-3.5" />
                    <span>POS Card</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPaymentMethod("bank_transfer")}
                    className={`py-2 px-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                      paymentMethod === "bank_transfer"
                        ? "bg-obsidian text-ivory border-obsidian"
                        : "bg-ivory text-obsidian-600 border-hairline hover:bg-ivory-sand"
                    }`}
                  >
                    <Building className="w-3.5 h-3.5" />
                    <span>Bank Transfer</span>
                  </button>
                </div>
              </div>

              {/* Discount & Optional Customer Fields */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-obsidian uppercase tracking-wider">
                    Discount (PKR)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={discountAmount}
                    onChange={(e) => setDiscountAmount(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-hairline bg-ivory font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-obsidian uppercase tracking-wider">
                    Customer Name (Opt)
                  </label>
                  <input
                    type="text"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    placeholder="Walk-in Client"
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-hairline bg-ivory"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-obsidian uppercase tracking-wider">
                    Customer Phone (Opt)
                  </label>
                  <input
                    type="tel"
                    value={customerPhone}
                    onChange={(e) => setCustomerPhone(e.target.value)}
                    placeholder="03001234567"
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-hairline bg-ivory font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-obsidian uppercase tracking-wider">
                    Register Notes (Opt)
                  </label>
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Counter 1, Cashier note"
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-hairline bg-ivory"
                  />
                </div>
              </div>

              {/* Totals Breakdown */}
              <div className="space-y-1.5 pt-3 border-t border-hairline text-xs">
                <div className="flex justify-between text-obsidian-600">
                  <span>Subtotal</span>
                  <span className="font-mono">{formatPKR(subtotal)}</span>
                </div>
                {discountVal > 0 && (
                  <div className="flex justify-between text-crimson font-medium">
                    <span>Discount</span>
                    <span className="font-mono">- {formatPKR(discountVal)}</span>
                  </div>
                )}
                <div className="flex justify-between text-base font-semibold text-obsidian pt-1 border-t border-hairline">
                  <span>Total Payable</span>
                  <span className="font-mono text-champagne-dark">{formatPKR(totalPayable)}</span>
                </div>
              </div>

              {/* Complete & Ring Up Button */}
              <button
                type="submit"
                disabled={isSubmitting || cartItems.length === 0}
                className="w-full py-3 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 disabled:opacity-50 transition-colors flex items-center justify-center gap-2 shadow-subtle"
              >
                {isSubmitting ? (
                  <span>Recording Sale & Deducting Stock...</span>
                ) : (
                  <>
                    <Receipt className="w-4 h-4" />
                    <span>Complete Sale & Deduct Stock ({formatPKR(totalPayable)})</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: SALES HISTORY & RECEIPTS */}
      {activeTab === "history" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-ivory-light p-3.5 rounded-xl border border-hairline">
            <div className="relative flex-1 w-full sm:w-auto">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-obsidian-400" />
              <input
                type="text"
                placeholder="Search receipt #, customer name or phone..."
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-hairline bg-ivory"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <select
                value={historyMethodFilter}
                onChange={(e) => setHistoryMethodFilter(e.target.value)}
                className="px-3 py-1.5 text-xs rounded-lg border border-hairline bg-ivory"
              >
                <option value="">All Tenders</option>
                <option value="cash">Cash</option>
                <option value="pos_card">POS Card</option>
                <option value="bank_transfer">Bank Transfer</option>
              </select>

              <button
                type="button"
                onClick={loadSalesHistory}
                className="px-3 py-1.5 rounded-lg border border-hairline bg-ivory hover:bg-ivory-sand text-xs font-semibold"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-2xl border border-hairline bg-ivory-light shadow-subtle overflow-hidden">
            {historyLoading ? (
              <div className="p-12 text-center text-xs text-obsidian-400">Loading sales history...</div>
            ) : salesHistory.length === 0 ? (
              <div className="p-12 text-center text-xs text-obsidian-500">
                No offline walk-in sales found. Switch to the Register tab to record a sale.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-ivory-sand border-b border-hairline text-obsidian-600 font-semibold uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Receipt #</th>
                      <th className="py-3 px-4">Date & Time</th>
                      <th className="py-3 px-4">Customer</th>
                      <th className="py-3 px-4">Pieces</th>
                      <th className="py-3 px-4">Tender</th>
                      <th className="py-3 px-4 text-right">Total (PKR)</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline">
                    {salesHistory.map((s) => (
                      <tr key={s.id} className="hover:bg-ivory-sand/40 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold text-obsidian">
                          {s.receipt_number}
                        </td>
                        <td className="py-3 px-4 text-obsidian-600 whitespace-nowrap">
                          {new Date(s.sale_date).toLocaleString("en-PK", {
                            dateStyle: "short",
                            timeStyle: "short",
                          })}
                        </td>
                        <td className="py-3 px-4">
                          <p className="font-medium text-obsidian">{s.customer_name || "Walk-in Client"}</p>
                          {s.customer_phone && (
                            <p className="text-[10px] text-obsidian-500 font-mono">{s.customer_phone}</p>
                          )}
                        </td>
                        <td className="py-3 px-4 text-obsidian-700">
                          {s.items?.length || 0} line item{s.items?.length === 1 ? "" : "s"}
                        </td>
                        <td className="py-3 px-4 capitalize text-obsidian-600 font-medium">
                          {s.payment_method?.replace("_", " ")}
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-semibold text-obsidian">
                          {formatPKR(Number(s.total_amount))}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                              s.status === "completed"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-crimson/10 text-crimson border border-crimson/20"
                            }`}
                          >
                            {s.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right space-x-2 whitespace-nowrap">
                          <button
                            type="button"
                            onClick={() => setActiveReceipt(s)}
                            className="p-1 text-obsidian hover:bg-ivory rounded-md"
                            title="View Receipt"
                          >
                            <Receipt className="w-3.5 h-3.5" />
                          </button>
                          {s.status === "completed" && (
                            <button
                              type="button"
                              onClick={() => handleVoidSale(s.id, s.receipt_number)}
                              className="p-1 text-crimson hover:bg-crimson/10 rounded-md"
                              title="Void and restore stock"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
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
      )}

      {/* RECEIPT MODAL */}
      {activeReceipt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/70 backdrop-blur-xs">
          <div className="w-full max-w-md bg-white text-obsidian rounded-2xl p-6 shadow-card border border-hairline space-y-4 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-hairline">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-champagne-dark">
                Official POS Receipt
              </span>
              <button
                type="button"
                onClick={() => setActiveReceipt(null)}
                className="p-1 text-obsidian-400 hover:text-obsidian"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Printable Receipt Body */}
            <div id="pos-print-area" className="space-y-4 text-xs font-mono">
              {/* Brand Banner */}
              <div className="text-center space-y-1 pb-3 border-b border-dashed border-obsidian-300">
                <img
                  src="/logo/transparent/navbar/logo-navbar-dark.svg"
                  alt="UWEARNOVA"
                  className="h-8 mx-auto object-contain"
                />
                <p className="text-[10px] font-sans text-obsidian-500 uppercase tracking-widest mt-1">
                  Atelier & Flagship Store &bull; Sialkot, Pakistan
                </p>
                <p className="text-[11px] font-bold text-obsidian">{activeReceipt.receipt_number}</p>
                <p className="text-[10px] text-obsidian-500">
                  {new Date(activeReceipt.sale_date).toLocaleString("en-PK")}
                </p>
              </div>

              {/* Customer info */}
              <div className="space-y-0.5 text-[11px] pb-2 border-b border-dashed border-obsidian-300">
                <p>
                  <strong>Customer:</strong> {activeReceipt.customer_name || "Walk-in Guest"}
                </p>
                {activeReceipt.customer_phone && (
                  <p>
                    <strong>Phone:</strong> {activeReceipt.customer_phone}
                  </p>
                )}
                <p>
                  <strong>Tender:</strong>{" "}
                  <span className="uppercase">{activeReceipt.payment_method?.replace("_", " ")}</span>
                </p>
                {activeReceipt.staff_name && (
                  <p>
                    <strong>Cashier:</strong> {activeReceipt.staff_name}
                  </p>
                )}
              </div>

              {/* Items List */}
              <div className="space-y-2 py-1">
                {activeReceipt.items?.map((item: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-start gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold text-obsidian truncate">{item.product_name}</p>
                      <p className="text-[10px] text-obsidian-500">{item.variant_label}</p>
                      <p className="text-[10px] text-obsidian-400">
                        {item.quantity} &times; {formatPKR(Number(item.unit_price))}
                      </p>
                    </div>
                    <span className="font-semibold shrink-0">
                      {formatPKR(Number(item.line_total))}
                    </span>
                  </div>
                ))}
              </div>

              {/* Totals */}
              <div className="space-y-1 pt-3 border-t border-dashed border-obsidian-300">
                <div className="flex justify-between">
                  <span>Subtotal:</span>
                  <span>{formatPKR(Number(activeReceipt.subtotal))}</span>
                </div>
                {Number(activeReceipt.discount_amount) > 0 && (
                  <div className="flex justify-between text-crimson">
                    <span>Discount:</span>
                    <span>- {formatPKR(Number(activeReceipt.discount_amount))}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm font-bold pt-1 border-t border-obsidian text-obsidian">
                  <span>TOTAL:</span>
                  <span>{formatPKR(Number(activeReceipt.total_amount))}</span>
                </div>
              </div>

              {/* Footer Note */}
              <div className="text-center text-[10px] text-obsidian-500 pt-3 border-t border-dashed border-obsidian-300 space-y-0.5">
                <p className="font-sans font-medium">Thank you for curating with {BRAND_CONFIG.name}.</p>
                <p>7-Day Store Exchange with Original Receipt</p>
                <p>In-Store & Online: {BRAND_CONFIG.contact.phone}</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-2 border-t border-hairline">
              <button
                type="button"
                onClick={() => window.print()}
                className="flex-1 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold flex items-center justify-center gap-1.5 hover:bg-obsidian-800"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print Receipt</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveReceipt(null)}
                className="px-4 py-2 rounded-button border border-hairline text-xs font-semibold text-obsidian hover:bg-ivory-sand"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
