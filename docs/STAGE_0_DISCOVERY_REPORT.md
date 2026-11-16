# Stage 0 — Read-Only Discovery Report

**Workspace:** `E:\UWearNova`  
**Date:** 2026-11-16  
**Status:** Stage 0 complete. Awaiting approval before Stage 1.  

> [!IMPORTANT]
> This report was produced entirely from static inspection. No code was changed, no packages were installed, no migrations were run, no cloud resources were created, and no DNS changes were made.

---

## 1. Repository & Git Status

| Property | Value |
|---|---|
| Path | `E:\UWearNova` |
| `.git` directory present | Yes |
| Branch | `master` |
| Commits | **0** (all files untracked) |
| Remotes | None configured |
| Working tree | All files show as `??` (untracked) |

**Implication:** No commit history to preserve. The entire workspace is a copy of `E:\website` with docs added. A proper initial commit should be the first action in Stage 1.

---

## 2. Verified Framework & Runtime Versions

### Frontend (`frontend/package.json`)

| Dependency | Declared Version | Role |
|---|---|---|
| Next.js | `^15.1.0` | Framework |
| React | `^19.0.0` | UI library |
| React DOM | `^19.0.0` | DOM renderer |
| TypeScript | `^5.7.2` | Type system |
| Tailwind CSS | `^3.4.16` | Styling |
| clsx | `^2.1.1` | Class merging |
| lucide-react | `^0.468.0` | Icons |
| tailwind-merge | `^2.5.5` | Tailwind dedup |
| Lockfile | `package-lock.json` (npm) | Present |

No other dependencies (no `@supabase/ssr`, no `next-auth`, no state management library, no form library).

### Backend (`backend/requirements.txt` + `backend/pyproject.toml`)

| Dependency | Version Constraint | Role |
|---|---|---|
| FastAPI | `>=0.115.0` | HTTP framework |
| Uvicorn[standard] | `>=0.32.0` | ASGI server |
| Pydantic | `>=2.10.0` | Schema validation |
| pydantic-settings | `>=2.6.0` | Env config |
| SQLAlchemy[asyncio] | `>=2.0.36` | ORM |
| Alembic | `>=1.14.0` | Migrations |
| PyMySQL | `>=1.1.1` | Sync MySQL driver |
| aiomysql | `>=0.2.0` | Async MySQL driver |
| argon2-cffi | `>=23.1.0` | Password hashing |
| PyJWT | `>=2.9.0` | Token signing |
| boto3 | `>=1.35.0` | AWS S3 client |
| email-validator | `>=2.2.0` | Email format validation |
| httpx | `>=0.28.0` | HTTP client |
| python-multipart | `>=0.0.12` | Form data (in requirements.txt only, missing from pyproject.toml) |
| greenlet | `>=3.1.0` | SQLAlchemy async support |
| cryptography | `>=43.0.0` | PyMySQL SSL |
| Python | `>=3.11` | Runtime |
| Docker base image | `python:3.12` | Container runtime |

**Known issue:** `python-multipart` is in `requirements.txt` but omitted from `pyproject.toml` dependencies. This causes `RuntimeError: Form data requires "python-multipart"` when running tests via pyproject.toml-based installs.

---

## 3. Project Structure

```
E:\UWearNova/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/             # Router aggregator + health endpoint
│   │   ├── common/             # Error handlers
│   │   ├── core/               # Config, database, security, logging, models, base
│   │   └── modules/            # 19 domain modules (see §4)
│   ├── migrations/             # Alembic migrations (19 revisions)
│   │   └── versions/
│   ├── tests/
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                   # Next.js application
│   ├── src/
│   │   ├── app/                # App Router (28 pages, 3 layouts)
│   │   ├── components/         # 33 React components
│   │   ├── context/            # Auth, Cart, Wishlist providers
│   │   ├── data/               # Static fallback data
│   │   ├── lib/                # API client, utils, brand config
│   │   └── types/              # TypeScript type definitions
│   ├── public/
│   ├── next.config.mjs
│   ├── package.json
│   ├── package-lock.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── docs/                       # Migration guide + existing audit
├── infra/terraform/            # AWS ECS/RDS/S3/CloudFront IaC (not deployed)
├── .github/workflows/          # CI/CD: ci, deploy-production, deploy-staging, gh-pages
├── logo/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

> [!NOTE]
> In this workspace the frontend lives under `frontend/` (with its own `package.json`), unlike `E:\website` where frontend files sit at the project root.

---

## 4. FastAPI Endpoint Inventory

**20 backend modules**, **208 route-decorated endpoints** total (regex count of `@router.{method}(` patterns):

| Module | Endpoints | Prefix Pattern | Auth Required |
|---|---:|---|---|
| auth | 8 | `/auth/*` | Mixed (register/login public, rest authenticated) |
| catalog | 31 | `/categories/*`, `/collections/*`, `/products/*`, `/admin/categories/*`, `/admin/collections/*`, `/admin/products/*` | Public (storefront), Staff (admin) |
| cart | 10 | `/cart/*`, `/wishlist/*` | Customer + Anonymous (cart token) |
| customer | 20 | `/customer/*`, `/admin/customers/*` | Customer, Staff |
| staff | 22 | `/staff/*` | Staff only |
| content | 16 | `/content/*`, `/admin/content/*` | Public + Staff |
| payments | 15 | `/payments/*`, `/admin/payments/*`, `/customer/payments/*` | Mixed |
| orders | 13 | `/orders/*`, `/admin/orders/*`, `/customer/orders/*` | Mixed |
| inventory | 11 | `/admin/inventory/*` | Staff |
| returns | 11 | `/returns/*`, `/admin/returns/*`, `/customer/returns/*` | Mixed |
| fulfillment | 9 | `/fulfillment/*`, `/admin/fulfillment/*`, `/customer/fulfillment/*` | Mixed |
| media | 8 | `/admin/media/*`, `/admin/products/*/media/*` | Staff |
| shipping | 8 | `/shipping/*`, `/admin/shipping/*` | Public + Staff |
| promotions | 7 | `/promotions/*`, `/admin/promotions/*` | Public + Staff |
| reports | 7 | `/admin/reports/*` | Staff |
| reviews | 4 | `/reviews/*`, `/admin/reviews/*` | Public + Staff |
| offline_sales | 4 | `/admin/offline-sales/*` | Staff |
| rbac | 3 | `/admin/rbac/*` | Admin |
| audit | 1 | `/admin/audit-logs` | Admin |

---

## 5. SQLAlchemy Model / Table Inventory

**47 tables** across 18 model files (+ 2 association tables from RBAC = ~49 total table names):

| Module | Tables | Table Names |
|---|---:|---|
| auth | 3 | `users`, `refresh_tokens`, `password_resets` |
| catalog | 5 | `categories`, `collections`, `products`, `product_variants`, `product_images` (+ `product_collections` association) |
| rbac | 2 + 2 assoc | `roles`, `permissions`, `role_permissions`, `user_roles` |
| cart | 4 | `carts`, `cart_items`, `wishlists`, `wishlist_items` |
| orders | 4 | `orders`, `order_items`, `order_status_history`, `checkout_sessions` |
| payments | 4 | `payments`, `payment_transactions`, `payment_events`, `refunds` |
| inventory | 3 | `inventory_items`, `inventory_movements`, `stock_reservations` |
| shipping | 2 | `shipping_methods`, `shipping_rates` |
| fulfillment | 3 | `shipments`, `shipment_items`, `tracking_events` |
| customer | 2 | `customer_profiles`, `addresses` |
| returns | 2 | `return_requests`, `return_items` |
| reviews | 1 | `product_reviews` |
| content | 3 | `content_pages`, `banners`, `faqs` |
| promotions | 2 | `coupons`, `coupon_usage` |
| staff | 4 | `staff_profiles`, `staff_assignments`, `work_queues`, `support_tickets` |
| audit | 1 | `audit_logs` |
| offline_sales | 2 | `offline_sales`, `offline_sale_items` |

### Alembic Migration Chain (19 revisions, linear)

```
1b97deaf6b37  baseline_schema                         (2026-11-10)
    └─ f65b9f41043f  identity_and_auth_tables
        └─ 3d8042914983  rbac_and_audit_tables
            └─ 19b855e08445  categories_and_collections
                └─ d4fc55d592df  products_variants_images
                    └─ eb987fbddf47  product_media_metadata_columns
                        └─ 05ed229b0f54  inventory_tables
                            └─ 79afb81abaa2  cart_and_wishlist_tables
                                └─ 61e5fd2f0ee5  shipping_tables
                                    └─ cdade44decfd  orders_and_checkout_tables
                                        └─ 16d42444d379  payments_and_transactions
                                            └─ 073a8073cb18  payment_events_and_refunds
                                                └─ 71ea9085ba8d  fulfillment_and_shipments
                                                    └─ eb3475f7833b  returns_and_return_items
                                                        └─ 9f41b238d81c  customer_profiles_and_addresses
                                                            └─ a84e207b92cd  staff_operations_and_support
                                                                └─ b39e318cf142  promotions_reviews_content
                                                                    └─ c10d3e5a7b9f  add_is_coming_soon_to_categories
                                                                        └─ d2e5a6f8b901  offline_sales  (HEAD)
```

All migrations path: `backend/migrations/versions/`

---

## 6. Authentication & RBAC Inventory

### Authentication Flow

| Component | Implementation |
|---|---|
| Password hashing | Argon2id (time_cost=3, memory_cost=64MB, parallelism=4, hash_len=32, salt_len=16) |
| Token signing | HS256 JWT via PyJWT |
| Access token lifetime | 30 minutes (default) |
| Refresh token | Stored as SHA-256 hash in `refresh_tokens` table, 14-day expiry |
| Token storage (frontend) | `sessionStorage` (access), `localStorage` (refresh) |
| Token rotation | Refresh endpoint rotates token, old one revoked |
| Account lockout | `failed_login_attempts` counter + `locked_until` timestamp |
| Email verification | `email_verified_at` column exists, but no verification flow endpoint |
| Password reset | Token created and stored (SHA-256 hashed), but **no email dispatch** |

### RBAC Structure

- **Tables:** `roles`, `permissions`, `role_permissions` (M2M), `user_roles` (M2M)
- **Permission model:** Granular codes like `products.create`, `orders.read` with categories
- **Role assignment:** Users ↔ Roles via `user_roles`, Roles ↔ Permissions via `role_permissions`
- **System roles:** `is_system` flag prevents deletion of built-in roles
- **User types:** `customer`, `staff`, `admin` (column on `users` table)
- **Roles eager-loaded:** `lazy="selectin"` on User.roles relationship

### JWT Claims

```json
{
  "sub": "<user_id>",
  "user_type": "customer|staff|admin",
  "iat": <unix_timestamp>,
  "exp": <unix_timestamp>,
  "type": "access"
}
```

**Note:** Roles/permissions are NOT embedded in JWT claims. They are loaded from the database on each request via the `get_current_user` dependency.

---

## 7. Frontend Route & API-Call Inventory

### Pages (28 routes)

| Route | Purpose | Backend Dependencies |
|---|---|---|
| `/` | Homepage | `catalogApi.getProducts()`, `catalogApi.getCategoryTree()` |
| `/collections/[category]` | Category listing | `catalogApi.getProducts()`, `catalogApi.getCategory()` |
| `/product/[slug]` | Product detail | `catalogApi.getProductBySlug()` |
| `/cart` | Shopping cart | `cartApi.getCart()`, cart mutations |
| `/wishlist` | Wishlist | `cartApi.getWishlist()`, wishlist mutations |
| `/checkout` | Checkout form | `ordersApi.checkout()`, `shippingApi.*` |
| `/checkout/success` | Order confirmation | `ordersApi.getOrder()` |
| `/account` | Customer account | `customerApi.getProfile()`, orders, addresses, returns |
| `/staff` | Staff dashboard | `staffApi.*` |
| `/admin` | Admin dashboard | `adminApi.getOverview()` |
| `/admin/products` | Product management | `adminApi.getProducts()` |
| `/admin/products/new` | Create product | `adminApi.createProduct()` |
| `/admin/products/[id]/edit` | Edit product | `adminApi.getProduct()`, `adminApi.updateProduct()` |
| `/admin/categories` | Category management | `adminApi.getCategories()`, CRUD |
| `/admin/orders` | Order management | `adminApi.getOrders()` |
| `/admin/payments` | Payment management | `adminApi.getPayments()` |
| `/admin/customers` | Customer management | `adminApi.getCustomers()` |
| `/admin/returns` | Returns management | `adminApi.getReturns()` |
| `/admin/audit-logs` | Audit trail | `adminApi.getAuditLogs()` |
| `/admin/pos` | Point of sale | `adminApi.createOfflineSale()` |
| `/about` | About page | Static content |
| `/contact` | Contact page | Static content |
| `/faqs` | FAQ page | Potentially `contentApi.*` |
| `/privacy-policy` | Privacy policy | Static content |
| `/terms` | Terms & conditions | Static content |
| `/shipping-delivery` | Shipping info | Static content |
| `/returns-exchanges` | Returns policy | Static content |

### Frontend API Modules (12 files)

| File | Export | Backend Endpoints Called |
|---|---|---|
| `client.ts` | `apiClient()` | Core fetch wrapper, token management |
| `auth.ts` | `authApi` | `/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`, `/auth/change-password` |
| `cart.ts` | `cartApi` | `/cart`, `/cart/items`, `/cart/merge`, `/wishlist`, `/wishlist/items` |
| `catalog.ts` | `catalogApi` | `/categories/tree`, `/categories`, `/collections`, `/products` |
| `orders.ts` | `ordersApi` | `/orders/checkout`, `/orders/{number}` |
| `customer.ts` | `customerApi` | `/customer/profile`, `/customer/preferences`, `/customer/addresses`, `/customer/orders`, `/customer/returns`, `/customer/security` |
| `admin.ts` | `adminApi` | `/admin/reports/*`, `/admin/categories/*`, `/admin/products/*`, `/admin/orders/*`, `/admin/payments/*`, `/admin/customers/*`, `/admin/returns/*`, `/admin/audit-logs`, `/admin/offline-sales/*` |
| `staff.ts` | `staffApi` | `/staff/*` |
| `shipping.ts` | `shippingApi` | `/shipping/*` |
| `payments.ts` | `paymentsApi` | `/payments/*` |
| `content.ts` | `contentApi` | `/content/*` |
| `adapters.ts` | Mapping functions | No API calls (data transforms) |
| `types.ts` | TypeScript types | No API calls |

### Context Providers

| Provider | State | Backend Dependency |
|---|---|---|
| `AuthContext` | User session, auth modal | `authApi.login()`, `authApi.getMe()`, `authApi.logout()`, `cartApi.mergeCart()` |
| `CartContext` | Cart items, totals | `cartApi.*` with localStorage fallback |
| `WishlistContext` | Wishlist items | `cartApi.getWishlist()` with localStorage fallback |

### Static Fallback Data

| File | Contents | Purpose |
|---|---|---|
| `data/products.ts` | `PRODUCTS = []` (empty array) | Fallback product data (currently empty) |
| `data/categories.ts` | 6 hardcoded categories with Unsplash URLs | Fallback category data for when backend is unavailable |

---

## 8. Media / Image Storage Inventory

### Storage Architecture

| Component | Implementation |
|---|---|
| Storage abstraction | `BaseStorageService` ABC |
| Production adapter | `S3StorageService` (AWS S3 + optional CloudFront CDN) |
| Development adapter | `MockStorageService` (in-memory, simulated URLs) |
| Local adapter | Mentioned in config (`STORAGE_BACKEND=local`) but **no `LocalStorageService` class exists** |
| Current default | `STORAGE_BACKEND=mock` |
| Upload method | Presigned PUT URL (server generates URL, client uploads directly to S3) |
| File validation | MIME type whitelist: JPEG, PNG, WebP, AVIF; 10MB max |
| URL expiry | 15 minutes for presigned upload URLs |
| Static uploads mount | `/uploads` directory mounted in FastAPI (for local file serving) |

### Current Image Sources

1. **Unsplash URLs** — All seed data categories and products use `images.unsplash.com` URLs
2. **product_images table** — Stores `image_url`, `alt_text`, `sort_order`, `is_primary`
3. **No actual uploaded images exist** — Storage backend is `mock`; no AWS credentials configured

### Key Observations

- `next.config.mjs` allows remote images from `*.unsplash.com`, `localhost:8000`, `backend:8000`, and `**` (all HTTPS)
- Static export mode (`output: 'export'`) is the default (via `STATIC_EXPORT` env var)
- When `STATIC_EXPORT !== 'false'`, Next.js Image optimization is disabled (`unoptimized: true`)

---

## 9. Environment Variable Names

### Backend (from `.env.example` + `config.py`)

```
APP_ENV, APP_NAME, DEBUG, PORT, HOST, API_V1_PREFIX, SECRET_KEY
CORS_ORIGINS
MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD
DATABASE_URL, DATABASE_URL_ASYNC
JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
COOKIE_SECURE, COOKIE_SAMESITE, COOKIE_DOMAIN
STORAGE_BACKEND, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
AWS_S3_BUCKET_NAME, AWS_CLOUDFRONT_DOMAIN
MEDIA_UPLOAD_MAX_BYTES, PRESIGNED_URL_EXPIRE_SECONDS
STORE_CURRENCY, FREE_SHIPPING_THRESHOLD, STANDARD_SHIPPING_FEE, COD_ENABLED, MAX_CART_LINE_ITEMS
ONLINE_PAYMENT_PROVIDER, PAYMENT_WEBHOOK_SECRET, PAYMENT_GATEWAY_API_KEY
PAYMENT_GATEWAY_MERCHANT_ID, PAYMENT_GATEWAY_BASE_URL
DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT, DB_POOL_RECYCLE, DB_POOL_PRE_PING
```

### Frontend (from `next.config.mjs` + `docker-compose.yml`)

```
NEXT_PUBLIC_API_URL, NEXT_PUBLIC_STORE_NAME, NEXT_PUBLIC_STORE_CURRENCY
INTERNAL_API_URL
NODE_ENV, PORT
STATIC_EXPORT
```

> [!CAUTION]
> `docker-compose.yml` contains development-only credentials in plaintext (MySQL passwords, SECRET_KEY). These must never be used in production.

---

## 10. Mock / Simulated Functionality Inventory

| Feature | Implementation Type | Evidence |
|---|---|---|
| **Media storage** | Mock (in-memory) | `MockStorageService`: simulated URLs, no actual file storage |
| **Online payments** | Mock | `MockOnlinePaymentProvider`: fake transaction refs, HMAC test signatures |
| **Unconfigured payments** | Explicit refusal | `UnconfiguredPaymentProvider`: raises HTTP 400 for all operations |
| **COD payments** | Real (first-class) | `CodPaymentProvider`: genuine provider, no external dependency |
| **Courier/tracking** | Simulated | Fulfillment module exists, but no real courier API integration |
| **Email delivery** | Not implemented | Password reset token stored but never dispatched via email |
| **Static product data** | Empty fallback | `data/products.ts` exports `PRODUCTS = []` |
| **Static category data** | Hardcoded fallback | `data/categories.ts` has 6 categories with Unsplash images |
| **Shipping rates** | Configured | Rate lookup exists, but courier rates may be manually configured, not API-fetched |
| **Terraform AWS infra** | Defined, not deployed | ECS, RDS, S3, CloudFront, ECR, VPC, IAM — all `.tf` files present, no `.terraform/` or state files |

---

## 11. Hosting / Runtime Compatibility Assessment

### Current Next.js Configuration

| Setting | Value | Migration Impact |
|---|---|---|
| Default output mode | `export` (static HTML) | **Must change to `standalone` or default for SSR** |
| `STATIC_EXPORT` env toggle | `!== 'false'` → static export | Conditional; can be switched off |
| Image optimization | Disabled in static mode | Will need enabling for SSR mode |
| Middleware | **None** (`middleware.ts` does not exist) | Simplifies hosting compatibility |
| Server Actions | **None** | No `"use server"` directives found |
| Route Handlers | **None** (`route.ts` files do not exist) | No server-side API routes in frontend |
| `"use client"` directives | 3 context providers only | Most pages are server-renderable |
| Node.js API imports | **None** | No `fs`, `path`, `crypto`, `node:*` imports |
| Native dependencies | **None** | Pure JavaScript dependencies only |

### Cloudflare Pages/Workers Compatibility

| Factor | Assessment |
|---|---|
| Next.js 15.1.0 support | ⚠️ **Requires verification** — `@cloudflare/next-on-pages` or `next-on-cf` adapter compatibility with exact 15.1.0 must be tested |
| React 19 support | ⚠️ **Requires verification** — React 19 streaming SSR behavior on Workers runtime |
| No middleware | ✅ No middleware conflicts |
| No Node.js APIs | ✅ No `node:*` imports, no `fs`/`crypto` usage |
| No native modules | ✅ Compatible with Workers runtime |
| Static export current default | ✅ Could deploy as static-only to Pages immediately |
| Image optimization | ⚠️ Next.js built-in image optimization requires Node.js; would need Cloudflare Image Resizing or `unoptimized: true` |
| Dynamic routes (`[slug]`, `[category]`, `[id]`) | ⚠️ Need SSR for real data; static export generates no dynamic pages without `generateStaticParams` |

### Verdict

The frontend is **simple and lightweight** — no server-side features, no middleware, no Node.js APIs, no native dependencies. The main blocker is switching from `output: 'export'` to SSR mode for dynamic content. Cloudflare Pages/Workers compatibility is plausible but **must be tested** with the exact Next.js 15.1.0 + React 19 combination.

---

## 12. CI/CD & Infrastructure

### GitHub Actions Workflows (4 files)

| Workflow | Purpose | Status |
|---|---|---|
| `ci.yml` | Lint, type-check, test on push/PR | Defined, not runtime-tested |
| `deploy-production.yml` | Deploy to AWS ECS | Defined, no AWS infra exists |
| `deploy-staging.yml` | Deploy to staging | Defined, no staging env exists |
| `frontend-gh-pages.yml` | Deploy static export to GitHub Pages | Defined, may be active in original repo |

### Terraform (14 files)

AWS infrastructure defined but **not deployed** (no `.terraform/`, no `terraform.tfstate`):

- VPC + subnets + NAT gateway
- ECS Fargate cluster + services (backend + frontend)
- RDS MySQL 8.0 instance
- ECR repositories
- S3 bucket + CloudFront distribution
- IAM roles and policies
- Secrets Manager
- CloudWatch logging
- Security groups
- Staging and production tfvars

### Docker

| File | Purpose |
|---|---|
| `docker-compose.yml` | Local dev: MySQL 8.0 + FastAPI backend + Next.js frontend |
| `backend/Dockerfile` | Python 3.12, pip install, uvicorn |
| `frontend/Dockerfile` | Node.js, npm build, next start |

---

## 13. Risks, Unknowns & Dependencies

### Critical Risks

| # | Risk | Severity | Detail |
|---|---|---|---|
| 1 | **No email delivery** | High | Password reset tokens are created but never sent. Users cannot recover accounts. |
| 2 | **No real payment gateway** | High | Only COD and Mock providers exist. Online payments refuse with HTTP 400. |
| 3 | **No real media storage** | Medium | Mock storage only; no actual files stored or served. |
| 4 | **Static export mode** | High | Current default renders static HTML with empty product data. Dynamic pages show nothing without backend. |
| 5 | **No git commits** | Medium | Workspace has `.git` but zero commits. No version history to roll back to. |
| 6 | **Argon2id password import** | Medium | Supabase Auth must support the exact Argon2id format (`$argon2id$v=19$m=65536,t=3,p=4$...`). Untested. |

### Unknowns Requiring Verification

| # | Unknown | Action Required |
|---|---|---|
| 1 | Cloudflare adapter + Next.js 15.1.0 + React 19 compatibility | Test in staging |
| 2 | Supabase Argon2id hash import format compatibility | Test with disposable account |
| 3 | Supabase free-tier connection pool limits (PgBouncer) | Check current documentation |
| 4 | R2 free-tier operation quotas for actual usage patterns | Calculate expected operations |
| 5 | MySQL → PostgreSQL type mapping edge cases (DECIMAL precision, ENUM behavior, timestamp semantics) | Review during Stage 1 |
| 6 | Frontend runtime behavior when switched from static to SSR mode | Build test required |

### Dependencies on External Services

| Service | Current State | Migration Target |
|---|---|---|
| MySQL 8.0 | Docker only (no hosted instance) | Supabase PostgreSQL |
| AWS S3 | Not configured (mock mode) | Cloudflare R2 |
| AWS CloudFront | Not configured | Cloudflare CDN |
| AWS ECS | Not deployed (Terraform only) | Cloudflare Pages/Workers or Vercel |
| Email provider | Not implemented | TBD (Resend, SendGrid, etc.) |
| Payment gateway | Not implemented | TBD (SafePay, PayFast, JazzCash) |
| Courier API | Not implemented | TBD |

---

## 14. Opus Serverless Trap Audit

> [!WARNING]
> The following analysis identifies specific serverless architecture traps that could impact the migration. These must be addressed in the Stage 1 design before implementation begins.

### 14.1 Database Connection Exhaustion

**Risk: HIGH**

| Factor | Detail |
|---|---|
| Supabase Free tier | PgBouncer in transaction mode, limited to **~20 direct connections** and **~200 pooled connections** |
| Current backend | `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20` — persistent connection pool managed by SQLAlchemy |
| Serverless pattern | Each Next.js Route Handler or Server Action creates a new Supabase client per request |
| Mitigation | Use `@supabase/ssr` with `createServerClient()` which goes through Supabase's built-in PgBouncer. Avoid raw `pg` connections. For complex transactions, use RPC calls to PostgreSQL functions (single connection, single transaction). Never hold connections across await boundaries in edge functions. |

**Specific concern:** The current backend has 208 endpoints. If converted to Next.js Route Handlers, each invocation opens a Supabase connection. At even modest concurrency (10 simultaneous requests), connection exhaustion is possible on free tier.

**Recommendation:** Use the Supabase JavaScript client exclusively (it goes through PostgREST, not direct connections). Reserve direct PostgreSQL connections for RPC functions only.

### 14.2 Cold Start Latency

**Risk: MEDIUM**

| Factor | Detail |
|---|---|
| Cloudflare Workers | Sub-millisecond cold starts (V8 isolates, not containers) |
| Vercel Serverless Functions | 250ms–2s cold starts (Node.js) |
| Vercel Edge Functions | Sub-millisecond cold starts (similar to Workers) |
| Supabase Edge Functions | ~100ms cold starts (Deno-based) |
| Impact on checkout | A 1-2s delay during checkout is acceptable for COD. For future online payments with redirect flows, cold starts compound with gateway latency. |

**Recommendation:** Cloudflare Workers or Vercel Edge Functions are preferred for latency-sensitive paths (checkout, auth). The current application has no WebSocket requirements, no long-polling, and no streaming—reducing cold start impact.

### 14.3 Timeout Limits

**Risk: MEDIUM-HIGH**

| Platform | CPU Time Limit | Wall-Clock Limit |
|---|---|---|
| Cloudflare Workers (free) | 10ms CPU | ~30s wall-clock |
| Cloudflare Workers (paid) | 50ms CPU | ~30s wall-clock |
| Vercel Serverless (Hobby) | N/A | 10s |
| Vercel Serverless (Pro) | N/A | 60s |
| Vercel Edge Functions | N/A | 25s |
| Supabase Edge Functions | N/A | ~150s (configurable) |

**Critical operations that could exceed limits:**

1. **Checkout transaction** — Current implementation: validate cart → check inventory → calculate totals → create order + items → reserve stock → create payment record. As a PostgreSQL function (RPC), this runs in milliseconds on the database server, well within limits.

2. **Bulk product status update** — `adminApi.bulkUpdateStatus()`: could process many products. Should be fine as a single SQL UPDATE.

3. **Report generation** — `/admin/reports/*`: aggregation queries on orders, payments, inventory. Depends on data volume; under 1,000 orders this is sub-second.

4. **Image upload** — Presigned URL pattern (current): server just generates URL (fast). Client uploads directly to R2 (no timeout concern). Server records metadata (fast).

**Recommendation:** Convert checkout to a PostgreSQL function (RPC) that runs atomically on the database. This eliminates timeout risk and ensures transactional integrity. All other operations are lightweight enough for serverless limits.

### 14.4 Edge Runtime Restrictions

**Risk: LOW**

| Restriction | Impact on UniNova |
|---|---|
| No `node:fs` | ✅ Not used in frontend; backend file system access replaced by R2 |
| No `node:crypto` | ✅ Not used in frontend; password hashing moves to Supabase Auth; webhook signatures use Web Crypto API (`crypto.subtle`) |
| No native modules | ✅ Current frontend has zero native dependencies |
| No `eval()` or dynamic code | ✅ No dynamic code execution in frontend |
| Limited `node:*` APIs | ✅ Frontend only uses `fetch`, `URL`, `URLSearchParams` — all available in Workers |

**The current frontend is already edge-compatible** in terms of API usage. The migration adds Supabase JS client which is also edge-compatible.

### 14.5 Supabase Free-Tier Pausing

**Risk: HIGH for live store**

| Factor | Detail |
|---|---|
| Inactivity threshold | 7 days without API requests → project paused |
| Resume time | 1–2 minutes (cold resume of PostgreSQL) |
| Impact | Store completely down during resume. Customers see errors. |
| Workaround (free) | Cron job or monitoring ping every few days |
| Permanent fix | Supabase Pro ($25/month) — no auto-pausing |

**Recommendation:** For initial development and staging, free tier is fine. Before accepting real customer orders, upgrade to Pro or implement a reliable keep-alive mechanism. The migration guide's $0/month target for database is unrealistic for a store that might go 7 days without traffic during slow periods.

### 14.6 R2 Operation Quotas

**Risk: LOW**

| Operation Type | Free Allowance | UniNova Usage Estimate |
|---|---|---|
| Class A (PUT, POST, LIST) | 1,000,000/month | ~100/month (product image uploads, admin operations) |
| Class B (GET, HEAD) | 10,000,000/month | ~10,000/month (product images served via CDN cache) |
| Storage | 10 GB | ~1 GB initially (product images, category banners) |
| Egress | Free (no egress charges) | N/A |

**Verdict:** R2 free tier is more than sufficient. Cloudflare CDN caching means most image requests never hit R2 origin.

### 14.7 RLS Performance

**Risk: LOW-MEDIUM**

| Factor | Detail |
|---|---|
| Table count | ~47 tables need RLS policies |
| Policy complexity | Simple: `auth.uid() = user_id` for customer data; role checks for admin |
| Performance impact | PostgreSQL evaluates RLS as additional WHERE clauses; negligible for indexed columns |
| Risk area | Complex join-based policies (e.g., "staff with `orders.read` permission") — must index `user_roles`, `role_permissions` |

**Recommendation:** Keep RLS policies simple. Use `auth.uid()` for customer isolation. For staff authorization, consider a `is_staff_with_permission(permission_code)` PostgreSQL function that the RLS policies call. Index `user_roles.user_id` and `role_permissions.role_id` (already indexed via primary keys).

### 14.8 Additional Serverless Traps

| Trap | Assessment |
|---|---|
| **No background jobs** | Current system has none (no Celery/RQ). Future needs (email sending, report generation) can use Supabase Edge Functions or Cloudflare Workers with scheduled triggers (cron). |
| **No WebSockets** | Current system has none. No migration concern. |
| **Request body size limits** | Cloudflare Workers: 100 MB free. Vercel: 4.5 MB (serverless) / 4 MB (edge). Image uploads via presigned R2 URLs bypass this. |
| **Environment variable limits** | Cloudflare: 64 per worker. Vercel: generous. Current app needs ~30 env vars — within limits. |
| **Concurrent function instances** | Cloudflare: 10 concurrent (free), 50,000 (paid). Vercel: varies. For <1,000 visitors/month, free tier is sufficient. |
| **Database connection during build** | Next.js build-time data fetching could fail if Supabase is paused. Use `dynamicParams` and runtime fetching, not `generateStaticParams` with DB calls. |

---

## 15. Summary & Readiness Assessment

### What is ready for migration:

1. ✅ Clean, well-structured codebase with clear module boundaries
2. ✅ Comprehensive API client layer that can be retargeted to Supabase
3. ✅ No Node.js-specific APIs in frontend (edge-compatible)
4. ✅ No middleware to complicate hosting
5. ✅ SQLAlchemy models clearly document the schema for PostgreSQL conversion
6. ✅ Storage abstraction already exists (swap S3 adapter for R2)
7. ✅ Payment provider abstraction already exists (add real providers later)
8. ✅ RBAC model maps well to PostgreSQL RLS + functions

### What needs careful attention:

1. ⚠️ Switch from static export to SSR mode
2. ⚠️ Cloudflare Pages/Workers adapter compatibility test
3. ⚠️ Argon2id password hash import into Supabase Auth
4. ⚠️ Checkout transaction atomicity in serverless context
5. ⚠️ Supabase free-tier pausing for live store
6. ⚠️ 208 endpoints → prioritize which actually need server-side implementation vs. direct Supabase client queries

### What is missing entirely:

1. ❌ Email delivery (must implement from scratch)
2. ❌ Real payment gateway integration
3. ❌ Real courier/shipping API integration
4. ❌ Real media files (all Unsplash placeholders)
5. ❌ Git commit history

---

> **Stage 0 is complete. Awaiting approval before proceeding to Stage 1 (Architecture & Migration Design).**
>
> **Model recommendation: The Opus serverless trap audit above covers the major architectural risks. The remaining Stage 1 work (schema mapping, RLS policy matrix, API replacement matrix, cost estimation) is systematic design work suitable for Sonnet. → Shift to Sonnet and continue.**
