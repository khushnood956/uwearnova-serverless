"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Search, Heart, ShoppingBag, User as UserIcon, LogOut } from "lucide-react";
import { BRAND_CONFIG } from "@/lib/brand";
import { AnnouncementBar } from "./AnnouncementBar";
import { Navbar } from "./Navbar";
import { MobileNav } from "./MobileNav";
import { SearchModal } from "@/components/search/SearchModal";
import { useCart } from "@/context/CartContext";
import { useWishlist } from "@/context/WishlistContext";
import { useAuth } from "@/context/AuthContext";

interface HeaderProps {
  cartCount?: number;
  wishlistCount?: number;
  onOpenSearch?: () => void;
  onOpenCart?: () => void;
}

export function Header({
  cartCount: propCartCount,
  wishlistCount: propWishlistCount,
  onOpenSearch,
  onOpenCart,
}: HeaderProps) {
  const pathname = usePathname();
  const isHome = pathname === "/";

  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);
  const [searchModalOpen, setSearchModalOpen] = React.useState(false);
  const [isScrolled, setIsScrolled] = React.useState(false);

  const { totalItems, openCartDrawer } = useCart();
  const { totalWishlistCount } = useWishlist();
  const { user, isAuthenticated, openAuthModal, logout } = useAuth();
  const [accountMenuOpen, setAccountMenuOpen] = React.useState(false);

  const cartCount = propCartCount !== undefined ? propCartCount : totalItems;
  const wishlistCount =
    propWishlistCount !== undefined ? propWishlistCount : totalWishlistCount;

  React.useEffect(() => {
    function handleScroll() {
      setIsScrolled(window.scrollY > 40);
    }
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleSearchClick = () => {
    if (onOpenSearch) {
      onOpenSearch();
    } else {
      setSearchModalOpen(true);
    }
  };

  const handleCartClick = () => {
    if (onOpenCart) {
      onOpenCart();
    } else {
      openCartDrawer();
    }
  };

  const isTransparent = isHome && !isScrolled;

  return (
    <>
      <header
        className={`sticky top-0 z-40 w-full transition-[background-color,border-color,box-shadow] duration-base ease-out ${
          isTransparent
            ? "bg-obsidian/40 backdrop-blur-md border-b border-ivory-light/10 text-ivory-light"
            : "bg-ivory/95 backdrop-blur-md border-b border-hairline shadow-subtle text-obsidian"
        }`}
      >
        <AnnouncementBar />

        {/* Fixed Header Bar (No padding jump on scroll) */}
        <div className="h-16 lg:h-20 flex items-center">
          <div className="container-site flex items-center justify-between">
            {/* Left: Mobile hamburger (Visible below md) */}
            <div className="flex items-center md:hidden">
              <button
                type="button"
                onClick={() => setMobileNavOpen(true)}
                aria-label="Open navigation menu"
                className={`p-2 -ml-2 rounded-button focus-visible:ring-1 focus-visible:ring-champagne transition-colors duration-fast ${
                  isTransparent
                    ? "text-ivory hover:text-white"
                    : "text-obsidian hover:text-obsidian-600"
                }`}
              >
                <Menu className="w-5 h-5" />
              </button>
            </div>

            {/* Brand Logo */}
            <div className="flex items-center gap-8">
              <Link
                href="/"
                className="inline-flex items-center transition-opacity duration-fast hover:opacity-90 py-1"
                aria-label="UWEARNOVA Home"
              >
                <img
                  src={isTransparent ? "/logo/transparent/navbar/logo-navbar-white.svg" : "/logo/transparent/navbar/logo-navbar-dark.svg"}
                  alt="UWEARNOVA"
                  className="h-7 sm:h-8 lg:h-9 w-auto object-contain"
                />
              </Link>
            </div>

            {/* Center: Desktop Navigation (md and up) */}
            <Navbar isTransparent={isTransparent} />

            {/* Right: Actions */}
            <div className="flex items-center space-x-1 sm:space-x-2">
              <button
                type="button"
                onClick={handleSearchClick}
                aria-label="Search catalogue"
                className={`w-10 h-10 rounded-button flex items-center justify-center transition-colors duration-fast ${
                  isTransparent
                    ? "text-ivory-light hover:bg-white/10"
                    : "text-obsidian hover:bg-ivory-sand"
                }`}
              >
                <Search className="w-5 h-5" />
              </button>

              <Link
                href="/wishlist"
                aria-label={`Saved items, ${wishlistCount} pieces`}
                className={`w-10 h-10 rounded-button flex items-center justify-center transition-colors duration-fast relative ${
                  isTransparent
                    ? "text-ivory-light hover:bg-white/10"
                    : "text-obsidian hover:bg-ivory-sand"
                }`}
              >
                <Heart className="w-5 h-5" />
                {wishlistCount > 0 && (
                  <span className="absolute top-1.5 right-1.5 flex items-center justify-center min-w-[16px] h-4 px-1 text-[10px] font-bold text-ivory bg-champagne-dark rounded-button">
                    {wishlistCount}
                  </span>
                )}
              </Link>

              <button
                type="button"
                onClick={handleCartClick}
                aria-label={`Shopping bag, ${cartCount} items`}
                className={`w-10 h-10 rounded-button flex items-center justify-center transition-colors duration-fast relative ${
                  isTransparent
                    ? "text-ivory-light hover:bg-white/10"
                    : "text-obsidian hover:bg-ivory-sand"
                }`}
              >
                <ShoppingBag className="w-5 h-5" />
                {cartCount > 0 && (
                  <span className="absolute top-1.5 right-1.5 flex items-center justify-center min-w-[16px] h-4 px-1 text-[10px] font-bold text-ivory bg-obsidian rounded-button">
                    {cartCount}
                  </span>
                )}
              </button>

              {/* Customer Account */}
              <div className="relative">
                {isAuthenticated ? (
                  <>
                    <button
                      type="button"
                      onClick={() => setAccountMenuOpen((prev) => !prev)}
                      aria-label="Account menu"
                      aria-expanded={accountMenuOpen}
                      className={`w-10 h-10 rounded-button flex items-center justify-center transition-colors duration-fast relative ${
                        isTransparent
                          ? "text-ivory-light hover:bg-white/10"
                          : "text-obsidian hover:bg-ivory-sand"
                      }`}
                    >
                      <UserIcon className="w-5 h-5" />
                      <span className="absolute bottom-2 right-2 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-ivory" />
                    </button>
                    {accountMenuOpen && (
                      <div
                        className="absolute right-0 mt-2 w-56 bg-ivory rounded-xl shadow-card border border-hairline py-2 z-50 text-obsidian"
                        onMouseLeave={() => setAccountMenuOpen(false)}
                      >
                        <div className="px-4 py-2 border-b border-hairline">
                          <p className="text-xs text-obsidian-400 uppercase tracking-wider font-medium">Signed in as</p>
                          <p className="text-sm font-semibold truncate text-obsidian mt-0.5">
                            {user?.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : user?.email}
                          </p>
                          <p className="text-xs text-obsidian-500 truncate">{user?.email}</p>
                        </div>
                        <div className="py-1 border-b border-hairline">
                          <Link
                            href="/account"
                            onClick={() => setAccountMenuOpen(false)}
                            className="block px-4 py-2 text-xs text-obsidian hover:bg-ivory-sand font-medium transition-colors"
                          >
                            My Account Dashboard
                          </Link>
                          <Link
                            href="/account?tab=orders"
                            onClick={() => setAccountMenuOpen(false)}
                            className="block px-4 py-2 text-xs text-obsidian hover:bg-ivory-sand font-medium transition-colors"
                          >
                            My Orders & Tracking
                          </Link>
                          {user?.user_type === "admin" && (
                            <Link
                              href="/admin"
                              onClick={() => setAccountMenuOpen(false)}
                              className="block px-4 py-2 text-xs text-champagne-dark hover:bg-champagne/10 font-semibold transition-colors"
                            >
                              ★ Store Admin Dashboard
                            </Link>
                          )}
                          {(user?.user_type === "staff" || user?.user_type === "admin") && (
                            <Link
                              href="/staff"
                              onClick={() => setAccountMenuOpen(false)}
                              className="block px-4 py-2 text-xs text-obsidian hover:bg-ivory-sand font-medium transition-colors"
                            >
                              Staff Operations
                            </Link>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            setAccountMenuOpen(false);
                            logout();
                          }}
                          className="w-full text-left px-4 py-2.5 text-xs text-crimson hover:bg-crimson/5 flex items-center gap-2 transition-colors font-medium"
                        >
                          <LogOut className="w-3.5 h-3.5" />
                          Sign Out
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => openAuthModal("signin")}
                    aria-label="Sign in"
                    className={`w-10 h-10 rounded-button flex items-center justify-center transition-colors duration-fast ${
                      isTransparent
                        ? "text-ivory-light hover:bg-white/10"
                        : "text-obsidian hover:bg-ivory-sand"
                    }`}
                    title="Sign In"
                  >
                    <UserIcon className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <MobileNav
        isOpen={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />

      <SearchModal
        isOpen={searchModalOpen}
        onClose={() => setSearchModalOpen(false)}
      />
    </>
  );
}
