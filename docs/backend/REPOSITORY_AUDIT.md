# UniNova — M00 Repository & Architecture Audit Report

**Date:** November 10, 2026  
**Auditor:** Antigravity (AI Engineering Agent)  
**Status:** Completed & Verified  
**Scope:** Repository structure, Next.js frontend state, data types, runtime environments, backend presence check, and AWS hosting architecture recommendation.

---

## 1. Executive Summary

This repository audit represents the verified current-state analysis of the UniNova codebase prior to backend scaffolding and full-stack integration. 

Key verified findings:
1. **Frontend State:** A fully functional, responsive, statically pre-rendered Next.js 15 (App Router) storefront with 33 verified static routes. The recent UI overhaul (Cormorant Garamond/Inter typography, centralized luxury tokens, 0 `transition-all` instances, balanced product grids) was confirmed directly against source code and production build output.
2. **Backend Existence:** **Zero** backend code currently exists. There are no Python files, Dockerfiles, docker-compose configurations, database schemas, or API routes in the repository.
3. **Data & State Architecture:** All catalog data is hardcoded in TypeScript arrays (`src/data/products.ts`, `src/data/categories.ts`). Cart and wishlist states are stored in browser `localStorage`. Checkout generates simulated client-side order IDs (`UNV-XXXXXX`) stored in `sessionStorage`.
4. **Local Runtime Readiness:** Python 3.14.6, pip 26.2.1, Docker 28.3.3, Node v24.18.0, npm 11.16.0, and Git 2.54.0 are installed and available in the environment.
5. **AWS Compute Recommendation:** Amazon ECS on AWS Fargate for the FastAPI container; Amazon RDS for MySQL 8.0 in a private VPC subnet; Amazon S3 + CloudFront for product media; and evaluation of Next.js standalone container on ECS vs. AWS Amplify Hosting for the frontend.

---

## 2. Repository Structure & Documentation Separation

The repository is organized cleanly with strict separation between frontend specifications and backend blueprints:

```text
E:\website\
├── package.json                                         # Frontend manifest (Next.js 15, React 19)
├── tsconfig.json                                        # TypeScript 5.7 configuration
├── next.config.mjs                                      # Security headers, remote image patterns
├── tailwind.config.ts                                   # Design tokens, fluid clamp typography
├── postcss.config.mjs
├── fashion_ecommerce_concept_brief_performance_focused.md # [FRONTEND] Original concept brief
├── IMPLEMENTATION_PLAN.md                               # [FRONTEND] Modules 1–14 tracker
├── AGENT_BACKEND_INSTRUCTIONS.md                        # [BACKEND] Master execution prompt
├── docs/
│   └── backend/                                         # [BACKEND] Blueprint documentation
│       ├── README.md
│       ├── 01-backend-architecture.md
│       ├── 02-database-design.md
│       ├── 03-dashboards-and-rbac.md
│       ├── 04-api-contract.md
│       ├── 05-aws-deployment.md
│       ├── 06-implementation-plan.md
│       └── REPOSITORY_AUDIT.md                          # [THIS AUDIT]
├── src/                                                 # Frontend source code
│   ├── app/                                             # Next.js App Router pages
│   ├── components/                                      # UI, common, layout, cart, checkout
│   ├── context/                                         # CartContext, WishlistContext
│   ├── data/                                            # Mock catalog and category data
│   ├── lib/                                             # Brand config, utilities
│   └── types/                                           # TypeScript interfaces
└── uninova_backend_blueprint/                           # Source blueprint archive
```

---

## 3. Frontend Architecture & Runtimes

- **Framework:** Next.js `15.1.0` (App Router)
- **UI Library:** React `19.0.0`, React DOM `19.0.0`
- **Language / Compiler:** TypeScript `5.7.2`
- **Styling:** Tailwind CSS `3.4.16`, Autoprefixer `10.4.20`, PostCSS `8.4.49`
- **Icons:** `lucide-react` `0.468.0`
- **Utilities:** `clsx` `2.1.1`, `tailwind-merge` `2.5.5`
- **Scripts Configured:**
  - `npm run dev`: `next dev`
  - `npm run build`: `next build`
  - `npm run start`: `next start`
  - `npm run lint`: `next lint`

### Route Inventory & Pre-rendering Audit

Every route is confirmed to build statically into static HTML (`○ Static` or `● SSG`):

| Route Path | Type | File Path | Notes |
|---|---|---|---|
| `/` | Static | `src/app/page.tsx` | Homepage: Hero, Categories, Trending, Campaign, Collections, Brand Story |
| `/_not-found` | Static | `src/app/not-found.tsx` | Custom 404 luxury error page |
| `/about` | Static | `src/app/about/page.tsx` | Atelier story, 4-stat bar, drop cap, pull-quote |
| `/cart` | Static | `src/app/cart/page.tsx` | Cart review, shipping threshold, COD notice |
| `/checkout` | Static | `src/app/checkout/page.tsx` | Shipping address, payment selection, COD notice |
| `/checkout/success` | Static | `src/app/checkout/success/page.tsx` | Receipt display reading `uninova_last_order` |
| `/collections/[category]` | SSG (10 paths) | `src/app/collections/[category]/page.tsx` | `all`, `men`, `women`, `footwear`, `accessories`, `new-arrivals`, `essentials`, `signature`, `trending`, `sale` |
| `/contact` | Static | `src/app/contact/page.tsx` | Atelier on obsidian ink, contact form on ivory |
| `/faqs` | Static | `src/app/faqs/page.tsx` | 2-column layout with sticky concierge sidebar |
| `/product/[slug]` | SSG (10 paths) | `src/app/product/[slug]/page.tsx` | 10 products with gallery, variant selector, accordion |
| `/returns-exchanges` | Static | `src/app/returns-exchanges/page.tsx` | 7-day doorstep exchange policy & 3-step timeline |
| `/shipping-delivery` | Static | `src/app/shipping-delivery/page.tsx` | Dispatch timelines, free shipping threshold, COD info |
| `/wishlist` | Static | `src/app/wishlist/page.tsx` | Wishlisted product grid and empty state |

Total routes: **33 static pages**. Verified with `npm run build` exiting with code 0.

---

## 4. Verification of UI State & Code Quality

The code was inspected to confirm that recent UI overhaul fixes are in place:
1. **Fonts & Typography:** `Cormorant_Garamond` (`--font-serif`) and `Inter` (`--font-sans`) are properly initialized via `next/font/google` in `src/app/layout.tsx`. Tailwind `fontFamily` maps directly to these variables with reliable serif/sans fallbacks.
2. **Transition Rules:** Grep for `transition-all` returns **0 occurrences** across the codebase. All transitions animate composite properties (`transform`, `opacity`, `background-color`, `border-color`, `color`).
3. **Touch Targets:** The disruptive `@media (pointer: coarse)` global minimum size rule was removed from `globals.css`. Touch targets are explicitly managed on buttons and inputs.
4. **Grid Alignment:** `ProductGrid.tsx` enforces `grid-cols-2 lg:grid-cols-4`, resolving the 3+1 orphan card defect on tablet breakpoints.
5. **Color Palette:** Centralized tokens in `tailwind.config.ts` (`ivory`, `sand`, `obsidian`, `champagne`, `sale`, `success`, `danger`). Off-palette amber and emerald hardcoded colors have been eliminated.

---

## 5. Current Data Models & Client-Side API Assumptions

### Catalog Data (`src/types/product.ts`, `src/data/products.ts`)
- 10 hardcoded products across 4 categories: `men` (3), `women` (3), `footwear` (2), `accessories` (2).
- Each product defines `ProductVariant` entries with `sku`, `size`, `color`, `colorHex`, `inStock`, and `inventoryCount`.
- Prices are stored as numbers in PKR (e.g. `14500`).
- Collections: `new-arrivals`, `essentials`, `signature`, `trending`, `sale`.

### Cart & Wishlist State (`src/context/CartContext.tsx`, `src/context/WishlistContext.tsx`)
- Cart items are stored in `localStorage` under key `uninova_cart_v1`.
- Line items are keyed as `${product.id}-${variant.sku}`.
- Subtotal, shipping threshold (PKR 5,000), and free shipping calculations are executed purely in the client browser.
- Wishlist stores product ID strings in `localStorage` under `uninova_wishlist_v1`.

### Checkout State (`src/components/checkout/CheckoutForm.tsx`)
- Form collects `fullName`, `email`, `phone`, `address`, `city`, `postalCode`, `paymentMethod` (`cod` | `card` | `wallet`), and optional `notes`.
- Submission does not communicate with a server. It generates `UNV-${Math.floor(100000 + Math.random() * 900000)}`, clears the cart, writes order JSON to `sessionStorage.setItem("uninova_last_order", ...)`, and redirects to `/checkout/success`.

### Necessary Backend Translations (Phases 1–5)
- **Monetary Precision:** The frontend uses JS floating-point numbers (`number`). The backend must use `Decimal` for all pricing and pass decimal-safe string or structured numeric representation to the frontend.
- **Server-Authoritative Pricing:** The frontend currently calculates shipping and discounts locally. In production, checkout quotes and order line item totals must be recalculated and validated server-side.
- **Guest vs. Customer Cart:** Cart state needs a migration path: anonymous guest carts merged with authenticated customer accounts upon sign-in.
- **Stock Reservations:** Current client decrements zero inventory on checkout; the backend must manage transactional stock deductions and reservations.

---

## 6. Backend Existence Check

An audit of the entire filesystem confirms:
- **Python:** No Python files (`.py`) exist in the repository.
- **Docker:** No `Dockerfile` or `docker-compose.yml` exists.
- **Database / Migrations:** No MySQL scripts, SQLite databases, or Alembic configuration (`alembic.ini`) exist.
- **API Endpoints:** No Next.js API routes (`src/app/api/*`) or external backend services exist.

**Conclusion:** The backend is starting from a clean slate. Scaffolding must be executed under a dedicated `backend/` directory in Phase 1 (M02).

---

## 7. Local Development Environments

The local host environment was checked and verified:
- **Python:** Python `3.14.6`, pip `26.2.1`
- **Docker:** Docker `28.3.3` (build `980b856`)
- **Node.js:** Node.js `v24.18.0`, npm `11.16.0`
- **Git:** Git `2.54.0.windows.1`

*Note regarding Python 3.14:* Python 3.14 is very modern. During M02/M03 dependency selection, we will verify compatibility of C-extensions / compiled wheels (such as `asyncmy` or `cryptography`) or select proven pure-Python / universally compatible libraries for FastAPI and SQLAlchemy.

---

## 8. AWS Hosting & Compute Recommendation

Per the blueprint guidelines, we recommend the least-complex, production-grade AWS architecture compatible with Next.js 15 App Router and FastAPI:

```text
                                  Clients (Web / Mobile)
                                            │
                                            ▼
                           Route 53 + ACM (Custom Domain & SSL)
                                            │
                                            ▼
                            CloudFront (Global CDN Distribution)
                     ┌──────────────────────┴──────────────────────┐
                     │ /api/*, /docs, /health                      │ /* (Storefront)
                     ▼                                             ▼
        Application Load Balancer (ALB)                   Next.js Storefront
                     │                                (Standalone Docker on ECS
                     ▼                                 or AWS Amplify Hosting)
        Amazon ECS on AWS Fargate
          (FastAPI Modular Monolith)
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
Amazon RDS for MySQL          Amazon S3
 (Private VPC Subnet,      (Product & Asset
 Multi-AZ in Production)     Media Storage)
```

### Recommendation Details

1. **Backend Compute (FastAPI):**
   - **Recommendation:** **Amazon ECS on AWS Fargate**.
   - **Rationale:** Serverless container execution eliminates EC2 management overhead while supporting long-lived connections, predictable startup times, and seamless Docker parity between local development and production.
2. **Database (MySQL):**
   - **Recommendation:** **Amazon RDS for MySQL 8.0** deployed in private VPC subnets with automated daily snapshots and KMS encryption at rest.
3. **Product Media Storage:**
   - **Recommendation:** **Amazon S3** with private access bucket policy, using presigned upload URLs for admin media management, served publicly via CloudFront with caching headers.
4. **Frontend Hosting (Next.js 15 + React 19):**
   - **Primary Recommendation:** Containerized Next.js standalone server deployed on **Amazon ECS Fargate** behind the same CloudFront distribution as the API.
   - **Alternative:** **AWS Amplify Hosting Gen 2** (subject to verification of React 19 / Next.js 15 build image support in the selected AWS region).
   - **Rationale:** Using ECS for both frontend and backend provides identical deployment primitives, zero vendor-lockin risk, unified CloudWatch logging, and straightforward private networking.

---

## 9. Phase 0 Verification & Next Steps

Module **M00 (Repository and architecture audit)** is complete. No application code was altered.

**Next Immediate Module:**
- **M01 (Documentation and workspace setup):** Ensure backend documentation, environment examples (`.env.example`), and project boundary definitions are formalized before beginning M02 (Backend project scaffold).
