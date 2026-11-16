"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight, Check, MapPin, Phone } from "lucide-react";
import { BRAND_CONFIG } from "@/lib/brand";
import { Button } from "@/components/ui/Button";

export function Footer() {
  const [email, setEmail] = React.useState("");
  const [isSubscribed, setIsSubscribed] = React.useState(false);

  const handleNewsletterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim() && email.includes("@")) {
      setIsSubscribed(true);
      setEmail("");
      setTimeout(() => setIsSubscribed(false), 5000);
    }
  };

  return (
    <footer className="bg-obsidian text-ivory-light pt-16 pb-12 border-t border-obsidian-800">
      <div className="container-site space-y-12">
        {/* Top Section: Brand & Newsletter */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-12 border-b border-obsidian-800">
          <div className="lg:col-span-6 space-y-4">
            <Link
              href="/"
              className="inline-flex items-center transition-opacity hover:opacity-90 py-1"
              aria-label="UWEARNOVA Home"
            >
              <img
                src="/logo/transparent/footer/logo-footer-horizontal-gold.svg"
                alt="UWEARNOVA"
                className="h-9 lg:h-10 w-auto object-contain"
              />
            </Link>
            <p className="text-sm text-ivory-light/75 max-w-md leading-relaxed font-light">
              {BRAND_CONFIG.tagline}. Redefining contemporary luxury fashion in Pakistan with clean architectural tailoring, mindful textiles, and enduring elegance.
            </p>
            <div className="flex items-center gap-4 text-xs text-ivory-light/60 pt-2 font-light">
              <span className="flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-champagne-light" />
                {BRAND_CONFIG.contact.location}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-champagne-light" />
                {BRAND_CONFIG.contact.phone}
              </span>
            </div>
          </div>

          <div className="lg:col-span-6 space-y-4">
            <span className="text-xs font-semibold tracking-[0.18em] uppercase text-champagne-light">
              The UWEARNOVA Journal
            </span>
            <p className="text-sm text-ivory-light/80 font-light">
              Receive private previews of limited-run capsules and editorial announcements.
            </p>

            <form onSubmit={handleNewsletterSubmit} className="flex gap-2 max-w-md">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email address"
                className="flex-1 h-12 px-4 rounded-button text-xs sm:text-sm bg-obsidian-900 border border-obsidian-700 text-white placeholder:text-obsidian-400 focus:outline-none focus:border-champagne transition-colors duration-fast"
              />
              <Button
                type="submit"
                variant="accent"
                size="md"
                className="h-12 bg-champagne text-obsidian hover:bg-champagne-light font-semibold shrink-0 group/btn"
              >
                <span>Join</span>
                <ArrowRight className="w-4 h-4 ml-1 transition-transform duration-base ease-out group-hover/btn:translate-x-1" />
              </Button>
            </form>

            {isSubscribed && (
              <p className="text-xs text-champagne-light flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5" />
                <span>Thank you. You have been added to our private journal list.</span>
              </p>
            )}
          </div>
        </div>

        {/* Links Navigation Columns with 1px scaleX underline hover */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-xs">
          {/* Shop */}
          <div className="space-y-3">
            <h4 className="font-serif font-medium text-sm text-white tracking-wide">
              Catalogue
            </h4>
            <ul className="space-y-2.5 text-ivory-light/75 font-light">
              {[
                { name: "Women's Collection", href: "/collections/women" },
                { name: "Men's Tailoring", href: "/collections/men" },
                { name: "Artisan Footwear", href: "/collections/footwear" },
                { name: "Leather Accessories", href: "/collections/accessories" },
                { name: "New Arrivals", href: "/collections/new-arrivals" },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="inline-block relative py-0.5 group hover:text-white transition-colors duration-fast"
                  >
                    <span>{link.name}</span>
                    <span className="absolute bottom-0 left-0 w-full h-[1px] bg-champagne origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-base ease-out" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Curations */}
          <div className="space-y-3">
            <h4 className="font-serif font-medium text-sm text-white tracking-wide">
              Curated Capsules
            </h4>
            <ul className="space-y-2.5 text-ivory-light/75 font-light">
              {[
                { name: "Signature Collection", href: "/collections/signature" },
                { name: "Everyday Essentials", href: "/collections/essentials" },
                { name: "Trending Pieces", href: "/collections/trending" },
                { name: "Seasonal Reductions", href: "/collections/sale" },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="inline-block relative py-0.5 group hover:text-white transition-colors duration-fast"
                  >
                    <span>{link.name}</span>
                    <span className="absolute bottom-0 left-0 w-full h-[1px] bg-champagne origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-base ease-out" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Customer Care */}
          <div className="space-y-3">
            <h4 className="font-serif font-medium text-sm text-white tracking-wide">
              Customer Care
            </h4>
            <ul className="space-y-2.5 text-ivory-light/75 font-light">
              {[
                { name: "Shipping & Delivery", href: "/shipping-delivery" },
                { name: "Exchanges & Returns", href: "/returns-exchanges" },
                { name: "Frequently Asked Questions", href: "/faqs" },
                { name: "WhatsApp Concierge", href: "/contact" },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="inline-block relative py-0.5 group hover:text-white transition-colors duration-fast"
                  >
                    <span>{link.name}</span>
                    <span className="absolute bottom-0 left-0 w-full h-[1px] bg-champagne origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-base ease-out" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Brand & Atelier */}
          <div className="space-y-3">
            <h4 className="font-serif font-medium text-sm text-white tracking-wide">
              The Atelier
            </h4>
            <ul className="space-y-2.5 text-ivory-light/75 font-light">
              {[
                { name: "About UWEARNOVA", href: "/about" },
                { name: "Contact Sialkot Studio", href: "/contact" },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="inline-block relative py-0.5 group hover:text-white transition-colors duration-fast"
                  >
                    <span>{link.name}</span>
                    <span className="absolute bottom-0 left-0 w-full h-[1px] bg-champagne origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-base ease-out" />
                  </Link>
                </li>
              ))}
              <li>
                <span className="text-ivory-light/40">Headquarters • Sialkot, Punjab, Pakistan</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar: Copyright, Policies & local currency */}
        <div className="pt-8 border-t border-obsidian-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ivory-light/50 font-light">
          <div className="flex flex-wrap items-center gap-4">
            <p>© {new Date().getFullYear()} {BRAND_CONFIG.name}. Modern luxury for Pakistan.</p>
            <span>•</span>
            <Link href="/privacy-policy" className="hover:text-white transition-colors">
              Privacy Policy
            </Link>
            <span>•</span>
            <Link href="/terms" className="hover:text-white transition-colors">
              Terms & Conditions
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <span className="px-3 py-1 rounded-button bg-obsidian-900 border border-obsidian-700 text-champagne-light text-[11px] tracking-wide">
              Currency: PKR (Rs.) • Pakistan
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
