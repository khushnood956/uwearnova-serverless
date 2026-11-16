"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  CreditCard,
  Banknote,
  Building,
  Truck,
  ShieldCheck,
  AlertCircle,
  CheckCircle,
  Tag,
  Loader2,
  X,
  Sparkles,
} from "lucide-react";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import { shippingApi, ShippingMethodQuoteItem, ShippingQuoteResponse } from "@/lib/api/shipping";
import { ordersApi, CheckoutRequest } from "@/lib/api/orders";
import { customerApi, CustomerAddress } from "@/lib/api/customer";
import { settingsApi, DynamicStoreSettings, DEFAULT_STORE_SETTINGS } from "@/lib/api/settings";
import { discountsApi } from "@/lib/api/discounts";
import { formatPKR } from "@/lib/brand";

const CITIES = [
  "Lahore",
  "Karachi",
  "Islamabad",
  "Rawalpindi",
  "Faisalabad",
  "Multan",
  "Peshawar",
  "Quetta",
  "Sialkot",
  "Gujranwala",
  "Hyderabad",
  "Abbottabad",
];

export function CheckoutForm() {
  const router = useRouter();
  const { items, subtotal, clearCart, refreshCart } = useCart();
  const { user, isAuthenticated } = useAuth();

  // Dynamic store settings (payment methods enabled, delivery fee)
  const [storeSettings, setStoreSettings] = React.useState<DynamicStoreSettings>(DEFAULT_STORE_SETTINGS);

  // Saved addresses for signed-in customer
  const [savedAddresses, setSavedAddresses] = React.useState<CustomerAddress[]>([]);
  const [selectedSavedAddressId, setSelectedSavedAddressId] = React.useState<number | "new">("new");

  // Form Fields
  const [formData, setFormData] = React.useState({
    fullName: "",
    email: "",
    phone: "",
    addressLine1: "",
    addressLine2: "",
    city: "Lahore",
    postalCode: "54000",
    customerNote: "",
  });

  // Selected Payment Method: "cod" | "card" | "bank_transfer"
  const [paymentMethod, setPaymentMethod] = React.useState<string>("cod");

  // Promo Code State
  const [promoInput, setPromoInput] = React.useState("");
  const [promoLoading, setPromoLoading] = React.useState(false);
  const [appliedPromo, setAppliedPromo] = React.useState<{
    code: string;
    discount_amount: number;
    discount_type: string;
    discount_value: number;
    message: string;
  } | null>(null);
  const [promoError, setPromoError] = React.useState<string | null>(null);

  // Shipping Quote State
  const [quoteResponse, setQuoteResponse] = React.useState<ShippingQuoteResponse | null>(null);
  const [selectedMethodCode, setSelectedMethodCode] = React.useState<string>("standard");
  const [quoteLoading, setQuoteLoading] = React.useState(false);
  const [quoteError, setQuoteError] = React.useState<string | null>(null);

  // Submission State
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // Load dynamic settings on mount
  React.useEffect(() => {
    settingsApi.getSettings().then((s) => {
      setStoreSettings(s);
      // Ensure selected method is one that is enabled
      if (!s.payment_methods.cod.enabled) {
        if (s.payment_methods.card.enabled) setPaymentMethod("card");
        else if (s.payment_methods.bank_transfer.enabled) setPaymentMethod("bank_transfer");
      }
    });
  }, []);

  // Auto-populate user data if authenticated
  React.useEffect(() => {
    if (isAuthenticated && user) {
      setFormData((prev) => ({
        ...prev,
        fullName: prev.fullName || `${user.first_name || ""} ${user.last_name || ""}`.trim() || "",
        email: prev.email || user.email || "",
      }));

      // Fetch saved address book
      customerApi.getAddresses()
        .then((res) => {
          if (res && res.items && res.items.length > 0) {
            setSavedAddresses(res.items);
            const def = res.items.find((a) => a.is_default) || res.items[0];
            setSelectedSavedAddressId(def.id);
            setFormData((prev) => ({
              ...prev,
              fullName: def.full_name || prev.fullName,
              phone: def.phone || prev.phone,
              addressLine1: def.street_address,
              addressLine2: def.apartment_suite || "",
              city: def.city || "Lahore",
              postalCode: def.postal_code || "54000",
            }));
          }
        })
        .catch(() => {});
    }
  }, [isAuthenticated, user]);

  const handleSelectSavedAddress = (idStr: string) => {
    if (idStr === "new") {
      setSelectedSavedAddressId("new");
      return;
    }
    const id = Number(idStr);
    setSelectedSavedAddressId(id);
    const addr = savedAddresses.find((a) => a.id === id);
    if (addr) {
      setFormData((prev) => ({
        ...prev,
        fullName: addr.full_name,
        phone: addr.phone,
        addressLine1: addr.street_address,
        addressLine2: addr.apartment_suite || "",
        city: addr.city,
        postalCode: addr.postal_code || "",
      }));
    }
  };

  // Fetch Authoritative Backend Shipping Quote whenever city or subtotal changes
  const fetchShippingQuote = React.useCallback(async (city: string) => {
    if (!city) return;
    setQuoteLoading(true);
    setQuoteError(null);
    try {
      const res = await shippingApi.getQuote({
        city,
        is_cod: paymentMethod === "cod",
        subtotal,
      });
      setQuoteResponse(res);
      if (res.available_methods && res.available_methods.length > 0) {
        setSelectedMethodCode(res.recommended_method_code || res.available_methods[0].code);
      }
    } catch {
      setQuoteError("Courier dynamic tariff engine temporarily unreachable; using standard flat rate.");
    } finally {
      setQuoteLoading(false);
    }
  }, [subtotal, paymentMethod]);

  React.useEffect(() => {
    fetchShippingQuote(formData.city);
  }, [formData.city, fetchShippingQuote]);

  // Selected Shipping Method
  const activeMethod: ShippingMethodQuoteItem | undefined = quoteResponse?.available_methods.find(
    (m) => m.code === selectedMethodCode
  ) || quoteResponse?.available_methods[0];

  const authoritativeShippingFee = activeMethod
    ? Number(activeMethod.final_fee)
    : (subtotal >= storeSettings.free_shipping_threshold ? 0 : storeSettings.delivery_fee);

  const discountAmount = appliedPromo ? appliedPromo.discount_amount : 0;
  const authoritativeGrandTotal = Math.max(0, subtotal - discountAmount + authoritativeShippingFee);

  // Apply Promo Code
  const handleApplyPromo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!promoInput.trim()) return;
    setPromoLoading(true);
    setPromoError(null);
    try {
      const res = await discountsApi.validatePromoCode(promoInput, subtotal);
      if (!res.valid) {
        setPromoError(res.message || "Invalid coupon code.");
        setAppliedPromo(null);
      } else {
        setAppliedPromo({
          code: res.code,
          discount_amount: res.discount_amount,
          discount_type: res.discount_type,
          discount_value: res.discount_value,
          message: res.message || `Code ${res.code} applied!`,
        });
        setPromoError(null);
        setPromoInput("");
      }
    } catch (err: any) {
      setPromoError(err.message || "Failed to validate coupon code.");
    } finally {
      setPromoLoading(false);
    }
  };

  const handleRemovePromo = () => {
    setAppliedPromo(null);
    setPromoError(null);
  };

  // Handle Checkout Submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanPhone = formData.phone.replace(/[\s\-\(\)]/g, "");
    if (!/^(\+?92|0)?3[0-9]{9}$/.test(cleanPhone)) {
      setErrorMessage("Please enter a valid Pakistani mobile number (e.g. 03001234567 or +923001234567).");
      return;
    }

    if (items.length === 0) {
      setErrorMessage("Your shopping bag is empty.");
      return;
    }

    setIsSubmitting(true);
    const idempotencyKey = `idemp_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    try {
      const checkoutPayload: CheckoutRequest = {
        customer_name: formData.fullName,
        customer_email: formData.email,
        customer_phone: cleanPhone,
        shipping_address: {
          full_name: formData.fullName,
          phone: cleanPhone,
          address_line_1: formData.addressLine1,
          address_line_2: formData.addressLine2 || undefined,
          city: formData.city,
          postal_code: formData.postalCode || undefined,
          country_code: "PK",
        },
        shipping_method_code: activeMethod?.code || "standard",
        payment_method: paymentMethod,
        customer_note: formData.customerNote || undefined,
        coupon_code: appliedPromo?.code || undefined,
        idempotency_key: idempotencyKey,
      };

      const order = await ordersApi.checkout(checkoutPayload, idempotencyKey);

      await clearCart();
      await refreshCart();
      router.push(`/checkout/success?order=${order.order_number}`);
    } catch (err: any) {
      console.error("Checkout failed:", err);
      setErrorMessage(
        err.message ||
        "An unexpected error occurred while processing your checkout. Your cart has been preserved. Please verify details and retry."
      );
      setIsSubmitting(false);
    }
  };

  const { cod, card, bank_transfer } = storeSettings.payment_methods;

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Error Alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-crimson/10 border border-crimson/30 text-crimson text-xs flex items-start gap-2.5 animate-in fade-in">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-semibold">Checkout Issue</p>
            <p className="font-light">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* 1. Contact Details */}
      <div className="p-6 sm:p-8 rounded-card bg-ivory-light border border-hairline shadow-subtle space-y-4">
        <div className="flex items-center justify-between border-b border-hairline pb-3">
          <h3 className="font-serif text-lg sm:text-xl font-medium text-obsidian tracking-tight">
            1. Client & Contact Details
          </h3>
          {isAuthenticated && (
            <span className="text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full font-medium">
              Verified Client
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
              Full Name
            </label>
            <input
              type="text"
              required
              value={formData.fullName}
              onChange={(e) => setFormData((p) => ({ ...p, fullName: e.target.value }))}
              placeholder="e.g. Amina Khan"
              className="w-full px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
              Mobile Contact
            </label>
            <input
              type="tel"
              required
              value={formData.phone}
              onChange={(e) => setFormData((p) => ({ ...p, phone: e.target.value }))}
              placeholder="0300 1234567"
              className="w-full px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne font-mono"
            />
          </div>

          <div className="sm:col-span-2 space-y-1">
            <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
              Email Address for Order Tracking & Invoicing
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
              placeholder="amina.khan@example.com"
              className="w-full px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
            />
          </div>
        </div>
      </div>

      {/* 2. Delivery Address */}
      <div className="p-6 sm:p-8 rounded-card bg-ivory-light border border-hairline shadow-subtle space-y-4">
        <div className="border-b border-hairline pb-3">
          <h3 className="font-serif text-lg sm:text-xl font-medium text-obsidian tracking-tight">
            2. Delivery Destination
          </h3>
          <p className="text-xs text-obsidian-500 font-light mt-0.5">
            Complimentary doorstep shipping nationwide across Pakistan.
          </p>
        </div>

        {savedAddresses.length > 0 && (
          <div className="space-y-1.5 pb-2">
            <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
              Select Saved Address
            </label>
            <select
              value={selectedSavedAddressId}
              onChange={(e) => handleSelectSavedAddress(e.target.value)}
              className="w-full px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
            >
              <option value="new">+ Enter New Delivery Address</option>
              {savedAddresses.map((addr) => (
                <option key={addr.id} value={addr.id}>
                  {addr.full_name} — {addr.street_address}, {addr.city} {addr.is_default ? "(Default)" : ""}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
              Street Address & House / Flat #
            </label>
            <input
              type="text"
              required
              value={formData.addressLine1}
              onChange={(e) => setFormData((p) => ({ ...p, addressLine1: e.target.value }))}
              placeholder="e.g. House 42, Street 7, Sector F-8/3"
              className="w-full px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                City
              </label>
              <select
                value={formData.city}
                onChange={(e) => setFormData((p) => ({ ...p, city: e.target.value }))}
                className="w-full px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
              >
                {CITIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                Postal Code (Optional)
              </label>
              <input
                type="text"
                value={formData.postalCode}
                onChange={(e) => setFormData((p) => ({ ...p, postalCode: e.target.value }))}
                placeholder="54000"
                className="w-full px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne font-mono"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
              Delivery Instructions for Rider (Optional)
            </label>
            <input
              type="text"
              value={formData.customerNote}
              onChange={(e) => setFormData((p) => ({ ...p, customerNote: e.target.value }))}
              placeholder="e.g. Ring bell or leave with gatekeeper"
              className="w-full px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
            />
          </div>
        </div>
      </div>

      {/* 3. Promo & Discount Codes */}
      <div className="p-6 sm:p-8 rounded-card bg-ivory-light border border-hairline shadow-subtle space-y-4">
        <div className="flex items-center justify-between border-b border-hairline pb-3">
          <div className="flex items-center gap-2">
            <Tag className="w-4 h-4 text-champagne-dark" />
            <h3 className="font-serif text-lg sm:text-xl font-medium text-obsidian tracking-tight">
              3. Promotion Code & Vouchers
            </h3>
          </div>
          <span className="text-xs text-obsidian-500 font-light">Optional</span>
        </div>

        {appliedPromo ? (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-700" />
              <div>
                <p className="text-xs font-semibold text-emerald-900 font-mono">
                  CODE: {appliedPromo.code}
                </p>
                <p className="text-[11px] text-emerald-700">{appliedPromo.message}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono font-bold text-xs text-emerald-800">
                - {formatPKR(appliedPromo.discount_amount)}
              </span>
              <button
                type="button"
                onClick={handleRemovePromo}
                className="text-emerald-700 hover:text-emerald-900 p-1"
                title="Remove discount"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                type="text"
                value={promoInput}
                onChange={(e) => setPromoInput(e.target.value.toUpperCase())}
                placeholder="Enter promo code (e.g. WELCOME10)"
                className="flex-1 px-3.5 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne font-mono uppercase"
              />
              <button
                type="button"
                onClick={handleApplyPromo}
                disabled={promoLoading || !promoInput.trim()}
                className="px-5 py-2.5 rounded-lg bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800 transition-colors disabled:opacity-50 flex items-center gap-1.5 shrink-0"
              >
                {promoLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Apply"}
              </button>
            </div>
            {promoError && (
              <p className="text-xs text-crimson flex items-center gap-1 mt-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{promoError}</span>
              </p>
            )}
          </div>
        )}
      </div>

      {/* 4. Delivery Method & Courier Tariff */}
      <div className="p-6 sm:p-8 rounded-card bg-ivory-light border border-hairline shadow-subtle space-y-4">
        <div className="flex items-center justify-between border-b border-hairline pb-3">
          <h3 className="font-serif text-lg sm:text-xl font-medium text-obsidian tracking-tight">
            4. Delivery Tariff
          </h3>
          <span className="text-xs text-obsidian-500 font-light">
            Server Quote: <strong>{formData.city}</strong>
          </span>
        </div>

        {quoteLoading ? (
          <div className="py-6 text-center text-xs text-obsidian-500 flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-champagne border-t-transparent rounded-full animate-spin" />
            <span>Calculating dynamic tariff...</span>
          </div>
        ) : quoteResponse && quoteResponse.available_methods.length > 0 ? (
          <div className="space-y-3">
            {quoteResponse.available_methods.map((method) => {
              const isSelected = selectedMethodCode === method.code;
              return (
                <label
                  key={method.code}
                  className={`flex items-start justify-between p-4 rounded-xl border cursor-pointer transition-colors ${
                    isSelected
                      ? "border-champagne-dark bg-champagne-light/30 ring-1 ring-champagne-dark"
                      : "border-hairline bg-ivory hover:bg-ivory-sand"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="radio"
                      name="shipping_method"
                      value={method.code}
                      checked={isSelected}
                      onChange={() => setSelectedMethodCode(method.code)}
                      className="mt-1 text-champagne-dark"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-obsidian">{method.name}</span>
                        {method.is_free && (
                          <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                            Free Shipping
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-obsidian-500 mt-0.5 font-light">
                        Estimated transit: {method.estimated_days_min}–{method.estimated_days_max} business days
                      </p>
                    </div>
                  </div>
                  <span className="font-mono font-semibold text-xs text-obsidian">
                    {method.is_free ? "FREE" : formatPKR(Number(method.final_fee))}
                  </span>
                </label>
              );
            })}
          </div>
        ) : (
          <div className="p-4 rounded-xl border border-hairline bg-ivory text-xs text-obsidian-600 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Truck className="w-4 h-4 text-champagne-dark" />
              <span>Standard Nationwide Courier (2–4 Business Days)</span>
            </div>
            <span className="font-mono font-medium">
              {subtotal >= storeSettings.free_shipping_threshold ? "FREE" : formatPKR(storeSettings.delivery_fee)}
            </span>
          </div>
        )}
      </div>

      {/* 5. Dynamic Payment Method Selection */}
      <div className="p-6 sm:p-8 rounded-card bg-ivory-light border border-hairline shadow-subtle space-y-4">
        <div className="border-b border-hairline pb-3">
          <h3 className="font-serif text-lg sm:text-xl font-medium text-obsidian tracking-tight">
            5. Payment Method
          </h3>
          <p className="text-xs text-obsidian-500 font-light mt-0.5">
            Select an authorized payment option configured for your delivery.
          </p>
        </div>

        <div className="space-y-3">
          {/* Option A: Cash on Delivery (If Enabled by Admin) */}
          {cod.enabled && (
            <label
              className={`flex items-start justify-between p-4 rounded-xl border cursor-pointer transition-colors ${
                paymentMethod === "cod"
                  ? "border-champagne-dark bg-champagne-light/30 ring-1 ring-champagne-dark"
                  : "border-hairline bg-ivory hover:bg-ivory-sand"
              }`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="radio"
                  name="payment_method"
                  value="cod"
                  checked={paymentMethod === "cod"}
                  onChange={() => setPaymentMethod("cod")}
                  className="mt-1 text-champagne-dark"
                />
                <div>
                  <div className="flex items-center gap-2">
                    <Banknote className="w-4 h-4 text-champagne-dark" />
                    <span className="font-semibold text-xs text-obsidian">{cod.title}</span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark">
                      Recommended
                    </span>
                  </div>
                  <p className="text-xs text-obsidian-600 font-light mt-1">
                    {cod.description}
                  </p>
                </div>
              </div>
            </label>
          )}

          {/* Option B: Credit / Debit Card (If Enabled by Admin) */}
          {card.enabled && (
            <label
              className={`flex items-start justify-between p-4 rounded-xl border cursor-pointer transition-colors ${
                paymentMethod === "card"
                  ? "border-champagne-dark bg-champagne-light/30 ring-1 ring-champagne-dark"
                  : "border-hairline bg-ivory hover:bg-ivory-sand"
              }`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="radio"
                  name="payment_method"
                  value="card"
                  checked={paymentMethod === "card"}
                  onChange={() => setPaymentMethod("card")}
                  className="mt-1 text-champagne-dark"
                />
                <div>
                  <div className="flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-champagne-dark" />
                    <span className="font-semibold text-xs text-obsidian">{card.title}</span>
                  </div>
                  <p className="text-xs text-obsidian-600 font-light mt-1">
                    {card.description}
                  </p>
                </div>
              </div>
            </label>
          )}

          {/* Option C: Direct Bank Transfer / IBFT (If Enabled by Admin) */}
          {bank_transfer.enabled && (
            <label
              className={`flex items-start justify-between p-4 rounded-xl border cursor-pointer transition-colors ${
                paymentMethod === "bank_transfer"
                  ? "border-champagne-dark bg-champagne-light/30 ring-1 ring-champagne-dark"
                  : "border-hairline bg-ivory hover:bg-ivory-sand"
              }`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="radio"
                  name="payment_method"
                  value="bank_transfer"
                  checked={paymentMethod === "bank_transfer"}
                  onChange={() => setPaymentMethod("bank_transfer")}
                  className="mt-1 text-champagne-dark"
                />
                <div>
                  <div className="flex items-center gap-2">
                    <Building className="w-4 h-4 text-champagne-dark" />
                    <span className="font-semibold text-xs text-obsidian">{bank_transfer.title}</span>
                  </div>
                  <p className="text-xs text-obsidian-600 font-light mt-1">
                    {bank_transfer.description}
                  </p>
                  {bank_transfer.details && (
                    <div className="mt-2 p-2.5 rounded bg-ivory-sand/60 font-mono text-[11px] text-obsidian">
                      {bank_transfer.details}
                    </div>
                  )}
                </div>
              </div>
            </label>
          )}
        </div>
      </div>

      {/* 6. Order Summary & Confirm */}
      <div className="space-y-4">
        <div className="p-4 rounded-xl bg-ivory-sand/40 border border-hairline space-y-2 text-xs">
          <div className="flex justify-between text-obsidian-600">
            <span>Subtotal ({items.length} pieces):</span>
            <span className="font-mono">{formatPKR(subtotal)}</span>
          </div>
          {appliedPromo && (
            <div className="flex justify-between text-emerald-700 font-medium">
              <span>Promo Discount ({appliedPromo.code}):</span>
              <span className="font-mono">- {formatPKR(appliedPromo.discount_amount)}</span>
            </div>
          )}
          <div className="flex justify-between text-obsidian-600">
            <span>Delivery Fee:</span>
            <span className="font-mono">
              {authoritativeShippingFee === 0 ? "FREE" : formatPKR(authoritativeShippingFee)}
            </span>
          </div>
          <div className="pt-2 border-t border-hairline flex justify-between font-serif text-base font-semibold text-obsidian">
            <span>Payable Amount:</span>
            <span className="font-mono text-champagne-dark">{formatPKR(authoritativeGrandTotal)}</span>
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || items.length === 0}
          className="w-full py-4 px-6 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 disabled:opacity-50 transition-colors flex items-center justify-center gap-2 shadow-subtle"
        >
          {isSubmitting ? (
            <>
              <div className="w-4 h-4 border-2 border-champagne border-t-transparent rounded-full animate-spin" />
              <span>Placing Order With Verified Backend...</span>
            </>
          ) : (
            <span>
              Confirm Order • {formatPKR(authoritativeGrandTotal)}
            </span>
          )}
        </button>

        <p className="text-[11px] text-obsidian-500 text-center font-light flex items-center justify-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-champagne-dark" />
          <span>Complimentary Doorstep Inspection & Exchanges Across Pakistan</span>
        </p>
      </div>
    </form>
  );
}
