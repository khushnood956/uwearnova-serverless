"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  User as UserIcon,
  Package,
  MapPin,
  Heart,
  RotateCcw,
  Shield,
  LogOut,
  ChevronRight,
  Plus,
  Trash2,
  CheckCircle,
  Clock,
  Truck,
  AlertCircle,
  ExternalLink,
  Edit2,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useWishlist } from "@/context/WishlistContext";
import { useCart } from "@/context/CartContext";
import {
  customerApi,
  CustomerProfile,
  CustomerAddress,
  CustomerOrderDetail,
  CustomerReturnDetail,
  CustomerSecurityOverview,
} from "@/lib/api/customer";
import { formatPKR } from "@/lib/brand";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";

type TabKey = "overview" | "orders" | "profile" | "addresses" | "returns" | "wishlist" | "security";

function AccountContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as TabKey) || "overview";

  const { user, isAuthenticated, isLoading: authLoading, logout, openAuthModal } = useAuth();
  const { wishlistIds, removeFromWishlist } = useWishlist();
  const { addItem } = useCart();

  const [activeTab, setActiveTab] = React.useState<TabKey>(initialTab);
  const [profile, setProfile] = React.useState<CustomerProfile | null>(null);
  const [addresses, setAddresses] = React.useState<CustomerAddress[]>([]);
  const [orders, setOrders] = React.useState<CustomerOrderDetail[]>([]);
  const [returns, setReturns] = React.useState<CustomerReturnDetail[]>([]);
  const [security, setSecurity] = React.useState<CustomerSecurityOverview | null>(null);
  const [selectedOrder, setSelectedOrder] = React.useState<CustomerOrderDetail | null>(null);

  const [loading, setLoading] = React.useState(false);
  const [statusMessage, setStatusMessage] = React.useState<{ type: "success" | "error"; text: string } | null>(null);

  // Forms state
  const [editProfileForm, setEditProfileForm] = React.useState({ first_name: "", last_name: "", phone: "" });
  const [addressModalOpen, setAddressModalOpen] = React.useState(false);
  const [editingAddressId, setEditingAddressId] = React.useState<number | null>(null);
  const [addressForm, setAddressForm] = React.useState({
    label: "Home",
    full_name: "",
    phone: "",
    street_address: "",
    apartment_suite: "",
    city: "Lahore",
    province: "Punjab",
    postal_code: "",
    delivery_instructions: "",
    is_default: false,
  });

  const [returnModalOpen, setReturnModalOpen] = React.useState(false);
  const [returnForm, setReturnForm] = React.useState({
    order_number: "",
    request_type: "return" as "return" | "exchange",
    reason: "Size too large",
    item_id: 0,
    quantity: 1,
  });

  const [passwordForm, setPasswordForm] = React.useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setStatusMessage({ type, text });
    setTimeout(() => setStatusMessage(null), 4000);
  };

  // Load account data when authenticated
  const loadData = React.useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      const [profData, addrData, ordData, retData, secData] = await Promise.allSettled([
        customerApi.getProfile(),
        customerApi.getAddresses(),
        customerApi.getOrders({ limit: 20 }),
        customerApi.getReturns({ page_size: 20 }),
        customerApi.getSecurityOverview(),
      ]);

      if (profData.status === "fulfilled") {
        setProfile(profData.value);
        setEditProfileForm({
          first_name: profData.value.first_name || "",
          last_name: profData.value.last_name || "",
          phone: profData.value.phone || "",
        });
      }
      if (addrData.status === "fulfilled") {
        setAddresses(addrData.value.items || []);
      }
      if (ordData.status === "fulfilled") {
        setOrders(ordData.value.items || []);
      }
      if (retData.status === "fulfilled") {
        setReturns(retData.value.items || []);
      }
      if (secData.status === "fulfilled") {
        setSecurity(secData.value);
      }
    } catch (err) {
      console.warn("Failed to load customer details:", err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  if (authLoading) {
    return (
      <main className="flex-1 py-20 bg-ivory text-center">
        <div className="w-8 h-8 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-obsidian-500 font-medium tracking-wide">Loading your account...</p>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="flex-1 py-20 bg-ivory">
        <div className="container-site max-w-md mx-auto text-center space-y-6">
          <div className="w-16 h-16 rounded-full bg-ivory-sand flex items-center justify-center mx-auto text-obsidian border border-hairline">
            <UserIcon className="w-7 h-7" />
          </div>
          <div className="space-y-2">
            <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight">Customer Portal</h1>
            <p className="text-sm text-obsidian-600 font-light leading-relaxed">
              Please sign in to access your order history, delivery addresses, and account settings.
            </p>
          </div>
          <button
            type="button"
            onClick={() => openAuthModal("signin")}
            className="w-full py-3.5 px-6 rounded-button bg-obsidian text-ivory text-xs font-semibold tracking-wider uppercase hover:bg-obsidian-800 transition-colors"
          >
            Sign In to Your Account
          </button>
        </div>
      </main>
    );
  }

  // Handle Profile Update
  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const updated = await customerApi.updateProfile(editProfileForm);
      setProfile(updated);
      showNotification("Profile details updated successfully.");
    } catch (err: any) {
      showNotification(err.message || "Failed to update profile", "error");
    }
  };

  // Handle Address Save
  const handleAddressSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingAddressId) {
        await customerApi.updateAddress(editingAddressId, addressForm);
        showNotification("Address updated successfully.");
      } else {
        await customerApi.createAddress(addressForm);
        showNotification("Address added to your address book.");
      }
      setAddressModalOpen(false);
      setEditingAddressId(null);
      const res = await customerApi.getAddresses();
      setAddresses(res.items || []);
    } catch (err: any) {
      showNotification(err.message || "Failed to save address", "error");
    }
  };

  // Handle Delete Address
  const handleDeleteAddress = async (id: number) => {
    if (!confirm("Are you sure you want to remove this delivery address?")) return;
    try {
      await customerApi.deleteAddress(id);
      setAddresses((prev) => prev.filter((a) => a.id !== id));
      showNotification("Address removed.");
    } catch (err: any) {
      showNotification(err.message || "Failed to remove address", "error");
    }
  };

  // Handle Set Default Address
  const handleSetDefaultAddress = async (id: number) => {
    try {
      await customerApi.setDefaultAddress(id);
      const res = await customerApi.getAddresses();
      setAddresses(res.items || []);
      showNotification("Default delivery address updated.");
    } catch (err: any) {
      showNotification(err.message || "Failed to set default address", "error");
    }
  };

  // Handle Change Password
  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      showNotification("New passwords do not match.", "error");
      return;
    }
    if (passwordForm.new_password.length < 8) {
      showNotification("Password must be at least 8 characters.", "error");
      return;
    }
    try {
      await customerApi.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
      showNotification("Password changed successfully. Please log in again if required.");
    } catch (err: any) {
      showNotification(err.message || "Failed to change password", "error");
    }
  };

  // Handle Submit Return Request
  const handleReturnSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await customerApi.submitReturn({
        order_number: returnForm.order_number,
        request_type: returnForm.request_type,
        reason: returnForm.reason,
        items: [{ order_item_id: returnForm.item_id || 1, quantity: returnForm.quantity, reason: returnForm.reason }],
      });
      setReturnModalOpen(false);
      showNotification("Return/Exchange request lodged. Our concierge team will review it.");
      const res = await customerApi.getReturns({ page_size: 20 });
      setReturns(res.items || []);
    } catch (err: any) {
      showNotification(err.message || "Failed to submit request", "error");
    }
  };

  return (
    <main className="flex-1 pb-20 bg-ivory">
      {/* Toast Notification */}
      {statusMessage && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-card text-xs font-medium flex items-center gap-2 border animate-in slide-in-from-bottom-2 ${
            statusMessage.type === "success"
              ? "bg-emerald-950 text-emerald-200 border-emerald-800"
              : "bg-crimson text-ivory border-crimson/80"
          }`}
        >
          {statusMessage.type === "success" ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{statusMessage.text}</span>
        </div>
      )}

      <div className="container-site pt-6 pb-12">
        <Breadcrumbs items={[{ label: "My Account" }]} />

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline mt-4">
          <div>
            <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
              Customer Sanctuary
            </span>
            <h1 className="font-serif text-3xl sm:text-4xl font-medium text-obsidian tracking-tight mt-1">
              Welcome, {profile?.first_name || user?.first_name || "Valued Client"}
            </h1>
            <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
              Manage your orders, saved addresses, doorstep exchanges, and personal preferences.
            </p>
          </div>

          <button
            type="button"
            onClick={logout}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-button text-xs font-medium text-crimson hover:bg-crimson/5 border border-crimson/20 transition-colors self-start sm:self-auto"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-8 items-start">
          {/* Navigation Sidebar */}
          <aside className="lg:col-span-3 bg-ivory-light rounded-xl border border-hairline p-3 shadow-subtle space-y-1">
            {[
              { key: "overview", label: "Account Overview", icon: Sparkles },
              { key: "orders", label: "Order History", icon: Package, badge: orders.length },
              { key: "addresses", label: "Address Book", icon: MapPin, badge: addresses.length },
              { key: "returns", label: "Returns & Exchanges", icon: RotateCcw, badge: returns.length },
              { key: "wishlist", label: "Saved Wishlist", icon: Heart, badge: wishlistIds.length },
              { key: "profile", label: "Profile & Preferences", icon: UserIcon },
              { key: "security", label: "Security & Logins", icon: Shield },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key as TabKey)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-obsidian text-ivory shadow-subtle"
                      : "text-obsidian-700 hover:text-obsidian hover:bg-ivory-sand"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{tab.label}</span>
                  </div>
                  {tab.badge !== undefined && tab.badge > 0 && (
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                        isActive ? "bg-champagne text-obsidian" : "bg-ivory-sand text-obsidian-700"
                      }`}
                    >
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </aside>

          {/* Main Tab Content */}
          <section className="lg:col-span-9 bg-ivory-light rounded-2xl border border-hairline p-6 sm:p-8 shadow-card min-h-[500px]">
            {/* 1. OVERVIEW TAB */}
            {activeTab === "overview" && (
              <div className="space-y-8">
                <div>
                  <h2 className="font-serif text-2xl font-medium text-obsidian">Account Overview</h2>
                  <p className="text-xs text-obsidian-500 font-light mt-1">
                    Snapshot of your recent boutique activity and active orders.
                  </p>
                </div>

                {/* Metric Summary Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="p-4 rounded-xl bg-ivory border border-hairline shadow-subtle">
                    <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Total Orders</span>
                    <p className="font-serif text-2xl font-medium text-obsidian mt-1">{orders.length}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-ivory border border-hairline shadow-subtle">
                    <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Wishlisted Pieces</span>
                    <p className="font-serif text-2xl font-medium text-obsidian mt-1">{wishlistIds.length}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-ivory border border-hairline shadow-subtle">
                    <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Saved Addresses</span>
                    <p className="font-serif text-2xl font-medium text-obsidian mt-1">{addresses.length}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-ivory border border-hairline shadow-subtle">
                    <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Active Returns</span>
                    <p className="font-serif text-2xl font-medium text-obsidian mt-1">
                      {returns.filter((r) => r.status !== "completed" && r.status !== "rejected").length}
                    </p>
                  </div>
                </div>

                {/* Recent Orders Section */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-serif text-lg font-medium text-obsidian">Recent Orders</h3>
                    {orders.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setActiveTab("orders")}
                        className="text-xs text-champagne-dark font-medium hover:underline flex items-center gap-1"
                      >
                        <span>View All ({orders.length})</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  {orders.length === 0 ? (
                    <div className="py-12 text-center rounded-xl border border-dashed border-hairline p-6">
                      <Package className="w-8 h-8 text-obsidian-300 mx-auto mb-2" />
                      <p className="text-sm font-medium text-obsidian">No orders placed yet</p>
                      <p className="text-xs text-obsidian-500 mt-1 max-w-sm mx-auto">
                        Your completed purchases and dispatch tracking updates will appear here.
                      </p>
                      <Link
                        href="/collections/all"
                        className="mt-4 inline-block px-5 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
                      >
                        Explore Collections
                      </Link>
                    </div>
                  ) : (
                    <div className="divide-y divide-hairline border border-hairline rounded-xl overflow-hidden bg-ivory">
                      {orders.slice(0, 3).map((ord) => (
                        <div key={ord.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-serif text-sm font-semibold text-obsidian">{ord.order_number}</span>
                              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark border border-champagne-dark/20">
                                {ord.status}
                              </span>
                            </div>
                            <p className="text-xs text-obsidian-500 mt-1">
                              {new Date(ord.created_at).toLocaleDateString()} • {ord.items.length} item(s) •{" "}
                              <strong className="text-obsidian font-semibold">{formatPKR(Number(ord.grand_total))}</strong>
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedOrder(ord);
                              setActiveTab("orders");
                            }}
                            className="text-xs text-obsidian hover:text-champagne-dark font-medium border border-hairline px-3 py-1.5 rounded-button bg-ivory-sand/40 hover:bg-ivory-sand transition-colors self-start sm:self-auto"
                          >
                            View Details
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Shortcuts */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-hairline">
                  <button
                    type="button"
                    onClick={() => setActiveTab("addresses")}
                    className="p-4 rounded-xl border border-hairline bg-ivory hover:bg-ivory-sand/50 transition-colors text-left"
                  >
                    <MapPin className="w-5 h-5 text-champagne-dark mb-2" />
                    <p className="text-xs font-semibold text-obsidian">Manage Addresses</p>
                    <p className="text-[11px] text-obsidian-500 mt-0.5">Add or update your delivery destinations</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("returns")}
                    className="p-4 rounded-xl border border-hairline bg-ivory hover:bg-ivory-sand/50 transition-colors text-left"
                  >
                    <RotateCcw className="w-5 h-5 text-champagne-dark mb-2" />
                    <p className="text-xs font-semibold text-obsidian">7-Day Exchanges</p>
                    <p className="text-[11px] text-obsidian-500 mt-0.5">Initiate complimentary doorstep exchange</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("security")}
                    className="p-4 rounded-xl border border-hairline bg-ivory hover:bg-ivory-sand/50 transition-colors text-left"
                  >
                    <Shield className="w-5 h-5 text-champagne-dark mb-2" />
                    <p className="text-xs font-semibold text-obsidian">Security & Password</p>
                    <p className="text-[11px] text-obsidian-500 mt-0.5">Update credentials and active sessions</p>
                  </button>
                </div>
              </div>
            )}

            {/* 2. ORDERS TAB */}
            {activeTab === "orders" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-hairline">
                  <div>
                    <h2 className="font-serif text-2xl font-medium text-obsidian">Order History</h2>
                    <p className="text-xs text-obsidian-500 font-light mt-1">
                      Track current dispatch consignments and review past pieces.
                    </p>
                  </div>
                  {selectedOrder && (
                    <button
                      type="button"
                      onClick={() => setSelectedOrder(null)}
                      className="text-xs text-obsidian-600 hover:text-obsidian underline"
                    >
                      ← Back to All Orders
                    </button>
                  )}
                </div>

                {selectedOrder ? (
                  /* Order Detail & Timeline View */
                  <div className="space-y-6 animate-in fade-in duration-200">
                    <div className="p-4 rounded-xl bg-ivory border border-hairline flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Order Reference</span>
                        <h3 className="font-serif text-xl font-medium text-obsidian mt-0.5">{selectedOrder.order_number}</h3>
                        <p className="text-xs text-obsidian-500 mt-0.5">
                          Placed on {new Date(selectedOrder.created_at).toLocaleDateString()} • Payment:{" "}
                          <span className="capitalize font-medium text-obsidian">{selectedOrder.payment_method}</span> ({selectedOrder.payment_status})
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] uppercase tracking-wider text-obsidian-400 font-semibold">Grand Total</span>
                        <p className="font-serif text-2xl font-semibold text-obsidian">
                          {formatPKR(Number(selectedOrder.grand_total))}
                        </p>
                      </div>
                    </div>

                    {/* Timeline */}
                    {selectedOrder.timeline && selectedOrder.timeline.length > 0 && (
                      <div className="p-4 rounded-xl bg-ivory border border-hairline space-y-3">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-obsidian">Order Status Timeline</h4>
                        <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[1.5px] before:bg-hairline">
                          {selectedOrder.timeline.map((step, idx) => (
                            <div key={idx} className="relative">
                              <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-champagne-dark ring-4 ring-ivory" />
                              <div className="text-xs">
                                <span className="font-semibold capitalize text-obsidian">{step.status}</span>
                                <span className="text-obsidian-400 ml-2 text-[11px]">{new Date(step.created_at).toLocaleString()}</span>
                                {step.notes && <p className="text-obsidian-600 mt-0.5 font-light">{step.notes}</p>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Shipments / Tracking */}
                    {selectedOrder.shipments && selectedOrder.shipments.length > 0 && (
                      <div className="p-4 rounded-xl bg-ivory-sand/40 border border-hairline space-y-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-obsidian flex items-center gap-1.5">
                          <Truck className="w-4 h-4 text-champagne-dark" />
                          <span>Shipment & Tracking Consignment</span>
                        </h4>
                        {selectedOrder.shipments.map((ship) => (
                          <div key={ship.id} className="text-xs text-obsidian-700 flex items-center justify-between pt-1">
                            <div>
                              <span>Courier: <strong>{ship.courier_name}</strong></span> • Tracking: <span className="font-mono">{ship.tracking_number}</span>
                            </div>
                            <span className="capitalize font-medium text-champagne-dark">{ship.status}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Ordered Items */}
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-obsidian">Pieces in this order</h4>
                      <div className="divide-y divide-hairline border border-hairline rounded-xl overflow-hidden bg-ivory">
                        {selectedOrder.items.map((item) => (
                          <div key={item.id} className="p-3.5 flex items-center justify-between text-xs">
                            <div className="space-y-0.5">
                              <Link href={`/product/${item.product_slug}`} className="font-medium text-obsidian hover:underline">
                                {item.product_name}
                              </Link>
                              <p className="text-obsidian-500 text-[11px]">
                                Size: {item.size} • Color: {item.color_name} • Qty: {item.quantity}
                              </p>
                            </div>
                            <span className="font-medium text-obsidian">{formatPKR(Number(item.line_total))}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : orders.length === 0 ? (
                  <div className="py-12 text-center rounded-xl border border-dashed border-hairline p-6">
                    <Package className="w-8 h-8 text-obsidian-300 mx-auto mb-2" />
                    <p className="text-sm font-medium text-obsidian">No orders on record</p>
                    <p className="text-xs text-obsidian-500 mt-1">You haven&apos;t placed any orders yet.</p>
                  </div>
                ) : (
                  <div className="divide-y divide-hairline border border-hairline rounded-xl overflow-hidden bg-ivory">
                    {orders.map((ord) => (
                      <div key={ord.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-serif text-sm font-semibold text-obsidian">{ord.order_number}</span>
                            <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark border border-champagne-dark/20">
                              {ord.status}
                            </span>
                          </div>
                          <p className="text-xs text-obsidian-500 mt-1">
                            {new Date(ord.created_at).toLocaleDateString()} • {ord.items.length} piece(s) • Total:{" "}
                            <strong className="text-obsidian font-semibold">{formatPKR(Number(ord.grand_total))}</strong>
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setSelectedOrder(ord)}
                          className="text-xs text-obsidian hover:text-champagne-dark font-medium border border-hairline px-3 py-1.5 rounded-button bg-ivory-sand/40 hover:bg-ivory-sand transition-colors self-start sm:self-auto"
                        >
                          View Details & Tracking
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 3. PROFILE TAB */}
            {activeTab === "profile" && (
              <div className="space-y-6">
                <div>
                  <h2 className="font-serif text-2xl font-medium text-obsidian">Personal Profile</h2>
                  <p className="text-xs text-obsidian-500 font-light mt-1">
                    Manage your identity, contact details, and marketing notifications.
                  </p>
                </div>

                <form onSubmit={handleProfileSubmit} className="space-y-4 max-w-lg">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">First Name</label>
                      <input
                        type="text"
                        value={editProfileForm.first_name}
                        onChange={(e) => setEditProfileForm((p) => ({ ...p, first_name: e.target.value }))}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:outline-none focus:ring-1 focus:ring-champagne"
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">Last Name</label>
                      <input
                        type="text"
                        value={editProfileForm.last_name}
                        onChange={(e) => setEditProfileForm((p) => ({ ...p, last_name: e.target.value }))}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:outline-none focus:ring-1 focus:ring-champagne"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">Email (Account ID)</label>
                    <input
                      type="email"
                      value={profile?.email || user?.email || ""}
                      disabled
                      className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-sand/60 text-obsidian-500 cursor-not-allowed"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">Mobile Phone (for Courier SMS)</label>
                    <input
                      type="tel"
                      value={editProfileForm.phone}
                      onChange={(e) => setEditProfileForm((p) => ({ ...p, phone: e.target.value }))}
                      placeholder="+92 319 1772713"
                      className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:outline-none focus:ring-1 focus:ring-champagne"
                    />
                  </div>

                  <button
                    type="submit"
                    className="px-6 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
                  >
                    Save Profile Changes
                  </button>
                </form>
              </div>
            )}

            {/* 4. ADDRESSES TAB */}
            {activeTab === "addresses" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-hairline">
                  <div>
                    <h2 className="font-serif text-2xl font-medium text-obsidian">Address Book</h2>
                    <p className="text-xs text-obsidian-500 font-light mt-1">
                      Save shipping destinations for seamless nationwide delivery.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setEditingAddressId(null);
                      setAddressForm({
                        label: "Home",
                        full_name: profile ? `${profile.first_name} ${profile.last_name}`.trim() : "",
                        phone: profile?.phone || "",
                        street_address: "",
                        apartment_suite: "",
                        city: "Lahore",
                        province: "Punjab",
                        postal_code: "",
                        delivery_instructions: "",
                        is_default: addresses.length === 0,
                      });
                      setAddressModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-button bg-obsidian text-ivory text-xs font-medium hover:bg-obsidian-800 transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Address</span>
                  </button>
                </div>

                {addresses.length === 0 ? (
                  <div className="py-12 text-center rounded-xl border border-dashed border-hairline p-6">
                    <MapPin className="w-8 h-8 text-obsidian-300 mx-auto mb-2" />
                    <p className="text-sm font-medium text-obsidian">No addresses saved yet</p>
                    <p className="text-xs text-obsidian-500 mt-1">Add your shipping address for fast checkout.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {addresses.map((addr) => (
                      <div
                        key={addr.id}
                        className={`p-4 rounded-xl border bg-ivory flex flex-col justify-between transition-colors ${
                          addr.is_default ? "border-champagne-dark ring-1 ring-champagne-dark/20" : "border-hairline"
                        }`}
                      >
                        <div className="space-y-1 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold uppercase tracking-wider text-[10px] text-champagne-dark">
                              {addr.label || "Address"}
                            </span>
                            {addr.is_default && (
                              <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark">
                                Primary Default
                              </span>
                            )}
                          </div>
                          <p className="font-medium text-obsidian text-sm mt-1">{addr.full_name}</p>
                          <p className="text-obsidian-600">{addr.street_address}</p>
                          {addr.apartment_suite && <p className="text-obsidian-500">{addr.apartment_suite}</p>}
                          <p className="text-obsidian-600">
                            {addr.city}, {addr.province} {addr.postal_code}
                          </p>
                          <p className="text-obsidian-500 pt-1">Phone: {addr.phone}</p>
                        </div>

                        <div className="flex items-center justify-between pt-4 mt-3 border-t border-hairline/80 text-xs">
                          {!addr.is_default && (
                            <button
                              type="button"
                              onClick={() => handleSetDefaultAddress(addr.id)}
                              className="text-xs text-champagne-dark font-medium hover:underline"
                            >
                              Set as Default
                            </button>
                          )}
                          <div className="flex items-center gap-2 ml-auto">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingAddressId(addr.id);
                                setAddressForm({
                                  label: addr.label || "Home",
                                  full_name: addr.full_name,
                                  phone: addr.phone,
                                  street_address: addr.street_address,
                                  apartment_suite: addr.apartment_suite || "",
                                  city: addr.city,
                                  province: addr.province || "Punjab",
                                  postal_code: addr.postal_code || "",
                                  delivery_instructions: addr.delivery_instructions || "",
                                  is_default: addr.is_default,
                                });
                                setAddressModalOpen(true);
                              }}
                              className="p-1.5 text-obsidian-500 hover:text-obsidian"
                              title="Edit address"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteAddress(addr.id)}
                              className="p-1.5 text-crimson hover:text-crimson/80"
                              title="Delete address"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 5. RETURNS TAB */}
            {activeTab === "returns" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-hairline">
                  <div>
                    <h2 className="font-serif text-2xl font-medium text-obsidian">Returns & Exchanges</h2>
                    <p className="text-xs text-obsidian-500 font-light mt-1">
                      7-day door-to-door complimentary exchange and return policy.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      if (orders.length === 0) {
                        showNotification("You do not have any orders eligible for return yet.", "error");
                        return;
                      }
                      setReturnForm({
                        order_number: orders[0]?.order_number || "",
                        request_type: "exchange",
                        reason: "Size too large",
                        item_id: orders[0]?.items[0]?.id || 1,
                        quantity: 1,
                      });
                      setReturnModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-button bg-obsidian text-ivory text-xs font-medium hover:bg-obsidian-800 transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Lodge Request</span>
                  </button>
                </div>

                {returns.length === 0 ? (
                  <div className="py-12 text-center rounded-xl border border-dashed border-hairline p-6">
                    <RotateCcw className="w-8 h-8 text-obsidian-300 mx-auto mb-2" />
                    <p className="text-sm font-medium text-obsidian">No return requests on file</p>
                    <p className="text-xs text-obsidian-500 mt-1 max-w-sm mx-auto">
                      All UWEARNOVA garments are covered by our 7-day doorstep replacement policy.
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-hairline border border-hairline rounded-xl overflow-hidden bg-ivory">
                    {returns.map((ret) => (
                      <div key={ret.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-serif text-sm font-semibold text-obsidian">{ret.return_number}</span>
                            <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark">
                              {ret.request_type}
                            </span>
                            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-ivory-sand text-obsidian">
                              {ret.status}
                            </span>
                          </div>
                          <p className="text-xs text-obsidian-500 mt-1">
                            Order {ret.order_number} • Submitted {new Date(ret.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="text-xs font-medium text-obsidian capitalize">
                          Resolution: {ret.refund_status || "Pending Review"}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 6. WISHLIST TAB */}
            {activeTab === "wishlist" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-hairline">
                  <div>
                    <h2 className="font-serif text-2xl font-medium text-obsidian">Saved Pieces</h2>
                    <p className="text-xs text-obsidian-500 font-light mt-1">
                      Your curated shortlist of boutique items.
                    </p>
                  </div>
                  <Link href="/wishlist" className="text-xs text-champagne-dark font-medium hover:underline">
                    View Full Wishlist Grid →
                  </Link>
                </div>

                {wishlistIds.length === 0 ? (
                  <div className="py-12 text-center rounded-xl border border-dashed border-hairline p-6">
                    <Heart className="w-8 h-8 text-obsidian-300 mx-auto mb-2" />
                    <p className="text-sm font-medium text-obsidian">Your wishlist is currently empty</p>
                    <p className="text-xs text-obsidian-500 mt-1">Click the heart icon on any piece to save it here.</p>
                  </div>
                ) : (
                  <p className="text-xs text-obsidian-600">
                    You have <strong>{wishlistIds.length}</strong> saved piece(s) in your customer collection. Access them anytime on the wishlist page.
                  </p>
                )}
              </div>
            )}

            {/* 7. SECURITY TAB */}
            {activeTab === "security" && (
              <div className="space-y-8">
                <div>
                  <h2 className="font-serif text-2xl font-medium text-obsidian">Security & Authentication</h2>
                  <p className="text-xs text-obsidian-500 font-light mt-1">
                    Keep your account secure with robust credentials and session controls.
                  </p>
                </div>

                {/* Session Overview */}
                {security && (
                  <div className="p-4 rounded-xl bg-ivory border border-hairline space-y-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-obsidian">Session Health</h3>
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="text-obsidian-400">Active Sessions:</span>{" "}
                        <strong className="text-obsidian">{security.active_sessions_count}</strong>
                      </div>
                      <div>
                        <span className="text-obsidian-400">Email Verified:</span>{" "}
                        <strong className={security.is_verified ? "text-emerald-600" : "text-amber-600"}>
                          {security.is_verified ? "Yes" : "Pending"}
                        </strong>
                      </div>
                    </div>
                  </div>
                )}

                {/* Change Password Form */}
                <form onSubmit={handlePasswordSubmit} className="space-y-4 max-w-md">
                  <h3 className="font-serif text-lg font-medium text-obsidian">Change Password</h3>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">Current Password</label>
                    <input
                      type="password"
                      value={passwordForm.current_password}
                      onChange={(e) => setPasswordForm((p) => ({ ...p, current_password: e.target.value }))}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:outline-none focus:ring-1 focus:ring-champagne"
                      required
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">New Password</label>
                    <input
                      type="password"
                      value={passwordForm.new_password}
                      onChange={(e) => setPasswordForm((p) => ({ ...p, new_password: e.target.value }))}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:outline-none focus:ring-1 focus:ring-champagne"
                      required
                      minLength={8}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">Confirm New Password</label>
                    <input
                      type="password"
                      value={passwordForm.confirm_password}
                      onChange={(e) => setPasswordForm((p) => ({ ...p, confirm_password: e.target.value }))}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:outline-none focus:ring-1 focus:ring-champagne"
                      required
                      minLength={8}
                    />
                  </div>

                  <button
                    type="submit"
                    className="px-6 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
                  >
                    Update Password
                  </button>
                </form>
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Address Modal */}
      {addressModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-lg bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4">
            <h3 className="font-serif text-xl font-medium text-obsidian">
              {editingAddressId ? "Edit Delivery Address" : "Add Delivery Address"}
            </h3>
            <form onSubmit={handleAddressSubmit} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase">Label (Home, Office)</label>
                  <input
                    type="text"
                    value={addressForm.label}
                    onChange={(e) => setAddressForm((f) => ({ ...f, label: e.target.value }))}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase">Recipient Name</label>
                  <input
                    type="text"
                    value={addressForm.full_name}
                    onChange={(e) => setAddressForm((f) => ({ ...f, full_name: e.target.value }))}
                    required
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase">Mobile Phone</label>
                  <input
                    type="tel"
                    value={addressForm.phone}
                    onChange={(e) => setAddressForm((f) => ({ ...f, phone: e.target.value }))}
                    required
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase">City</label>
                  <select
                    value={addressForm.city}
                    onChange={(e) => setAddressForm((f) => ({ ...f, city: e.target.value }))}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                  >
                    <option value="Lahore">Lahore</option>
                    <option value="Karachi">Karachi</option>
                    <option value="Islamabad">Islamabad</option>
                    <option value="Rawalpindi">Rawalpindi</option>
                    <option value="Faisalabad">Faisalabad</option>
                    <option value="Multan">Multan</option>
                    <option value="Peshawar">Peshawar</option>
                    <option value="Quetta">Quetta</option>
                    <option value="Sialkot">Sialkot</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-obsidian uppercase">Street Address</label>
                <input
                  type="text"
                  value={addressForm.street_address}
                  onChange={(e) => setAddressForm((f) => ({ ...f, street_address: e.target.value }))}
                  required
                  placeholder="House #, Street name, Sector / Block"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-obsidian uppercase">Apartment / Suite (Optional)</label>
                <input
                  type="text"
                  value={addressForm.apartment_suite}
                  onChange={(e) => setAddressForm((f) => ({ ...f, apartment_suite: e.target.value }))}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={addressForm.is_default}
                  onChange={(e) => setAddressForm((f) => ({ ...f, is_default: e.target.checked }))}
                  className="rounded border-hairline text-champagne-dark"
                />
                <label htmlFor="is_default" className="text-xs text-obsidian">
                  Set as my primary delivery address
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setAddressModalOpen(false)}
                  className="px-4 py-2 rounded-button text-xs text-obsidian hover:bg-ivory-sand"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold"
                >
                  Save Address
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Return Request Modal */}
      {returnModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-lg bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4">
            <h3 className="font-serif text-xl font-medium text-obsidian">Request Return or Exchange</h3>
            <form onSubmit={handleReturnSubmit} className="space-y-3">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-obsidian uppercase">Order Number</label>
                <select
                  value={returnForm.order_number}
                  onChange={(e) => setReturnForm((f) => ({ ...f, order_number: e.target.value }))}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                >
                  {orders.map((o) => (
                    <option key={o.id} value={o.order_number}>
                      {o.order_number} — {new Date(o.created_at).toLocaleDateString()} ({formatPKR(Number(o.grand_total))})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase">Request Type</label>
                  <select
                    value={returnForm.request_type}
                    onChange={(e) => setReturnForm((f) => ({ ...f, request_type: e.target.value as "return" | "exchange" }))}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                  >
                    <option value="exchange">Doorstep Exchange (Swap Size/Color)</option>
                    <option value="return">Return & Refund</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase">Reason</label>
                  <select
                    value={returnForm.reason}
                    onChange={(e) => setReturnForm((f) => ({ ...f, reason: e.target.value }))}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                  >
                    <option value="Size too large">Size too large</option>
                    <option value="Size too small">Size too small</option>
                    <option value="Color or fabric preference">Color/Fabric preference</option>
                    <option value="Defect or stitching issue">Defect or stitching issue</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setReturnModalOpen(false)}
                  className="px-4 py-2 rounded-button text-xs text-obsidian hover:bg-ivory-sand"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold"
                >
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}

export default function CustomerAccountPage() {
  return (
    <React.Suspense
      fallback={
        <main className="flex-1 py-20 bg-ivory text-center">
          <div className="w-8 h-8 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-obsidian-500 font-medium tracking-wide">Loading your account...</p>
        </main>
      }
    >
      <AccountContent />
    </React.Suspense>
  );
}
