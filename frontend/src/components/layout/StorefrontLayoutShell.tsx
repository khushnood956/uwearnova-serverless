"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { CartDrawer } from "@/components/cart/CartDrawer";
import { AuthModal } from "@/components/auth/AuthModal";
import { SkipToContent } from "@/components/common/SkipToContent";

export function StorefrontLayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuth();

  const isPortalRoute = pathname.startsWith("/admin") || pathname.startsWith("/staff");

  // Read role synchronously from cookie or localStorage to immediately detect privileged users
  // and prevent ANY storefront flash during initial client hydration
  const [activeRole, setActiveRole] = React.useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const match = document.cookie.match(/(?:^|; )uwear_user_role=([^;]*)/);
      if (match) return decodeURIComponent(match[1]);
      try {
        return localStorage.getItem("uwear_user_role");
      } catch {
        return null;
      }
    }
    return null;
  });

  // Keep activeRole synchronized with auth state
  React.useEffect(() => {
    if (user?.user_type) {
      setActiveRole(user.user_type);
    }
  }, [user]);

  const isPrivileged = activeRole === "admin" || activeRole === "staff";

  // Strict enforcement: When authenticated as Admin or Staff, there is NO ROUTE to the customer website.
  // Immediately redirect to authorized workstation using replace
  React.useEffect(() => {
    if (isPrivileged && !isPortalRoute) {
      const target = activeRole === "admin" ? "/admin" : "/staff";
      window.location.replace(target);
    }
  }, [isPrivileged, isPortalRoute, activeRole]);

  // If in portal route, render cleanly with dedicated workstation container
  if (isPortalRoute) {
    return (
      <>
        <div id="main-content" className="flex-1 flex flex-col focus:outline-none min-h-screen">
          {children}
        </div>
        <AuthModal />
      </>
    );
  }

  // If privileged staff/admin attempted to view public customer routes, shield completely
  // (Zero customer storefront or hero section is ever rendered in the DOM)
  if (isPrivileged) {
    return (
      <div className="min-h-screen bg-obsidian text-ivory flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-2 border-champagne border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-champagne uppercase tracking-widest font-semibold">
          Redirecting to Authorized Workstation...
        </p>
      </div>
    );
  }

  // Normal customer storefront layout
  return (
    <>
      <SkipToContent />
      <Header />
      <div id="main-content" className="flex-1 flex flex-col focus:outline-none">
        {children}
      </div>
      <Footer />
      <CartDrawer />
      <AuthModal />
    </>
  );
}
