# UWEARNOVA — Luxury Fashion E-Commerce Serverless Platform

[![Next.js 15](https://img.shields.io/badge/Next.js-15.1.0-black?logo=next.js)](https://nextjs.org/)
[![React 19](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL%2017-3ECF8E?logo=supabase)](https://supabase.com/)
[![Cloudflare R2](https://img.shields.io/badge/Cloudflare-R2%20Storage-F38020?logo=cloudflare)](https://developers.cloudflare.com/r2/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v3.4-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)

A modern, high-performance, serverless luxury fashion e-commerce platform built for **UWEARNOVA**. Engineered with **Next.js 15 Standalone App Router**, **Supabase (PostgreSQL 17, GoTrue Auth, ACID Stored Procedures, Row Level Security)**, and **Cloudflare R2** (S3-compatible zero-egress media storage).

---

## 1. System Architecture

```text
                                [ User / Web Browser ]
                                          │
                        ┌─────────────────┴─────────────────┐
                        │                                   │
                        ▼                                   ▼
             [ Storefront & Admin ]               [ Direct Media Upload ]
             Next.js 15 Standalone App            S3v4 Presigned PUT (0ms server load)
             Edge SSR / React 19 RSC                       │
                        │                                   ▼
                        │ PostgREST / RPC       [ Cloudflare R2 Storage ]
                        ▼                       - Global Edge CDN
         [ Supabase PostgreSQL 17 ]             - Zero Egress Bandwidth Fees
         - GoTrue Authentication                - 11 9's Data Durability
         - Row-Level Security (RLS)
         - ACID Transactional Checkout (place_order_atomic)
         - Automated Real-time Sales Reporting Views
```

---

## 2. Key Platform Features

- **Storefront & Curated Collections:**
  - Multi-tier luxury department navigation (Men, Women, Kids, Footwear, Accessories, Perfumes).
  - High-performance, latency-optimized catalog browsing with parallelized queries and in-memory taxonomy caching.
  - Persistent shopping bag, curated wishlist, instant search modal, and responsive filter drawers.
  - Nationwide delivery calculation and authoritatively verified pricing.

- **Cash on Delivery (COD) & ACID Transactional Commerce:**
  - Guaranteed stock reservation via Postgres atomic RPC (`place_order_atomic`) preventing race conditions or overselling.
  - Reliable COD order state machine: orders transition seamlessly through `placed`, `confirmed`, `dispatched`, `delivered`, and `paid`.
  - Doorstep 7-day complimentary exchanges and returns workflow.

- **Administrative Console & Staff Ecosystem:**
  - **Store Management (`/admin`):** Executive sales reporting, catalog merchandiser, inline subcategory manager, and order processing.
  - **Point-of-Sale (POS) Terminal (`/admin/pos`):** Fast in-store cashier terminal with quick barcodes, instant cart manipulation, and automated receipt generation.
  - **Staff Workspaces (`/staff`):** Role-tailored queues for dispatch packing, warehouse inventory intake, and customer support.
  - **Customer Sanctuary (`/account`):** Live consignment tracking, address book management, order history, and security preferences.

- **Remote Latency & Navigation Optimizations:**
  - **Next.js Middleware Prefetch Fast-Path:** Instant bypass on `<Link>` prefetch requests (`purpose: prefetch`), eliminating 300ms round-trips to remote databases on link hover.
  - **Anonymous Fast-Path:** Zero network overhead for visitors browsing public storefront pages.
  - **React `cache()` Request Deduplication:** Single-roundtrip data sharing across metadata generation and page components.
  - **Instant Skeletons (`loading.tsx`):** 0ms perceived route transition latency with champagne-bone shimmering skeletons across all route groups.

---

## 3. Repository Structure

```text
uwearnova-serverless/
├── frontend/                     # Next.js 15 App Router Application
│   ├── src/
│   │   ├── app/                  # App Router Pages, Routes, & Loading Skeletons
│   │   ├── components/           # Luxury UI, Product, Cart, Admin, & Layout Components
│   │   ├── context/              # AuthContext, CartContext, WishlistContext
│   │   ├── lib/                  # Supabase clients (client, server, admin), Brand config
│   │   │   ├── api/              # Direct PostgREST & RPC callers (11 modules)
│   │   │   ├── storage/          # Cloudflare R2 S3v4 client helper
│   │   │   └── supabase/         # Server client, Middleware helper, React cache()
│   │   └── middleware.ts         # High-performance Next.js Edge Middleware
│   ├── public/                   # Vector logos, favicons, webmanifest
│   └── package.json              # Next.js dependencies & scripts
├── supabase/                     # Supabase PostgreSQL Foundation
│   ├── migrations/               # Version-controlled SQL migrations (Schema, RBAC, RPCs)
│   ├── seed.sql                  # Canonical seed data & verified inventory
│   └── tests/                    # RLS security verification suite
├── docs/                         # Migration documentation (Stages 0 through 10)
├── scripts/                      # Migration, verification, and seed automation scripts
├── archive/                      # Retired legacy backend manifest
├── package.json                  # Root proxy scripts for automated deployment
└── vercel.json                   # Vercel deployment configuration
```

---

## 4. Environment Configuration

To configure production or staging environments, supply the following environment variables:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-id>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Cloudflare R2 Object Storage
R2_ACCOUNT_ID=<your-cloudflare-account-id>
R2_ACCESS_KEY_ID=<your-r2-access-key-id>
R2_SECRET_ACCESS_KEY=<your-r2-secret-access-key>
R2_BUCKET_NAME=uwearnova
NEXT_PUBLIC_R2_PUBLIC_DOMAIN=https://<your-r2-public-domain>

# Storefront Brand Identity
NEXT_PUBLIC_STORE_NAME=UWEARNOVA
NEXT_PUBLIC_STORE_EMAIL=info@uwearnova.com
NODE_ENV=production
```

---

## 5. Deployment Instructions

### Deploy to Vercel (1-Click Ready)
1. Import this repository into Vercel.
2. If prompted, set **Root Directory** to `frontend` (or leave default root with `vercel.json`).
3. Add the environment variables listed above.
4. Deploy! Next.js Standalone build will compile automatically.

### Deploy to Cloudflare Pages
1. Create a new Cloudflare Pages project connected to this repository.
2. Build command: `npm --prefix frontend run build` (or `npx @cloudflare/next-on-pages`).
3. Output directory: `frontend/.next` (or `.vercel/output/static`).
4. Configure environment variables in project settings.

---

## 6. Default Administrative & Staff Accounts

The platform comes pre-configured with 6 role-based staff accounts in live Supabase Auth:

| Role Title | Account Email | Initial Credentials | Primary Workstation |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin1@uwearnova.com` | `Admin@UwearNova2026!` | `/admin` (Full System Control) |
| **Store Admin** | `admin2@uwearnova.com` | `Admin@UwearNova2026!` | `/admin` (Catalog, Orders, Analytics) |
| **POS Cashier** | `sales1@uwearnova.com` | `Staff@UwearNova2026!` | `/admin/pos` & `/staff` (Point-of-Sale) |
| **Order Fulfillment** | `sales2@uwearnova.com` | `Staff@UwearNova2026!` | `/admin/orders` & `/staff` (Fulfillment) |
| **Warehouse Manager** | `inventory1@uwearnova.com` | `Staff@UwearNova2026!` | `/admin/products` & `/staff` (Inventory) |
| **Merchandiser** | `inventory2@uwearnova.com` | `Staff@UwearNova2026!` | `/admin/products/new` (Catalog) |

---

## 7. License & Credits

Copyright © 2026 UWEARNOVA. All rights reserved.
Developed for luxury fashion commerce with zero-serverful, modern web standards.
