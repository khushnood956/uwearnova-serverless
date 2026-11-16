import type { Metadata, Viewport } from "next";
import { BRAND_CONFIG } from "@/lib/brand";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { CartDrawer } from "@/components/cart/CartDrawer";
import { AuthModal } from "@/components/auth/AuthModal";
import { AuthProvider } from "@/context/AuthContext";
import { CartProvider } from "@/context/CartContext";
import { WishlistProvider } from "@/context/WishlistContext";
import { SkipToContent } from "@/components/common/SkipToContent";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: `${BRAND_CONFIG.name} | ${BRAND_CONFIG.tagline}`,
    template: `%s | ${BRAND_CONFIG.name}`,
  },
  description: BRAND_CONFIG.description,
  keywords: [
    "fashion",
    "pakistan fashion",
    "luxury apparel",
    "designer clothing",
    "footwear",
    "accessories",
    "contemporary style",
  ],
  authors: [{ name: BRAND_CONFIG.name }],
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
  manifest: "/site.webmanifest",
  openGraph: {
    title: `${BRAND_CONFIG.name} | ${BRAND_CONFIG.tagline}`,
    description: BRAND_CONFIG.description,
    type: "website",
    locale: "en_PK",
  },
};

export const viewport: Viewport = {
  themeColor: "#14120F",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col font-sans antialiased bg-ivory text-obsidian selection:bg-champagne/30 selection:text-obsidian">
        <AuthProvider>
          <CartProvider>
            <WishlistProvider>
              <SkipToContent />
              <Header />
              <div id="main-content" className="flex-1 flex flex-col focus:outline-none">
                {children}
              </div>
              <Footer />
              <CartDrawer />
              <AuthModal />
            </WishlistProvider>
          </CartProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
