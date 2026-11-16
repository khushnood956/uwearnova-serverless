"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ClipboardList,
  Package,
  Truck,
  Boxes,
  Headphones,
  ShieldAlert,
  ArrowLeft,
  LogOut,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { BRAND_CONFIG } from "@/lib/brand";

interface StaffLayoutProps {
  children: React.ReactNode;
}

export default function StaffLayout({ children }: StaffLayoutProps) {
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
            <ClipboardList className="w-6 h-6" />
          </div>
          <h1 className="font-serif text-2xl font-medium text-obsidian">Staff Operations Workspace</h1>
          <p className="text-xs text-obsidian-600 font-light">
            Please authenticate with your staff account credentials to access your assigned work queues.
          </p>
          <button
            type="button"
            onClick={() => openAuthModal("signin")}
            className="w-full py-3 px-4 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
          >
            Sign In to Staff Portal
          </button>
        </div>
      </div>
    );
  }

  const isStaffOrAdmin = user?.user_type === "staff" || user?.user_type === "admin";
  if (!isStaffOrAdmin) {
    return (
      <div className="min-h-screen bg-ivory flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-ivory-light border border-hairline rounded-2xl p-8 shadow-card text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-crimson/10 text-crimson flex items-center justify-center mx-auto">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h1 className="font-serif text-2xl font-medium text-obsidian">Staff Clearance Required</h1>
          <p className="text-xs text-obsidian-600 font-light">
            Your account ({user?.email}) is a standard customer account and is not authorized to access staff work queues.
          </p>
          <Link
            href="/"
            className="inline-block px-5 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold"
          >
            Return to Storefront
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-ivory font-sans text-obsidian">
      {/* Top Operations Bar */}
      <header className="h-16 bg-obsidian text-ivory border-b border-obsidian-800 flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-serif text-xl font-medium tracking-tight text-ivory">
            {BRAND_CONFIG.name}
          </Link>
          <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-champagne-dark text-ivory">
            Staff Operations
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="hidden sm:block text-right">
            <p className="text-ivory font-medium truncate max-w-[200px]">{user?.email}</p>
            <p className="text-[10px] text-ivory-light/60 uppercase tracking-wider">
              {user?.user_type === "admin" ? "Super Administrator" : "Fulfillment & Operations Specialist"}
            </p>
          </div>
          {user?.user_type === "admin" && (
            <Link
              href="/admin"
              className="text-[11px] text-champagne hover:underline font-semibold"
            >
              ★ Admin Console
            </Link>
          )}
          <Link
            href="/"
            className="text-[11px] text-ivory-light/80 hover:text-white"
          >
            Storefront
          </Link>
          <button
            type="button"
            onClick={logout}
            className="text-[11px] text-crimson hover:underline"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 p-6 sm:p-10 max-w-7xl w-full mx-auto">{children}</main>
    </div>
  );
}
