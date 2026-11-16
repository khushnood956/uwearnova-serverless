"use client";

import * as React from "react";
import Link from "next/link";
import {
  Users,
  UserPlus,
  ShieldAlert,
  ShieldCheck,
  Key,
  Copy,
  Check,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock,
  Mail,
  User,
  Phone,
  Shield,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { supabase } from "@/lib/supabase/client";

interface StaffAccount {
  id: number;
  email: string;
  phone: string | null;
  status: string;
  user_type: string;
  created_at: string;
  roles?: string[];
}

const AVAILABLE_ROLES = [
  { value: "store_admin", label: "Store Administrator (Full Admin Suite)" },
  { value: "super_admin", label: "Super Administrator (All Privileges + Accounts)" },
  { value: "order_manager", label: "Order & Fulfillment Specialist" },
  { value: "inventory_manager", label: "Inventory & Warehouse Controller" },
  { value: "catalog_manager", label: "Catalog & Product Merchandiser" },
  { value: "fulfillment_staff", label: "Dispatch & Packing Specialist" },
];

export default function AdminStaffManagementPage() {
  const { user } = useAuth();
  const isSuperAdmin = user?.email === "admin1@uwearnova.com";

  // Filter available roles based on caller authority:
  // Admin cannot create super_admin; only super_admin (admin1) can create super_admin
  const roleOptions = isSuperAdmin
    ? AVAILABLE_ROLES
    : AVAILABLE_ROLES.filter((r) => r.value !== "super_admin");
  const [accounts, setAccounts] = React.useState<StaffAccount[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [newEmail, setNewEmail] = React.useState("");
  const [newFirstName, setNewFirstName] = React.useState("");
  const [newLastName, setNewLastName] = React.useState("");
  const [newPhone, setNewPhone] = React.useState("");
  const [newRole, setNewRole] = React.useState("store_admin");
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Temporary credentials popup
  const [createdCredentials, setCreatedCredentials] = React.useState<{
    email: string;
    tempPassword: string;
    role: string;
  } | null>(null);
  const [copied, setCopied] = React.useState(false);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadAccounts = React.useCallback(async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from("users")
        .select(`
          id, email, phone, status, user_type, created_at,
          user_roles (
            roles ( name, display_name )
          )
        `)
        .in("user_type", ["admin", "staff"])
        .order("created_at", { ascending: false });

      if (error) throw new Error(error.message);

      const mapped: StaffAccount[] = (data || []).map((u: any) => ({
        id: u.id,
        email: u.email,
        phone: u.phone,
        status: u.status,
        user_type: u.user_type,
        created_at: u.created_at,
        roles: (u.user_roles || []).map((ur: any) => ur.roles?.display_name || ur.roles?.name).filter(Boolean),
      }));

      setAccounts(mapped);
    } catch (err: any) {
      showNotification(err.message || "Failed to load staff accounts", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const generateSecurePassword = () => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%";
    let pwd = "Admin@";
    for (let i = 0; i < 8; i++) {
      pwd += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return pwd + "26!";
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail.trim()) return;

    setIsSubmitting(true);
    const generatedPassword = generateSecurePassword();

    try {
      const res = await fetch("/api/admin/create-user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: newEmail.trim().toLowerCase(),
          password: generatedPassword,
          firstName: newFirstName.trim(),
          lastName: newLastName.trim(),
          phone: newPhone.trim(),
          role: newRole,
          requesterEmail: user?.email,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.error || "Failed to provision staff account");
      }

      setCreatedCredentials({
        email: newEmail.trim().toLowerCase(),
        tempPassword: generatedPassword,
        role: newRole,
      });

      // Reset form
      setNewEmail("");
      setNewFirstName("");
      setNewLastName("");
      setNewPhone("");
      setIsModalOpen(false);
      loadAccounts();
      showNotification("Account provisioned successfully!");
    } catch (err: any) {
      showNotification(err.message || "Error creating account", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (user && user.email !== "admin1@uwearnova.com") {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <div className="w-14 h-14 rounded-full bg-crimson/10 text-crimson flex items-center justify-center mx-auto">
          <ShieldAlert className="w-7 h-7" />
        </div>
        <h2 className="font-serif text-2xl font-medium text-obsidian">Super Administrator Authority Required</h2>
        <p className="text-xs text-obsidian-600 font-light max-w-md mx-auto leading-relaxed">
          Staff provisioning and account creation are strictly restricted to the Lead Super Administrator (admin1@uwearnova.com).
          Store Administrators (admin2 and admin3) possess full operational authority over Catalog, Offline POS Counter, Delivery Rates, Settings, and Order Operations.
        </p>
        <div className="pt-2">
          <Link
            href="/admin"
            className="inline-block px-5 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
          >
            Return to Store Overview
          </Link>
        </div>
      </div>
    );
  }

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
          {notification.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{notification.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Administrative Governance
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Staff & Administrator Management
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Super Administrator console to provision store managers, inventory controllers, and operators.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors flex items-center gap-2 shadow-subtle"
          >
            <UserPlus className="w-4 h-4 text-champagne" />
            <span>Create New Admin / Staff</span>
          </button>
          <button
            type="button"
            onClick={loadAccounts}
            disabled={loading}
            className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors"
            title="Refresh accounts"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Default Accounts Info Banner */}
      <div className="p-4 rounded-xl bg-ivory-light border border-hairline grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div className="space-y-1">
          <span className="text-[10px] uppercase font-bold text-champagne-dark tracking-wider">Super Administrator</span>
          <p className="font-semibold text-obsidian">admin1@uwearnova.com</p>
          <p className="text-obsidian-500 font-light text-[11px]">Sole authority for account provisioning & Super Admin creation.</p>
        </div>
        <div className="space-y-1">
          <span className="text-[10px] uppercase font-bold text-obsidian-500 tracking-wider">Store Administrators</span>
          <p className="font-semibold text-obsidian">admin2, admin3</p>
          <p className="text-obsidian-500 font-light text-[11px]">Full operational administration. Can create staff & admins (cannot create Super Admin).</p>
        </div>
        <div className="space-y-1">
          <span className="text-[10px] uppercase font-bold text-obsidian-500 tracking-wider">Staff Workstations</span>
          <p className="font-semibold text-obsidian">sales1, sales2, inventory1, inventory2</p>
          <p className="text-obsidian-500 font-light text-[11px]">Authorized for inventory updates, catalog edits, and POS sales.</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-ivory-light rounded-2xl border border-hairline shadow-subtle overflow-hidden">
        {loading ? (
          <div className="py-20 text-center">
            <div className="w-7 h-7 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs text-obsidian-500">Loading accounts...</p>
          </div>
        ) : accounts.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <Users className="w-8 h-8 text-obsidian-300 mx-auto" />
            <p className="text-sm font-medium text-obsidian">No staff or admin accounts found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline bg-ivory-sand/40 text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                  <th className="p-4">Staff Identifier</th>
                  <th className="p-4">Role Tier</th>
                  <th className="p-4">Assigned Capabilities</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Created Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {accounts.map((acc) => (
                  <tr key={acc.id} className="hover:bg-ivory transition-colors">
                    <td className="p-4 font-medium text-obsidian">
                      <div className="font-semibold">{acc.email}</div>
                      {acc.phone && <div className="text-[11px] text-obsidian-500">{acc.phone}</div>}
                    </td>
                    <td className="p-4">
                      <span
                        className={`text-[9px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full ${
                          acc.user_type === "admin"
                            ? "bg-champagne-light text-champagne-dark border border-champagne-dark/30"
                            : "bg-blue-100 text-blue-800 border border-blue-200"
                        }`}
                      >
                        {acc.user_type === "admin" ? "★ Administrator" : "Operations Staff"}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex flex-wrap gap-1">
                        {acc.user_type === "admin" ? (
                          <span className="text-[10px] font-medium text-champagne-dark">
                            Full Operational Access (Orders, POS, Inventory, Catalog, Finance)
                          </span>
                        ) : acc.roles && acc.roles.length > 0 ? (
                          acc.roles.map((r, i) => (
                            <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-ivory-sand text-obsidian">
                              {r}
                            </span>
                          ))
                        ) : (
                          <span className="text-[10px] text-obsidian-500">POS & Inventory Operations</span>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="text-[10px] font-semibold text-emerald-700 capitalize">
                        ● {acc.status}
                      </span>
                    </td>
                    <td className="p-4 text-obsidian-600">
                      {new Date(acc.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Creation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4">
            <div className="flex items-start justify-between border-b border-hairline pb-3">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-champagne-dark font-semibold">
                  Account Provisioning
                </span>
                <h3 className="font-serif text-xl font-medium text-obsidian">
                  Create Administrator or Staff
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-xs text-obsidian-500 hover:text-obsidian"
              >
                ✕ Close
              </button>
            </div>

            <form onSubmit={handleCreateAccount} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-semibold text-obsidian">First Name</label>
                  <input
                    type="text"
                    required
                    value={newFirstName}
                    onChange={(e) => setNewFirstName(e.target.value)}
                    placeholder="Bilal"
                    className="w-full px-3 py-2 rounded-lg border border-hairline bg-white"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-semibold text-obsidian">Last Name</label>
                  <input
                    type="text"
                    required
                    value={newLastName}
                    onChange={(e) => setNewLastName(e.target.value)}
                    placeholder="Ahmed"
                    className="w-full px-3 py-2 rounded-lg border border-hairline bg-white"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-obsidian">Corporate / Work Email</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="admin.ops@uwearnova.com"
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-white"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-obsidian">Mobile Contact (Optional)</label>
                <input
                  type="tel"
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  placeholder="+92 300 1234567"
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-white"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-obsidian">Assigned Privilege Tier</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-hairline bg-white"
                >
                  {roleOptions.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
                {!isSuperAdmin && (
                  <p className="text-[11px] text-obsidian-500 font-light mt-0.5">
                    Note: As a Store Administrator, you can provision operational Admins and Staff. Only admin1 can provision Super Administrators.
                  </p>
                )}
              </div>

              <p className="text-[11px] text-obsidian-500 font-light pt-1">
                A strong temporary password will be automatically generated and displayed on screen upon creation for secure hand-off.
              </p>

              <div className="flex justify-end gap-2 pt-3 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-button border border-hairline text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800 disabled:opacity-50"
                >
                  {isSubmitting ? "Provisioning..." : "Provision Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Temporary Credentials Popup */}
      {createdCredentials && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/70 backdrop-blur-xs">
          <div className="w-full max-w-md bg-ivory rounded-2xl p-6 shadow-card border border-champagne-dark space-y-4">
            <div className="w-12 h-12 rounded-full bg-champagne-light text-champagne-dark flex items-center justify-center mx-auto">
              <Key className="w-6 h-6" />
            </div>

            <div className="text-center space-y-1">
              <h3 className="font-serif text-xl font-medium text-obsidian">
                Account Provisioned
              </h3>
              <p className="text-xs text-obsidian-600">
                Please copy and securely deliver these initial credentials to the user.
              </p>
            </div>

            <div className="p-4 bg-white rounded-xl border border-hairline space-y-2 text-xs">
              <div>
                <span className="text-[10px] text-obsidian-400 uppercase font-semibold">User Email:</span>
                <p className="font-mono font-medium text-obsidian text-sm">{createdCredentials.email}</p>
              </div>
              <div>
                <span className="text-[10px] text-obsidian-400 uppercase font-semibold">Temporary Password:</span>
                <div className="flex items-center justify-between p-2 rounded bg-ivory-sand/50 font-mono text-obsidian font-bold text-sm">
                  <span>{createdCredentials.tempPassword}</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(createdCredentials.tempPassword)}
                    className="p-1 hover:text-champagne-dark"
                    title="Copy Password"
                  >
                    {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <span className="text-[10px] text-obsidian-400 uppercase font-semibold">Assigned Role:</span>
                <p className="font-medium text-obsidian capitalize">{createdCredentials.role.replace("_", " ")}</p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setCreatedCredentials(null)}
                className="w-full py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800"
              >
                Done (Credentials Recorded)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
