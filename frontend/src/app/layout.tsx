import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond, Jost } from "next/font/google";
import { BRAND_CONFIG } from "@/lib/brand";
import { StorefrontLayoutShell } from "@/components/layout/StorefrontLayoutShell";
import { AuthProvider } from "@/context/AuthContext";
import { CartProvider } from "@/context/CartContext";
import { WishlistProvider } from "@/context/WishlistContext";
import "./globals.css";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

const jost = Jost({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

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
  authors: [
    { name: BRAND_CONFIG.name },
    { name: "Khushnood Ahmad", url: "https://khushnood956.github.io/Portfolio" },
  ],
  creator: "Khushnood Ahmad",
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
    <html lang="en" className={`${cormorant.variable} ${jost.variable}`}>
      <body className="min-h-screen flex flex-col font-sans antialiased bg-ivory text-obsidian selection:bg-champagne/30 selection:text-obsidian">
        <AuthProvider>
          <CartProvider>
            <WishlistProvider>
              <StorefrontLayoutShell>{children}</StorefrontLayoutShell>
            </WishlistProvider>
          </CartProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
