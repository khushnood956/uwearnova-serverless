"use client";

import * as React from "react";
import Link from "next/link";
import { X, ChevronRight, ChevronDown, Phone, Mail, User as UserIcon, LogOut } from "lucide-react";
import { BRAND_CONFIG } from "@/lib/brand";
import { catalogApi } from "@/lib/api/catalog";
import { CategoryTreeNode } from "@/lib/api/types";
import { useAuth } from "@/context/AuthContext";

interface MobileNavProps {
  isOpen: boolean;
  onClose: () => void;
}

const FALLBACK_CATEGORIES: CategoryTreeNode[] = [
  { id: "1", name: "Men", slug: "men", level: 1, is_active: true, is_coming_soon: false, display_order: 1, children: [] },
  { id: "2", name: "Women", slug: "women", level: 1, is_active: true, is_coming_soon: false, display_order: 2, children: [] },
  { id: "3", name: "Kids", slug: "kids", level: 1, is_active: true, is_coming_soon: false, display_order: 3, children: [] },
  { id: "4", name: "Footwear", slug: "footwear", level: 1, is_active: true, is_coming_soon: true, display_order: 4, children: [] },
  { id: "5", name: "Accessories", slug: "accessories", level: 1, is_active: true, is_coming_soon: true, display_order: 5, children: [] },
  { id: "6", name: "Perfumes", slug: "perfumes", level: 1, is_active: true, is_coming_soon: true, display_order: 6, children: [] },
];

function cleanSubName(name: string, parentName: string): string {
  const re = new RegExp(`^${parentName}('s)?\\s+`, "i");
  return name.replace(re, "");
}

export function MobileNav({ isOpen, onClose }: MobileNavProps) {
  const [categories, setCategories] = React.useState<CategoryTreeNode[]>(FALLBACK_CATEGORIES);
  const [expandedId, setExpandedId] = React.useState<string | number | null>(null);
  const { user, isAuthenticated, openAuthModal, logout } = useAuth();

  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      catalogApi.getCategoryTree()
        .then((tree) => {
          if (Array.isArray(tree) && tree.length > 0) {
            setCategories(tree);
          }
        })
        .catch(() => {});
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleExpand = (id: string | number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Mobile Navigation"
      className="fixed inset-0 z-50 flex md:hidden"
    >
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-obsidian/60 backdrop-blur-xs transition-opacity duration-base ease-out"
      />

      {/* Drawer */}
      <div className="relative w-4/5 max-w-sm bg-ivory h-full shadow-card-hover flex flex-col z-10 p-6 overflow-y-auto border-r border-hairline">
        <div className="flex items-center justify-between pb-4 border-b border-hairline">
          <Link
            href="/"
            onClick={onClose}
            className="inline-flex items-center"
            aria-label="UWEARNOVA Home"
          >
            <img
              src="/logo/transparent/navbar/logo-navbar-dark.svg"
              alt="UWEARNOVA"
              className="h-7 w-auto object-contain"
            />
          </Link>
          <button
            onClick={onClose}
            aria-label="Close menu"
            className="w-10 h-10 flex items-center justify-center text-obsidian-600 hover:text-obsidian rounded-button hover:bg-ivory-sand transition-colors duration-fast"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* User Account Bar in Mobile Drawer */}
        <div className="py-3 border-b border-hairline">
          {isAuthenticated ? (
            <div className="flex items-center justify-between py-1">
              <div>
                <p className="text-xs font-semibold text-obsidian">
                  {user?.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : "Welcome back"}
                </p>
                <p className="text-[11px] text-obsidian-500 truncate max-w-[180px]">{user?.email}</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  logout();
                  onClose();
                }}
                className="text-xs text-crimson flex items-center gap-1 font-medium hover:underline"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => {
                onClose();
                openAuthModal("signin");
              }}
              className="w-full py-2.5 px-3 rounded-lg bg-obsidian text-ivory text-xs font-medium tracking-wide flex items-center justify-center gap-2 hover:bg-obsidian-800 transition-colors"
            >
              <UserIcon className="w-4 h-4" />
              Sign In / Register
            </button>
          )}
        </div>

        {/* Dynamic Categories Nav */}
        <nav className="py-4 flex flex-col space-y-1">
          {categories.map((dept) => {
            const hasChildren = dept.children && dept.children.length > 0;
            const isComingSoon = dept.is_coming_soon;
            const isExpanded = expandedId === dept.id;

            return (
              <div key={dept.id || dept.slug} className="flex flex-col">
                <div className="flex items-center justify-between py-2.5 px-3 rounded-lg text-sm font-medium text-obsidian hover:bg-ivory-sand transition-colors duration-fast">
                  <Link
                    href={`/collections/${dept.slug}`}
                    onClick={onClose}
                    className="flex-1 flex items-center gap-2"
                  >
                    <span>{dept.name}</span>
                    {isComingSoon && (
                      <span className="text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded-full bg-champagne-light text-champagne-dark border border-champagne-dark/20">
                        Soon
                      </span>
                    )}
                  </Link>
                  {!isComingSoon && hasChildren && (
                    <button
                      type="button"
                      onClick={() => toggleExpand(dept.id)}
                      aria-label={`Toggle ${dept.name} subcategories`}
                      className="p-1 -mr-1 text-obsidian-500 hover:text-obsidian"
                    >
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                  )}
                </div>

                {/* Subcategories Accordion */}
                {!isComingSoon && hasChildren && isExpanded && (
                  <div className="pl-4 py-1 space-y-1 flex flex-col border-l border-hairline ml-4 my-1">
                    <Link
                      href={`/collections/${dept.slug}`}
                      onClick={onClose}
                      className="py-1.5 px-3 text-xs font-semibold text-obsidian hover:text-champagne-dark"
                    >
                      All {dept.name}
                    </Link>
                    {dept.children.map((sub) => (
                      <Link
                        key={sub.id || sub.slug}
                        href={`/collections/${sub.slug}`}
                        onClick={onClose}
                        className="py-1.5 px-3 text-xs text-obsidian-600 hover:text-obsidian rounded-lg hover:bg-ivory-sand font-medium"
                      >
                        {cleanSubName(sub.name, dept.name)}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <div className="mt-auto pt-6 border-t border-hairline space-y-3 text-xs text-obsidian-600">
          <div className="flex items-center gap-2">
            <Phone className="w-4 h-4 text-champagne-dark" />
            <span>{BRAND_CONFIG.contact.phone}</span>
          </div>
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-champagne-dark" />
            <span>{BRAND_CONFIG.contact.email}</span>
          </div>
          <p className="text-[11px] text-obsidian-400 pt-1">
            {BRAND_CONFIG.contact.supportHours}
          </p>
        </div>
      </div>
    </div>
  );
}
