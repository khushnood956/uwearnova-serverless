/**
 * Brand Configuration for UWEARNOVA Fashion E-Commerce
 * Brand: UWEARNOVA
 * Market: Pakistan (PKR currency)
 */

export const BRAND_CONFIG = {
  name: "UWEARNOVA",
  tagline: "A New Dimension of Style",
  description: "Refined, contemporary fashion clothing, footwear and accessories designed for modern elegance.",
  currency: {
    code: "PKR",
    symbol: "Rs.",
    label: "PKR",
  },
  freeShippingThreshold: 3500, // PKR 3,500 free shipping
  contact: {
    email: "info@uwearnova.com",
    phone: "+92 319 1772713",
    supportHours: "Mon - Sat: 10:00 AM - 8:00 PM PKT",
    location: "Sialkot, Punjab, Pakistan",
  },
  socials: {
    instagram: "https://instagram.com",
    facebook: "https://facebook.com",
    tiktok: "https://tiktok.com",
    whatsapp: "https://wa.me/923191772713",
  },
  navigation: [
    { name: "Men", href: "/collections/men" },
    { name: "Women", href: "/collections/women" },
    { name: "Footwear", href: "/collections/footwear" },
    { name: "Accessories", href: "/collections/accessories" },
    { name: "New Arrivals", href: "/collections/new-arrivals" },
  ],
} as const;

export function formatPKR(amount: number): string {
  return `Rs. ${amount.toLocaleString("en-PK")}`;
}
