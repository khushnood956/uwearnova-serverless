# UWEARNOVA — Frontend Application

High-performance, luxury fashion e-commerce storefront, administrative command console, and staff operations workspace. Built with **Next.js 15 (App Router)**, **React 19**, **Tailwind CSS**, and **Supabase (PostgreSQL 17 & GoTrue Auth)**.

---

## 1. Architecture & Core Tech Stack

- **Framework:** Next.js 15.1 (Standalone App Router)
- **UI & Reactivity:** React 19, Lucide React, Tailwind CSS v3.4
- **Typography:** Google Fonts (`Cormorant Garamond` serif headlines + `Jost` geometric sans-serif UI/body)
- **Identity & Data:** `@supabase/ssr` & `@supabase/supabase-js`
- **Object Storage:** AWS SDK v3 for Cloudflare R2 presigned uploads
- **Currency & Market:** PKR (`Rs.`) tailored for Pakistan luxury market

---

## 2. Directory Structure

```text
frontend/
├── public/                     # Static assets, SVG luxury logos, favicons, site.webmanifest
├── src/
│   ├── app/                    # Next.js App Router (46 routes)
│   │   ├── (storefront)/       # Public collections, product details, cart, checkout, FAQs, contact
│   │   ├── admin/              # Administrative console
│   │   │   ├── audit-logs/     # Audit trail & system logging
│   │   │   ├── categories/     # Department and category merchandiser
│   │   │   ├── customers/      # Customer directory and order histories
│   │   │   ├── orders/         # Real-time order fulfillment & status workflow
│   │   │   ├── payments/       # Payment records and COD collection tracking
│   │   │   ├── pos/            # Point-of-Sale counter for offline in-store purchases
│   │   │   ├── products/       # Product catalog, variant manager, SKU inventory
│   │   │   ├── returns/        # Exchange and return dispatch queues
│   │   │   ├── settings/       # Dynamic delivery rates, payment method toggles, promo codes, bundles
│   │   │   └── staff/          # Staff provisioning & RBAC role assignments
│   │   ├── staff/              # Operations staff queue (inventory intake, dispatch booking)
│   │   ├── account/            # Customer account portal (orders, addresses, profile)
│   │   ├── api/                # Route handlers (admin user creation, presigned upload URLs)
│   │   ├── auth/callback/      # Supabase OAuth and email verification callback handler
│   │   ├── layout.tsx          # Root layout embedding Cormorant Garamond & Jost font variables
│   │   └── page.tsx            # High-fashion editorial landing page
│   ├── components/             # Reusable UI component library
│   │   ├── auth/               # Modal login/registration with email verification guidance
│   │   ├── cart/               # Persistent cart drawer with free-shipping progress
│   │   ├── checkout/           # Dynamic checkout with promo codes & enabled payment options
│   │   ├── common/             # Skeletons, buttons, inputs, badge components
│   │   ├── home/               # Hero, category grid, editorial campaign, brand story
│   │   ├── layout/             # Header, navbar, announcement bar, footer, storefront shell
│   │   └── product/            # Product cards, gallery, size guide, filter drawers
│   ├── context/                # Client state providers
│   │   ├── AuthContext.tsx     # Supabase session, role synchronization, auto-redirect
│   │   ├── CartContext.tsx     # Shopping bag state with local & server synchronization
│   │   └── WishlistContext.tsx # Customer wishlist state
│   ├── lib/                    # Core libraries and APIs
│   │   ├── api/                # Modular PostgREST & RPC client services
│   │   ├── brand.ts            # Canonical brand constants, contacts, social links
│   │   └── supabase/           # Browser, server, admin, and middleware Supabase clients
│   └── middleware.ts           # Ultra-fast Next.js Edge Middleware for role-based portal isolation
├── package.json                # Project dependencies and build scripts
├── tailwind.config.ts          # Luxury color palette (obsidian, champagne, ivory, sand)
└── tsconfig.json               # Strict TypeScript configuration
```

---

## 3. Role-Based Portal Isolation

The application enforces **strict portal isolation** at both the server edge (`middleware.ts`) and client hydration layer (`StorefrontLayoutShell.tsx`):

1. **Super Admin (`super_admin`) & Store Admin (`store_admin`):**
   - Full access to `/admin` management portals.
   - Any attempt to browse public shopping pages (`/`, `/collections`, etc.) is immediately redirected (`HTTP 307`) to `/admin`.
   - Only `admin1@uwearnova.com` (Super Admin) can provision additional Super Admin accounts.
2. **Operations Staff (`staff`):**
   - Direct access to `/staff`, `/admin/pos` (in-store counter), and `/admin/products` (inventory).
   - Any attempt to browse the customer storefront is immediately redirected to `/staff`.
3. **Customers (`customer`) & Guests:**
   - Full access to the public shopping storefront.
   - Administrative and staff portals are strictly inaccessible.

---

## 4. Dynamic Rates & Store Settings

Store settings are dynamically managed from `/admin/settings` and cached in memory with zero database schema bottlenecks:
- **Delivery Fee:** Dynamically adjustable (e.g. Rs. 200 vs Rs. 350) and immediately reflected in customer checkout and shipping calculation.
- **Payment Methods:** Toggle Cash on Delivery (COD), Online Card, or Bank Transfer. Unchecked payment methods are automatically hidden from customer checkout.
- **Promo Codes & Vouchers:** Create discount codes (fixed PKR or percentage) with validity periods and minimum order criteria.
- **Curated Bundles:** Configure bundle offers and promotional package discounts.

---

## 5. Development & Build

### Prerequisites
- Node.js >= 20.0.0
- npm >= 10.0.0

### Local Development
```bash
# Install dependencies
npm install

# Start development server with Turbopack
npm run dev -- --turbo
```

### Production Build
```bash
# Verify TypeScript, lint, and generate static pages
npm run build

# Start production server
npm run start
```

---

## 6. Environment Variables

Create `.env.local` inside `frontend/`:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Cloudflare R2 Media Storage
R2_ACCOUNT_ID=<your-account-id>
R2_ACCESS_KEY_ID=<your-access-key-id>
R2_SECRET_ACCESS_KEY=<your-secret-key>
R2_BUCKET_NAME=uwearnova
NEXT_PUBLIC_R2_PUBLIC_DOMAIN=https://<your-r2-domain>
```
