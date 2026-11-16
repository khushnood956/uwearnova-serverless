"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronDown, Sparkles } from "lucide-react";
import { catalogApi } from "@/lib/api/catalog";
import { CategoryTreeNode } from "@/lib/api/types";

interface NavbarProps {
  isTransparent?: boolean;
}

// Fallback baseline departments in case API is loading
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

export function Navbar({ isTransparent = false }: NavbarProps) {
  const [categories, setCategories] = React.useState<CategoryTreeNode[]>(FALLBACK_CATEGORIES);
  const [activeDropdown, setActiveDropdown] = React.useState<string | number | null>(null);
  const timeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = (deptId: string | number) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setActiveDropdown(deptId);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      setActiveDropdown(null);
    }, 180);
  };

  React.useEffect(() => {
    let mounted = true;
    catalogApi.getCategoryTree()
      .then((tree) => {
        if (mounted && Array.isArray(tree) && tree.length > 0) {
          setCategories(tree);
        }
      })
      .catch((err) => {
        console.warn("Failed to load category tree:", err);
      });
    return () => {
      mounted = false;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <nav className="hidden md:flex items-center space-x-6 lg:space-x-8 text-xs sm:text-sm font-medium tracking-wide">
      {categories.map((dept) => {
        const hasChildren = dept.children && dept.children.length > 0;
        const isComingSoon = dept.is_coming_soon;
        const isOpen = activeDropdown === dept.id;

        return (
          <div
            key={dept.id || dept.slug}
            className="relative py-2"
            onMouseEnter={() => !isComingSoon && hasChildren && handleMouseEnter(dept.id)}
            onMouseLeave={handleMouseLeave}
          >
            <Link
              href={`/collections/${dept.slug}`}
              className={`py-1 inline-flex items-center gap-1.5 relative group transition-colors duration-fast ${
                isTransparent
                  ? "text-ivory-light/90 hover:text-white"
                  : "text-obsidian-700 hover:text-obsidian"
              }`}
            >
              <span>{dept.name}</span>

              {isComingSoon && (
                <span className="text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded-full bg-champagne-light text-champagne-dark border border-champagne-dark/20 ml-0.5">
                  Soon
                </span>
              )}

              {!isComingSoon && hasChildren && (
                <ChevronDown className={`w-3 h-3 text-obsidian-400 group-hover:text-obsidian transition-transform duration-fast ${isOpen ? "rotate-180 text-obsidian" : ""}`} />
              )}

              <span className="absolute bottom-0 left-0 w-full h-[1.5px] bg-champagne origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-base ease-out" />
            </Link>

            {/* Subcategories Dropdown Panel with Seamless Hover Bridge */}
            {!isComingSoon && hasChildren && isOpen && (
              <div
                className="absolute left-0 top-full pt-1.5 w-56 z-50 animate-in fade-in slide-in-from-top-1 duration-150"
                onMouseEnter={() => handleMouseEnter(dept.id)}
                onMouseLeave={handleMouseLeave}
              >
                {/* Invisible hover bridge to eliminate gap */}
                <div className="absolute -top-3 left-0 right-0 h-4 bg-transparent" />
                
                <div className="bg-ivory rounded-xl shadow-card border border-hairline py-3 px-2">
                  <div className="px-3 pb-2 mb-1 border-b border-hairline/60">
                    <Link
                      href={`/collections/${dept.slug}`}
                      className="text-xs font-semibold text-obsidian hover:text-champagne-dark transition-colors uppercase tracking-wider flex items-center justify-between"
                    >
                      <span>All {dept.name}</span>
                      <Sparkles className="w-3 h-3 text-champagne-dark" />
                    </Link>
                  </div>
                  <div className="flex flex-col space-y-0.5">
                    {dept.children.map((sub) => (
                      <Link
                        key={sub.id || sub.slug}
                        href={`/collections/${sub.slug}`}
                        className="px-3 py-1.5 text-xs text-obsidian-700 hover:text-obsidian hover:bg-ivory-sand rounded-lg transition-colors font-medium"
                      >
                        {cleanSubName(sub.name, dept.name)}
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}
