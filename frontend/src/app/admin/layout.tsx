"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderTree,
  ShoppingBag,
  Package,
  CreditCard,
  Users,
  RotateCcw,
  ShieldAlert,
  ArrowLeft,
  LogOut,
  Sparkles,
  Store,
  Sliders,
  UserCog,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { BRAND_CONFIG } from "@/lib/brand";

interface AdminLayoutProps {
  children: React.ReactNode;
}

const ADMIN_NAV = [
  { name: "Executive Overview", href: "/admin", icon: LayoutDashboard },
  { name: "My Profile & Security", href: "/admin/profile", icon: UserCog },
  { name: "Rates & Payment Settings", href: "/admin/settings", icon: Sliders },
  { name: "Offline Sales (POS)", href: "/admin/pos", icon: Store },
  { name: "Departments & Categories", href: "/admin/categories", icon: FolderTree },
  { name: "Products & Catalogue", href: "/admin/products", icon: ShoppingBag },
  { name: "Order Operations", href: "/admin/orders", icon: Package },
  { name: "Payments & COD", href: "/admin/payments", icon: CreditCard },
  { name: "Customer Accounts", href: "/admin/customers", icon: Users },
  { name: "Staff & Administrators", href: "/admin/staff", icon: Sparkles },
  { name: "Returns & Exchanges", href: "/admin/returns", icon: RotateCcw },
  { name: "Audit Trail", href: "/admin/audit-logs", icon: ShieldAlert },
];

export default function AdminLayout({ children }: AdminLayoutProps) {
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, logout, openAuthModal } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-obsidian-900 text-ivory flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-champagne border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-ivory flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-ivory-light border border-hairline rounded-2xl p-8 shadow-card text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-ivory-sand flex items-center justify-center mx-auto text-obsidian">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h1 className="font-serif text-2xl font-medium text-obsidian">Administrative Access</h1>
          <p className="text-xs text-obsidian-600 font-light">
            You must be signed in with administrative credentials to access the store management console.
          </p>
          <button
            type="button"
            onClick={() => openAuthModal("signin")}
            className="w-full py-3 px-4 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
          >
            Sign In as Administrator
          </button>
        </div>
      </div>
    );
  }

  const isAuthorized = user?.user_type === "admin" || user?.user_type === "staff";
  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-ivory flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-ivory-light border border-hairline rounded-2xl p-8 shadow-card text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-crimson/10 text-crimson flex items-center justify-center mx-auto">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h1 className="font-serif text-2xl font-medium text-obsidian">Restricted Access</h1>
          <p className="text-xs text-obsidian-600 font-light">
            Your account ({user?.email}) has role <strong className="capitalize">{user?.user_type}</strong>. Only authorized administrative and staff personnel can access this workspace.
          </p>
          <div className="flex gap-2 justify-center pt-2">
            <button
              type="button"
              onClick={logout}
              className="px-4 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold"
            >
              Sign Out & Return to Store
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-ivory font-sans text-obsidian">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-obsidian text-ivory shrink-0 border-r border-obsidian-800 flex flex-col justify-between">
        <div>
          {/* Logo & Context */}
          <div className="p-6 border-b border-white/10">
            <div className="inline-flex items-center py-1 select-none">
              <img
                src="/logo/transparent/navbar/logo-navbar-white.svg"
                alt="UWEARNOVA"
                className="h-8 w-auto object-contain"
              />
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-champagne font-medium tracking-wider uppercase">
              <Sparkles className="w-3 h-3" />
              <span>Store Administration</span>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="p-3 space-y-1">
            {ADMIN_NAV.filter((item) => {
              // Only admin1 (Super Admin) is authorized to view and manage Staff & Administrators
              if (item.href === "/admin/staff" && user?.email !== "admin1@uwearnova.com") {
                return false;
              }
              return true;
            }).map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-champagne text-obsidian font-semibold shadow-subtle"
                      : "text-ivory-light/80 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Footer User Info */}
        <div className="p-4 border-t border-white/10 text-xs text-ivory-light/70 space-y-3">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-champagne font-semibold">
              {user?.email === "admin1@uwearnova.com" ? "★ Super Administrator" : "Store Administrator"}
            </p>
            <p className="text-xs font-semibold text-ivory truncate mt-0.5">
              {user?.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : user?.email}
            </p>
            <p className="text-[11px] text-ivory-light/50 truncate">{user?.email}</p>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-white/5">
            <Link
              href="/admin/profile"
              className="text-[11px] text-champagne hover:underline inline-flex items-center gap-1 font-semibold"
            >
              <UserCog className="w-3.5 h-3.5" />
              <span>Password & Name</span>
            </Link>
            <button
              type="button"
              onClick={logout}
              className="text-[11px] text-crimson hover:underline inline-flex items-center gap-1 font-semibold"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        <main className="flex-1 p-6 sm:p-10">{children}</main>
      </div>
    </div>
  );
}
