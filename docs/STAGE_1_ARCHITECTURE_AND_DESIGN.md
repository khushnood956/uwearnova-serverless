# UniNova: Stage 1 — Architecture & Migration Design Specification

**Document Version:** 1.0.0  
**Target Architecture:** Next.js 15 + Supabase (PostgreSQL, Auth, RLS, RPC) + Cloudflare (DNS, CDN, R2)  
**Workspace:** `E:\UWearNova`  
**Date:** 2026-11-16  
**Status:** Design Proposal — Awaiting Approval Before Provisioning or Implementation  

---

## 1. Executive Summary & Design Principles

This document establishes the blueprint for replacing the legacy serverful FastAPI + MySQL backend with a serverless/BaaS architecture centered on Supabase and Cloudflare. 

### Core Architectural Decisions
1. **Zero FastAPI / MySQL Dependency:** The final system terminates all FastAPI endpoints and MySQL tables.
2. **Next.js 15 Full-Stack SSR:** Switch Next.js from `output: 'export'` (static HTML export) to SSR (`output: 'standalone'`). Next.js Route Handlers and Server Actions handle privileged server operations, while storefront read queries run directly through `@supabase/ssr` / `@supabase/supabase-js`.
3. **Database Integrity via PostgreSQL RPC:** High-concurrency operations (such as checkout, inventory deduction, coupon application, and refund processing) run in PostgreSQL stored functions (`SECURITY DEFINER` with strict `search_path`), guaranteeing ACID transactions in sub-10ms without connection exhaustion or edge timeout hazards.
4. **Cloudflare R2 for Media Assets:** Product and marketing images migrate from mock/local paths to Cloudflare R2 object storage served behind Cloudflare CDN with custom cache rules.
5. **Strict RLS on All 50 Tables:** Row Level Security (RLS) is enabled on 100% of tables with a strict "default deny" posture.

---

## 2. Final Target Architecture

```text
                                 [ End Customer / Admin Staff ]
                                                |
                                                | HTTPS (TLS 1.3)
                                                v
                              +-----------------------------------+
                              |     Cloudflare Global Edge        |
                              | - DNS & DDoS Protection           |
                              | - SSL / Edge Caching              |
                              | - Custom Domain Routing           |
                              +-----------------+-----------------+
                                                |
                       +------------------------+------------------------+
                       |                                                 |
                       v (Storefront & Admin Routes)                     v (Image / Media CDN)
       +-------------------------------+                  +-------------------------------+
       |       Next.js 15 App          |                  |      Cloudflare R2 Bucket     |
       |  (Cloudflare Workers / Pages  |                  |        "product-media"        |
       |       or Vercel SSR)          |                  |  images.uninova.store/media/  |
       +---------------+---------------+                  +-------------------------------+
                       |
       +---------------+-----------------------+
       |                                       |
       | Client PostgREST Queries              | Privileged Server Actions /
       | (Public catalog, user profile,        | Server Route Handlers
       |  cart/wishlist with JWT RLS)          | (Webhook receivers, R2 presigning)
       v                                       v
+---------------------------------------------------------------------------------+
|                                 SUPABASE PLATFORM                               |
|                                                                                 |
|  +--------------------+   +-----------------------+   +----------------------+  |
|  |   Supabase Auth    |   |   PostgreSQL Engine   |   |   PostgREST API      |  |
|  | - JWT Minting      |   | - 50 Relational Tables|   | - Auto REST API      |  |
|  | - auth.users       |   | - RLS Policies        |   | - PostgREST filter   |  |
|  | - Role / UID claims|   | - RPC Atomic Trans.   |   | - JWT Verification   |  |
|  +--------------------+   +-----------------------+   +----------------------+  |
|                                                                                 |
+---------------------------------------------------------------------------------+
                       |
                       +-----------------------+
                       | External Integrations |
                       +-----------------------+
                       | - Transactional Email (Resend / Postmark via Webhook/Func)
                       | - Couriers (TCS / Trax API when configured)
                       | - Payment Gateways (COD primary; EasyPaisa/JazzCash future)
```

---

## 3. MySQL to PostgreSQL Schema Mapping

All 50 tables from the existing SQLAlchemy models are mapped below with specific PostgreSQL data types, primary keys, indexes, and relationship constraints.

### 3.1 Global Type Mapping Rules
* **Primary Keys:** `BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` for core transactional and catalog entities to retain compatibility with existing frontend numeric IDs.
* **UUIDs:** `UUID DEFAULT gen_random_uuid()` for auth linkage, public order references, and session tracking.
* **Timestamps:** `TIMESTAMPTZ` (`TIMESTAMP WITH TIME ZONE`) with `DEFAULT now()`.
* **Currency & Monetary Amounts:** `NUMERIC(12, 2)` strictly. Floating-point types are prohibited.
* **JSON:** `JSONB` for unstructured metadata, configuration, and audit diffs.
* **Booleans:** Native PostgreSQL `BOOLEAN` (replaces MySQL `TINYINT(1)`).
* **Strings:** `VARCHAR(n)` where lengths are fixed; `TEXT` where lengths vary.

### 3.2 Inventory of Mapped Tables

| Module | Table Name | Key Columns & Types | Relational Constraints / Notes |
|---|---|---|---|
| **Auth** | `users` | `id BIGINT IDENTITY`, `auth_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE`, `email VARCHAR(255) UNIQUE`, `status VARCHAR(32)`, `user_type VARCHAR(32)` | Bridges Supabase `auth.users` to domain logic |
| **Auth** | `refresh_tokens` | *DECOMMISSIONED* | Supabase Auth natively manages token lifecycles and rotation |
| **Auth** | `password_resets` | *DECOMMISSIONED* | Handled natively by Supabase Auth (`supabase.auth.resetPasswordForEmail`) |
| **RBAC** | `roles` | `id BIGINT IDENTITY`, `name VARCHAR(64) UNIQUE`, `display_name VARCHAR(128)`, `is_system BOOLEAN` | Seeded with `store_admin`, `catalog_manager`, `order_manager`, `support_staff` |
| **RBAC** | `permissions` | `id BIGINT IDENTITY`, `code VARCHAR(64) UNIQUE`, `category VARCHAR(64)`, `description VARCHAR(255)` | Granular codes (e.g. `products.create`, `orders.manage`) |
| **RBAC** | `role_permissions` | `role_id BIGINT REFERENCES roles(id) ON DELETE CASCADE`, `permission_id BIGINT REFERENCES permissions(id) ON DELETE CASCADE` | PK: `(role_id, permission_id)` |
| **RBAC** | `user_roles` | `user_id BIGINT REFERENCES users(id) ON DELETE CASCADE`, `role_id BIGINT REFERENCES roles(id) ON DELETE CASCADE` | PK: `(user_id, role_id)` |
| **Customer**| `customer_profiles`| `id BIGINT IDENTITY`, `user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE`, `first_name VARCHAR(64)`, `last_name VARCHAR(64)`, `phone VARCHAR(32)` | Indexed on `user_id` |
| **Customer**| `addresses` | `id BIGINT IDENTITY`, `user_id BIGINT REFERENCES users(id) ON DELETE CASCADE`, `full_name VARCHAR(128)`, `phone VARCHAR(32)`, `street_address TEXT`, `city VARCHAR(128)`, `province VARCHAR(64)`, `postal_code VARCHAR(32)`, `is_default BOOLEAN` | Indexed on `(user_id, is_default)` |
| **Catalog** | `categories` | `id BIGINT IDENTITY`, `name VARCHAR(128)`, `slug VARCHAR(128) UNIQUE`, `parent_id BIGINT REFERENCES categories(id) ON DELETE SET NULL`, `sort_order INT`, `is_active BOOLEAN`, `is_coming_soon BOOLEAN`, `image_url TEXT` | Tree navigation index on `(parent_id, is_active)` |
| **Catalog** | `collections` | `id BIGINT IDENTITY`, `name VARCHAR(128)`, `slug VARCHAR(128) UNIQUE`, `is_active BOOLEAN`, `sort_order INT`, `image_url TEXT` | Curated product groupings |
| **Catalog** | `products` | `id BIGINT IDENTITY`, `category_id BIGINT REFERENCES categories(id) ON DELETE RESTRICT`, `name VARCHAR(255)`, `slug VARCHAR(255) UNIQUE`, `price NUMERIC(12,2)`, `original_price NUMERIC(12,2)`, `status VARCHAR(32)`, `is_featured BOOLEAN`, `is_trending BOOLEAN`, `is_new_arrival BOOLEAN` | Full-text search index on `(name, slug)` |
| **Catalog** | `product_variants`| `id BIGINT IDENTITY`, `product_id BIGINT REFERENCES products(id) ON DELETE CASCADE`, `sku VARCHAR(64) UNIQUE`, `size VARCHAR(32)`, `color_name VARCHAR(64)`, `color_hex VARCHAR(16)`, `price NUMERIC(12,2)`, `inventory_count INT`, `is_active BOOLEAN` | Indexed on `(product_id, is_active)` |
| **Catalog** | `product_images` | `id BIGINT IDENTITY`, `product_id BIGINT REFERENCES products(id) ON DELETE CASCADE`, `image_url TEXT`, `alt_text VARCHAR(255)`, `sort_order INT`, `is_primary BOOLEAN` | Indexed on `(product_id, is_primary)` |
| **Catalog** | `product_collections`| `product_id BIGINT REFERENCES products(id) ON DELETE CASCADE`, `collection_id BIGINT REFERENCES collections(id) ON DELETE CASCADE` | PK: `(product_id, collection_id)` |
| **Cart** | `carts` | `id BIGINT IDENTITY`, `user_id BIGINT REFERENCES users(id) ON DELETE CASCADE`, `anonymous_token VARCHAR(64) UNIQUE`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ` | Supports guest checkout & auth merge |
| **Cart** | `cart_items` | `id BIGINT IDENTITY`, `cart_id BIGINT REFERENCES carts(id) ON DELETE CASCADE`, `variant_id BIGINT REFERENCES product_variants(id) ON DELETE CASCADE`, `quantity INT`, `created_at TIMESTAMPTZ` | Unique `(cart_id, variant_id)` |
| **Cart** | `wishlists` | `id BIGINT IDENTITY`, `user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE` | Customer wishlist header |
| **Cart** | `wishlist_items` | `id BIGINT IDENTITY`, `wishlist_id BIGINT REFERENCES wishlists(id) ON DELETE CASCADE`, `product_id BIGINT REFERENCES products(id) ON DELETE CASCADE` | Unique `(wishlist_id, product_id)` |
| **Inventory**| `inventory_locations`| `id BIGINT IDENTITY`, `name VARCHAR(128)`, `code VARCHAR(64) UNIQUE`, `is_active BOOLEAN`, `country_code VARCHAR(2)` | Physical warehouse locations |
| **Inventory**| `inventory_items` | `id BIGINT IDENTITY`, `variant_id BIGINT REFERENCES product_variants(id) ON DELETE CASCADE`, `location_id BIGINT REFERENCES inventory_locations(id) ON DELETE CASCADE`, `quantity_on_hand INT`, `quantity_reserved INT`, `reorder_threshold INT` | Unique `(variant_id, location_id)` |
| **Inventory**| `inventory_movements`| `id BIGINT IDENTITY`, `inventory_item_id BIGINT REFERENCES inventory_items(id) ON DELETE CASCADE`, `movement_type VARCHAR(32)`, `quantity INT`, `reference_type VARCHAR(64)`, `reference_id VARCHAR(64)`, `created_at TIMESTAMPTZ` | Immutable audit log of stock deltas |
| **Orders** | `orders` | `id BIGINT IDENTITY`, `order_number VARCHAR(64) UNIQUE`, `user_id BIGINT REFERENCES users(id) ON DELETE SET NULL`, `customer_email VARCHAR(255)`, `customer_phone VARCHAR(32)`, `customer_name VARCHAR(128)`, `status VARCHAR(32)`, `payment_status VARCHAR(32)`, `fulfillment_status VARCHAR(32)`, `payment_method VARCHAR(32)`, `subtotal NUMERIC(12,2)`, `shipping_fee NUMERIC(12,2)`, `discount_amount NUMERIC(12,2)`, `grand_total NUMERIC(12,2)`, `shipping_address JSONB`, `placed_at TIMESTAMPTZ` | Indexed on `(user_id, status, placed_at)` |
| **Orders** | `order_items` | `id BIGINT IDENTITY`, `order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE`, `variant_id BIGINT REFERENCES product_variants(id) ON DELETE SET NULL`, `product_name VARCHAR(255)`, `sku VARCHAR(64)`, `size VARCHAR(32)`, `color VARCHAR(64)`, `unit_price NUMERIC(12,2)`, `quantity INT`, `line_total NUMERIC(12,2)` | Historical immutable item snapshot |
| **Orders** | `order_status_history`| `id BIGINT IDENTITY`, `order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE`, `from_status VARCHAR(32)`, `to_status VARCHAR(32)`, `notes TEXT`, `created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL`, `created_at TIMESTAMPTZ` | Lifecycle tracking |
| **Orders** | `checkout_idempotency`| `id BIGINT IDENTITY`, `idempotency_key VARCHAR(128) UNIQUE`, `order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE`, `request_hash VARCHAR(64)`, `response_payload JSONB`, `expires_at TIMESTAMPTZ` | Prevents duplicate order placement |
| **Payments** | `payments` | `id BIGINT IDENTITY`, `order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE`, `provider_code VARCHAR(32)`, `payment_method VARCHAR(32)`, `status VARCHAR(32)`, `amount NUMERIC(12,2)`, `currency_code VARCHAR(3)`, `provider_reference VARCHAR(128)` | Financial payment header |
| **Payments** | `payment_transactions`| `id BIGINT IDENTITY`, `payment_id BIGINT REFERENCES payments(id) ON DELETE CASCADE`, `transaction_type VARCHAR(32)`, `amount NUMERIC(12,2)`, `status VARCHAR(32)`, `raw_response JSONB` | Ledger of transactions/attempts |
| **Payments** | `payment_events`| `id BIGINT IDENTITY`, `payment_id BIGINT REFERENCES payments(id) ON DELETE CASCADE`, `event_type VARCHAR(64)`, `raw_payload JSONB`, `signature_verified BOOLEAN` | Webhook verification audit |
| **Payments** | `refunds` | `id BIGINT IDENTITY`, `payment_id BIGINT REFERENCES payments(id) ON DELETE CASCADE`, `refund_number VARCHAR(64) UNIQUE`, `amount NUMERIC(12,2)`, `status VARCHAR(32)`, `reason TEXT` | Return/refund records |
| **Shipping** | `shipping_zones` | `id BIGINT IDENTITY`, `name VARCHAR(128)`, `country_code VARCHAR(2)`, `regions JSONB`, `is_active BOOLEAN` | Geographic delivery zones |
| **Shipping** | `shipping_methods`| `id BIGINT IDENTITY`, `zone_id BIGINT REFERENCES shipping_zones(id) ON DELETE CASCADE`, `name VARCHAR(128)`, `code VARCHAR(64) UNIQUE`, `base_rate NUMERIC(12,2)`, `free_threshold NUMERIC(12,2)`, `estimated_days VARCHAR(32)` | Delivery pricing policy |
| **Fulfillment**| `shipments` | `id BIGINT IDENTITY`, `order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE`, `tracking_number VARCHAR(128) UNIQUE`, `courier_name VARCHAR(64)`, `status VARCHAR(32)`, `shipped_at TIMESTAMPTZ`, `delivered_at TIMESTAMPTZ` | Physical parcel details |
| **Fulfillment**| `shipment_items`| `id BIGINT IDENTITY`, `shipment_id BIGINT REFERENCES shipments(id) ON DELETE CASCADE`, `order_item_id BIGINT REFERENCES order_items(id) ON DELETE CASCADE`, `quantity INT` | Items packed in shipment |
| **Fulfillment**| `shipment_events`| `id BIGINT IDENTITY`, `shipment_id BIGINT REFERENCES shipments(id) ON DELETE CASCADE`, `status VARCHAR(32)`, `location VARCHAR(128)`, `description TEXT`, `occurred_at TIMESTAMPTZ` | Courier tracking milestones |
| **Returns** | `return_requests`| `id BIGINT IDENTITY`, `return_number VARCHAR(64) UNIQUE`, `order_id BIGINT REFERENCES orders(id) ON DELETE RESTRICT`, `user_id BIGINT REFERENCES users(id) ON DELETE SET NULL`, `status VARCHAR(32)`, `request_type VARCHAR(32)`, `reason TEXT` | Return & exchange requests |
| **Returns** | `return_items` | `id BIGINT IDENTITY`, `return_request_id BIGINT REFERENCES return_requests(id) ON DELETE CASCADE`, `order_item_id BIGINT REFERENCES order_items(id) ON DELETE RESTRICT`, `quantity INT`, `reason VARCHAR(64)`, `condition VARCHAR(32)`, `status VARCHAR(32)` | Line items to return |
| **Reviews** | `product_reviews`| `id BIGINT IDENTITY`, `product_id BIGINT REFERENCES products(id) ON DELETE CASCADE`, `user_id BIGINT REFERENCES users(id) ON DELETE SET NULL`, `rating INT CHECK (rating BETWEEN 1 AND 5)`, `title VARCHAR(128)`, `comment TEXT`, `is_approved BOOLEAN`, `verified_purchase BOOLEAN` | Storefront reviews |
| **Promotions**| `coupons` | `id BIGINT IDENTITY`, `code VARCHAR(64) UNIQUE`, `discount_type VARCHAR(32)`, `discount_value NUMERIC(12,2)`, `minimum_order_amount NUMERIC(12,2)`, `usage_limit INT`, `usage_count INT`, `valid_from TIMESTAMPTZ`, `valid_until TIMESTAMPTZ`, `is_active BOOLEAN` | Discount coupons |
| **Promotions**| `coupon_redemptions`| `id BIGINT IDENTITY`, `coupon_id BIGINT REFERENCES coupons(id) ON DELETE RESTRICT`, `order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE`, `user_id BIGINT REFERENCES users(id) ON DELETE SET NULL`, `discount_amount NUMERIC(12,2)` | Redemption audit |
| **Staff** | `staff_profiles` | `id BIGINT IDENTITY`, `user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE`, `employee_id VARCHAR(32) UNIQUE`, `department VARCHAR(64)`, `is_active BOOLEAN` | Operational staff records |
| **Staff** | `support_tickets`| `id BIGINT IDENTITY`, `ticket_number VARCHAR(64) UNIQUE`, `user_id BIGINT REFERENCES users(id) ON DELETE SET NULL`, `order_id BIGINT REFERENCES orders(id) ON DELETE SET NULL`, `subject VARCHAR(255)`, `priority VARCHAR(32)`, `status VARCHAR(32)`, `assigned_staff_id BIGINT REFERENCES staff_profiles(id) ON DELETE SET NULL` | Helpdesk tickets |
| **Staff** | `support_ticket_messages`| `id BIGINT IDENTITY`, `ticket_id BIGINT REFERENCES support_tickets(id) ON DELETE CASCADE`, `sender_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL`, `message TEXT`, `is_internal BOOLEAN` | Ticket conversation thread |
| **Staff** | `staff_tasks` | `id BIGINT IDENTITY`, `staff_id BIGINT REFERENCES staff_profiles(id) ON DELETE CASCADE`, `title VARCHAR(255)`, `description TEXT`, `status VARCHAR(32)`, `due_date TIMESTAMPTZ` | Internal work assignments |
| **Content** | `announcement_bars`| `id BIGINT IDENTITY`, `text VARCHAR(255)`, `link_url TEXT`, `is_active BOOLEAN`, `display_order INT` | Header banners |
| **Content** | `homepage_campaigns`| `id BIGINT IDENTITY`, `title VARCHAR(128)`, `subtitle VARCHAR(255)`, `cta_text VARCHAR(64)`, `cta_url TEXT`, `image_url TEXT`, `is_active BOOLEAN`, `sort_order INT` | Hero & promotional campaigns |
| **Content** | `content_pages` | `id BIGINT IDENTITY`, `slug VARCHAR(128) UNIQUE`, `title VARCHAR(255)`, `body TEXT`, `meta_title VARCHAR(255)`, `meta_description TEXT`, `is_published BOOLEAN` | Static CMS pages (About, Terms, Privacy) |
| **Offline** | `offline_sales` | `id BIGINT IDENTITY`, `receipt_number VARCHAR(64) UNIQUE`, `staff_id BIGINT REFERENCES staff_profiles(id) ON DELETE RESTRICT`, `total_amount NUMERIC(12,2)`, `payment_method VARCHAR(32)`, `status VARCHAR(32)`, `customer_phone VARCHAR(32)` | Walk-in / POS transactions |
| **Offline** | `offline_sale_items`| `id BIGINT IDENTITY`, `sale_id BIGINT REFERENCES offline_sales(id) ON DELETE CASCADE`, `variant_id BIGINT REFERENCES product_variants(id) ON DELETE RESTRICT`, `unit_price NUMERIC(12,2)`, `quantity INT`, `line_total NUMERIC(12,2)` | POS line items |
| **Audit** | `audit_logs` | `id BIGINT IDENTITY`, `actor_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL`, `action VARCHAR(64)`, `entity_type VARCHAR(64)`, `entity_id VARCHAR(64)`, `changes JSONB`, `ip_address VARCHAR(45)`, `created_at TIMESTAMPTZ` | Immutable compliance trail |

---

## 4. Authentication & Password Migration Plan

### 4.1 Supabase Auth Architecture
* Customers and staff authenticate directly through Supabase Auth using the standard `@supabase/ssr` cookie-based session handler.
* When a user registers or logs in, Supabase issues an HTTP-only session cookie containing an encrypted JWT.
* The Next.js client (`src/lib/api/client.ts`) and Auth Context (`src/context/AuthContext.tsx`) are updated to consume Supabase Auth hooks and sessions directly, eliminating `sessionStorage` and custom token refresh loops.

### 4.2 Linking `auth.users` to `public.users`
To bridge Supabase's managed authentication with UniNova's domain entities, a PostgreSQL trigger automatically syncs records:

```sql
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (auth_user_id, email, status, user_type)
  VALUES (
    NEW.id,
    NEW.email,
    'active',
    COALESCE(NEW.raw_user_meta_data->>'user_type', 'customer')
  );
  
  -- Create customer profile automatically
  INSERT INTO public.customer_profiles (user_id, first_name, last_name, phone)
  VALUES (
    (SELECT id FROM public.users WHERE auth_user_id = NEW.id),
    NEW.raw_user_meta_data->>'first_name',
    NEW.raw_user_meta_data->>'last_name',
    NEW.raw_user_meta_data->>'phone'
  );
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();
```

### 4.3 Existing Customer Password Migration Strategy
* **Current State:** The database uses `Argon2id` hashes (`$argon2id$v=19$m=65536,t=3,p=4$...`).
* **Migration Approach:**
  1. *Staged Verification Test:* During Stage 3 (Data Migration Rehearsal), run a pilot script importing a test Argon2id hash into `auth.users` using the Supabase Admin API (`supabase.auth.admin.createUser({ password_hash: ... })`).
  2. *Graceful Fallback (Magic Link / Password Reset):* If the exact Argon2 parameters cannot be verified natively by Supabase's GoTrue instance, existing customer accounts are imported with their email, profile data, address book, and complete order history intact, but without password hashes. On their first post-migration visit, customers enter their email and receive an instant One-Time Password (OTP) / Magic Link or password reset prompt to establish a new password. Order history and addresses remain 100% attached to their account.

---

## 5. Row Level Security (RLS) Policy Matrix

Every table has RLS enabled with `ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;`. Default action is **DENY**.

### 5.1 Helper Functions for Role Checking
```sql
CREATE OR REPLACE FUNCTION auth.current_domain_user_id()
RETURNS BIGINT AS $$
  SELECT id FROM public.users WHERE auth_user_id = auth.uid() LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION auth.has_permission(p_code TEXT)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 
    FROM public.user_roles ur
    JOIN public.role_permissions rp ON ur.role_id = rp.role_id
    JOIN public.permissions p ON rp.permission_id = p.id
    JOIN public.users u ON ur.user_id = u.id
    WHERE u.auth_user_id = auth.uid()
      AND p.code = p_code
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION auth.is_staff()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.users 
    WHERE auth_user_id = auth.uid() 
      AND user_type IN ('staff', 'admin')
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;
```

### 5.2 Policy Matrix by Table Group

| Table Group / Name | Anonymous (`anon`) | Customer (`authenticated`) | Staff / Admin (`authenticated`) |
|---|---|---|---|
| **Catalog** (`categories`, `collections`, `products`, `product_variants`, `product_images`) | `SELECT` where `is_active = true` (and `status = 'active'`) | `SELECT` where `is_active = true` | `ALL` if `auth.has_permission('catalog.manage')` |
| **Content** (`announcement_bars`, `homepage_campaigns`, `content_pages`) | `SELECT` where `is_active = true` / `is_published = true` | Same as Anonymous | `ALL` if `auth.has_permission('content.manage')` |
| **Reviews** (`product_reviews`) | `SELECT` where `is_approved = true` | `SELECT` approved + `INSERT` own purchase review | `ALL` if `auth.has_permission('reviews.manage')` |
| **Customer Data** (`customer_profiles`, `addresses`) | No Access | `SELECT`, `UPDATE`, `DELETE` where `user_id = auth.current_domain_user_id()` | `SELECT` if `auth.has_permission('customers.read')` |
| **Cart** (`carts`, `cart_items`) | `SELECT`, `INSERT`, `UPDATE`, `DELETE` where `anonymous_token = current_setting('request.headers')::json->>'x-anonymous-cart-token'` | `SELECT`, `INSERT`, `UPDATE`, `DELETE` where `user_id = auth.current_domain_user_id()` | No direct access needed (isolated) |
| **Wishlist** (`wishlists`, `wishlist_items`) | No Access | `SELECT`, `INSERT`, `DELETE` where `user_id = auth.current_domain_user_id()` | No direct access needed |
| **Orders** (`orders`, `order_items`, `order_status_history`) | No direct access (Created only via RPC function) | `SELECT` where `user_id = auth.current_domain_user_id()` | `ALL` if `auth.has_permission('orders.manage')` |
| **Inventory** (`inventory_locations`, `inventory_items`, `inventory_movements`) | No Access | No Access (Deducted via RPC function) | `ALL` if `auth.has_permission('inventory.manage')` |
| **Payments** (`payments`, `payment_transactions`, `payment_events`, `refunds`) | No Access | `SELECT` where related `orders.user_id = auth.current_domain_user_id()` | `ALL` if `auth.has_permission('payments.manage')` |
| **Shipping** (`shipping_zones`, `shipping_methods`) | `SELECT` where `is_active = true` | `SELECT` where `is_active = true` | `ALL` if `auth.has_permission('shipping.manage')` |
| **Fulfillment** (`shipments`, `shipment_items`, `shipment_events`) | `SELECT` public tracking events by `tracking_number` | `SELECT` where order belongs to customer | `ALL` if `auth.has_permission('fulfillment.manage')` |
| **Returns** (`return_requests`, `return_items`) | No Access | `SELECT`, `INSERT` where `user_id = auth.current_domain_user_id()` | `ALL` if `auth.has_permission('returns.manage')` |
| **Coupons** (`coupons`, `coupon_redemptions`) | `SELECT` active code validation (via RPC) | Validate via RPC | `ALL` if `auth.has_permission('promotions.manage')` |
| **Staff & Admin** (`staff_profiles`, `support_tickets`, `staff_tasks`, `roles`, `permissions`, `audit_logs`) | No Access | Tickets: Customer can `SELECT`/`INSERT` own tickets | `ALL` based on respective granular permissions |
| **Offline Sales** (`offline_sales`, `offline_sale_items`) | No Access | No Access | `ALL` if `auth.has_permission('pos.manage')` |

---

## 6. API & Business-Logic Replacement Matrix

The 208 legacy FastAPI endpoints are mapped to modern serverless constructs:

```text
Target Pattern Distribution:
- Pattern A: Direct Supabase Client + PostgREST + RLS (102 endpoints - Storefront reads, simple customer writes)
- Pattern B: Next.js Server Actions / Route Handlers (48 endpoints - Privileged auth, uploads, webhooks)
- Pattern C: PostgreSQL Stored Functions / RPC (36 endpoints - High-concurrency ACID transactions)
- Pattern D: Decommissioned / Replaced by Supabase Auth (22 endpoints - Custom JWT and password tokens)
Total: 208 endpoints mapped
```

### Detailed Module Replacement Plan

| Module | Endpoints | Legacy Method | Target Replacement Pattern | Justification & Implementation Notes |
|---|---:|---|---|---|
| **Auth** | 8 | POST/GET | Pattern B & D (Supabase Auth) | `login`, `register`, `logout`, `refresh`, `password-reset/*` replaced by `@supabase/ssr` native auth methods. `getMe` uses `supabase.auth.getUser()`. |
| **Catalog** | 31 | GET/POST/PUT/DELETE | Pattern A (Client) & B (Admin Server Actions) | Public tree, collections, product listings, and product details query Supabase directly with client caching. Admin CRUD runs via Next.js Server Actions with permission checks. |
| **Cart & Wishlist** | 10 | GET/POST/PATCH/DELETE | Pattern A & Pattern C (RPC for Merge) | Cart item addition, updates, deletions query through Supabase with anonymous/user RLS. Guest cart merging on login runs as an atomic RPC `rpc('merge_guest_cart', { anon_token })`. |
| **Customer** | 20 | GET/POST/PATCH/DELETE | Pattern A (Direct Client) | Customer addresses, preferences, and profile updates execute directly via Supabase client constrained by `user_id = auth.current_domain_user_id()`. Admin views use Server Actions. |
| **Orders** | 13 | GET/POST | Pattern C (Checkout RPC) & Pattern A (Reads) | **Critical:** Order placement is executed via atomic RPC `rpc('place_order_atomic', payload)`. Customer order list and detail read directly via Supabase. Status transitions run via admin Server Action. |
| **Payments** | 15 | GET/POST | Pattern B (Route Handler) & Pattern C (RPC) | Payment initiation and COD cash collection run via Server Actions. Online gateway webhook listeners run as Next.js Route Handlers (`/api/webhooks/payment`) with cryptographic signature checks. |
| **Inventory** | 11 | GET/POST/PUT | Pattern A (Admin Read) & Pattern C (Adjust RPC) | Stock movements and threshold alerts update atomically via RPC to prevent overselling. Location listing reads via Supabase client. |
| **Shipping** | 8 | GET/POST/PUT | Pattern A (Read) & B (Admin Edit) | Storefront shipping calculation reads active methods from Supabase. Admin management via Server Actions. |
| **Fulfillment**| 9 | GET/POST | Pattern A (Tracking) & B (Admin Ops) | Public tracking endpoint `/api/tracking/[number]` reads `shipment_events`. Dispatching and packing run via admin Server Actions. |
| **Returns** | 11 | GET/POST/PATCH | Pattern A & B | Customer submit return requests; staff approve/reject and trigger inventory restock via Server Actions. |
| **Promotions** | 7 | GET/POST/DELETE | Pattern C (Validate Coupon RPC) | Coupon code redemption and validation run via atomic RPC `rpc('validate_and_apply_coupon')` enforcing usage limits and expiration server-side. |
| **Reviews** | 4 | GET/POST/PATCH | Pattern A (Public Read) & B (Staff Moderation) | Approved reviews read directly. Customer creation verified via purchase check. Staff moderation via Server Actions. |
| **Content** | 16 | GET/POST/PUT/DELETE | Pattern A (Reads) & B (Admin CRUD) | Announcements, campaigns, and CMS pages read directly. Editing via admin Server Actions. |
| **Media** | 8 | GET/POST/DELETE | Pattern B (R2 Upload Presigning) | Replaced by R2 presigned PUT generation in Next.js Server Action (`getPresignedUploadUrl`) and metadata record insertion. |
| **Reports** | 7 | GET | Pattern C (SQL Views / RPC) | Sales, low-stock, and best-seller analytics run via optimized PostgreSQL views (`v_admin_sales_overview`, `v_best_sellers`) with sub-second execution. |
| **Staff & Work**| 22 | GET/POST/PATCH | Pattern A & B | Staff profile queues, task management, and support ticketing run via Server Actions and Supabase client with RBAC checks. |
| **Offline Sales**| 4 | GET/POST | Pattern C (POS Atomic Sale RPC) | Walk-in sales create receipt, deduct stock, and record payment in a single database transaction via `rpc('create_offline_sale')`. |
| **RBAC & Audit**| 4 | GET/POST | Pattern A (Admin Read) & B (Admin Manage) | Role assignments and audit trail inspection. |

### 5.3 Core Transactional RPC: `place_order_atomic`
This replaces the FastAPI checkout pipeline with an atomic database function:
```sql
CREATE OR REPLACE FUNCTION public.place_order_atomic(p_order_data JSONB)
RETURNS JSONB AS $$
DECLARE
  v_user_id BIGINT;
  v_order_id BIGINT;
  v_order_number TEXT;
  v_item JSONB;
  v_variant_id BIGINT;
  v_qty INT;
  v_price NUMERIC(12,2);
  v_stock INT;
  v_subtotal NUMERIC(12,2) := 0;
  v_shipping NUMERIC(12,2);
  v_grand_total NUMERIC(12,2);
BEGIN
  -- 1. Identify User (null if guest)
  v_user_id := auth.current_domain_user_id();

  -- 2. Generate unique order number (UNV-YYYYMMDD-XXXXXX)
  v_order_number := 'UNV-' || to_char(now(), 'YYYYMMDD') || '-' || upper(substr(md5(random()::text), 1, 6));

  -- 3. Calculate shipping fee from database rule
  v_shipping := COALESCE((p_order_data->>'shipping_fee')::NUMERIC, 350.00);

  -- 4. Create Order Header
  INSERT INTO public.orders (
    order_number, user_id, customer_email, customer_phone, customer_name,
    status, payment_status, fulfillment_status, payment_method,
    subtotal, shipping_fee, discount_amount, grand_total, shipping_address
  ) VALUES (
    v_order_number, v_user_id,
    p_order_data->>'customer_email',
    p_order_data->>'customer_phone',
    p_order_data->>'customer_name',
    'pending_confirmation', 'unpaid', 'unfulfilled',
    p_order_data->>'payment_method',
    0, v_shipping, 0, 0,
    p_order_data->'shipping_address'
  ) RETURNING id INTO v_order_id;

  -- 5. Lock and Deduct Inventory for Each Line Item
  FOR v_item IN SELECT * FROM jsonb_array_elements(p_order_data->'items')
  LOOP
    v_variant_id := (v_item->>'variant_id')::BIGINT;
    v_qty := (v_item->>'quantity')::INT;

    -- Lock variant row and retrieve trusted price
    SELECT price, inventory_count INTO v_price, v_stock
    FROM public.product_variants
    WHERE id = v_variant_id FOR UPDATE;

    IF v_stock < v_qty THEN
      RAISE EXCEPTION 'INSUFFICIENT_STOCK: Variant % has only % units remaining.', v_variant_id, v_stock;
    END IF;

    -- Deduct stock
    UPDATE public.product_variants
    SET inventory_count = inventory_count - v_qty
    WHERE id = v_variant_id;

    -- Record movement audit
    INSERT INTO public.inventory_movements (
      inventory_item_id, movement_type, quantity, reference_type, reference_id
    ) VALUES (
      (SELECT id FROM public.inventory_items WHERE variant_id = v_variant_id LIMIT 1),
      'sale_deduction', -v_qty, 'order', v_order_number
    );

    -- Insert Order Item with trusted price
    INSERT INTO public.order_items (
      order_id, variant_id, product_name, sku, size, color, unit_price, quantity, line_total
    ) VALUES (
      v_order_id, v_variant_id,
      v_item->>'product_name', v_item->>'sku', v_item->>'size', v_item->>'color',
      v_price, v_qty, (v_price * v_qty)
    );

    v_subtotal := v_subtotal + (v_price * v_qty);
  END LOOP;

  -- 6. Finalize Totals
  v_grand_total := v_subtotal + v_shipping;
  UPDATE public.orders
  SET subtotal = v_subtotal, grand_total = v_grand_total
  WHERE id = v_order_id;

  -- 7. Clear Shopping Cart if cart ID was provided
  IF (p_order_data->>'cart_id') IS NOT NULL THEN
    DELETE FROM public.cart_items WHERE cart_id = (p_order_data->>'cart_id')::BIGINT;
  END IF;

  RETURN jsonb_build_object(
    'order_id', v_order_id,
    'order_number', v_order_number,
    'grand_total', v_grand_total,
    'status', 'pending_confirmation'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;
```

---

## 7. Cloudflare R2 Media Storage Architecture

### 7.1 Bucket Configuration
* **Bucket Name:** `uninova-media-staging` (staging) / `uninova-media-prod` (production)
* **Custom Domain:** `images.uninova.store`
* **Access Control:** Public reads enabled via Cloudflare CDN edge; direct writes restricted to presigned PUT URLs signed by Next.js server secrets.

### 7.2 Key Hierarchy
Object keys follow a structured, immutable naming pattern using random UUIDs to avoid filename collisions and sanitize malicious uploads:
```text
products/{product_id}/{uuid}.webp
categories/{category_id}/{uuid}.webp
campaigns/{campaign_id}/{uuid}.webp
brands/{brand_id}/{uuid}.webp
```

### 7.3 Direct-to-R2 Upload Sequence
```text
[ Staff Admin Browser ]               [ Next.js Server Action ]              [ Cloudflare R2 ]
         |                                       |                                  |
         | 1. Request Upload URL (file meta)     |                                  |
         |-------------------------------------->|                                  |
         |                                       | 2. Verify Session & Permission   |
         |                                       |    Generate S3-compatible        |
         |                                       |    Presigned PUT URL (15 min)    |
         | 3. Returns presigned URL + Key        |                                  |
         |<--------------------------------------|                                  |
         |                                                                          |
         | 4. Direct HTTP PUT Binary (image/webp, image/jpeg)                       |
         |------------------------------------------------------------------------->|
         |                                                                          |
         | 5. Confirm Upload with PostgreSQL Metadata                               |
         |-------------------------------------->|                                  |
         |                                       | 6. Insert into product_images    |
         | 7. Success Response                   |<---------------------------------|
         |<--------------------------------------|
```

---

## 8. Hosting Compatibility Decision: Next.js 15.1.0 on Edge

### 8.1 Evaluated Hosting Options

| Hosting Provider | Architecture | Cost (Initial Traffic) | Next.js 15.1 + React 19 Support | Trade-offs & Recommendation |
|---|---|---|---|---|
| **Option A: Cloudflare Pages / Workers (OpenNext)** | Serverless Edge Workers | $0 (Free allowance) | ⚠️ Experimental (Requires `@opennextjs/cloudflare`) | Requires bundle size auditing (<3MB compressed on free tier) and edge runtime compatibility testing. |
| **Option B: Vercel** | Serverless Node.js / Edge | $0 (Hobby) | ✅ Native 100% Support | First-class Next.js 15 & React 19 support. Zero configuration issues. Excellent cold start performance. |
| **Option C: Small VPS (Docker/Node standalone)** | Single Container | $4–$6/month | ✅ Standard Node runtime | Always-on, no cold starts, but introduces server maintenance and patching overhead. |

### 8.2 Recommended Staging Strategy
1. **Primary Target for Staging Rehearsal:** Cloudflare Workers via `@opennextjs/cloudflare` to maintain the user's unified Cloudflare preference (DNS + CDN + R2 + Hosting under $5/mo).
2. **Fallback Gateway:** If OpenNext encounters severe build/runtime bugs with Next.js 15.1.0's App Router during Stage 2 build validation, fall back cleanly to **Vercel Hobby** (Free tier) with Cloudflare DNS proxying the apex domain. Both platforms integrate identically with Supabase and Cloudflare R2.

### 8.3 Required Configuration Change in `frontend/next.config.mjs`
To support dynamic SSR and Route Handlers, remove `output: 'export'` and enable `standalone`:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  images: {
    formats: ['image/avif', 'image/webp'],
    remotePatterns: [
      { protocol: 'https', hostname: 'images.uninova.store' },
      { protocol: 'https', hostname: '*.r2.cloudflarestorage.com' },
      { protocol: 'https', hostname: 'images.unsplash.com' },
    ],
  },
};
export default nextConfig;
```

---

## 9. Environment & Secret Management Plan

### 9.1 Environment Variable Taxonomy

| Variable Name | Environment | Boundary | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Local, Staging, Prod | Public / Browser | Supabase project API endpoint |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Local, Staging, Prod | Public / Browser | Safe public key constrained by RLS |
| `NEXT_PUBLIC_SITE_URL` | Local, Staging, Prod | Public / Browser | Canonical base URL |
| `NEXT_PUBLIC_MEDIA_URL` | Local, Staging, Prod | Public / Browser | Public media CDN base URL (`https://images.uninova.store`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Local, Staging, Prod | **Server-Only** | Privileged database bypass key for seed/admin webhooks |
| `R2_ACCOUNT_ID` | Local, Staging, Prod | **Server-Only** | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Local, Staging, Prod | **Server-Only** | Cloudflare R2 S3-compatible API token |
| `R2_SECRET_ACCESS_KEY` | Local, Staging, Prod | **Server-Only** | Cloudflare R2 S3-compatible secret |
| `R2_BUCKET_NAME` | Local, Staging, Prod | **Server-Only** | Target R2 media bucket name |
| `PAYMENT_WEBHOOK_SECRET` | Local, Staging, Prod | **Server-Only** | HMAC secret for payment callback verification |
| `RESEND_API_KEY` | Staging, Prod | **Server-Only** | Transactional email provider token |

> [!CAUTION]
> Under no circumstances may `SUPABASE_SERVICE_ROLE_KEY`, `R2_SECRET_ACCESS_KEY`, or `PAYMENT_WEBHOOK_SECRET` be exposed to the browser or prefixed with `NEXT_PUBLIC_`.

---

## 10. Cost & Hosting Assessment (Updated Pricing)

### 10.1 Monthly Expense Forecast (<1,000 to 5,000 visitors/month)

| Component | Provider & Tier | Quota Included | Expected Monthly Cost |
|---|---|---|---:|
| **Database & Auth** | Supabase Free | 500 MB DB storage, 50,000 monthly active users (MAU), 5 GB egress | **$0.00** |
| **Storefront Hosting** | Cloudflare Workers / Pages (or Vercel Hobby) | 100,000 requests/day (Cloudflare) or 100 GB bandwidth (Vercel) | **$0.00** |
| **Media Object Storage**| Cloudflare R2 | 10 GB storage, 1M Class A ops (writes), 10M Class B ops (reads) | **$0.00** |
| **DNS, SSL & CDN** | Cloudflare Free | Unlimited traffic & DDoS mitigation | **$0.00** |
| **Domain Name** | Cloudflare Registrar | Annual renewal amortized ($10–$14/yr) | **~$1.00/mo** |
| **Transactional Email** | Resend (Free Tier) | 3,000 emails/month (100 emails/day) | **$0.00** |
| **Total Estimated Run Cost** | | | **Under $2.00 / month** |

### 10.2 Threshold Triggers for Paid Upgrades
* **Supabase Pro ($25/mo):** Required when active orders increase and the store cannot tolerate the free-tier 7-day inactivity pause, or when database storage exceeds 500 MB.
* **Cloudflare Workers Paid ($5/mo):** Required if worker CPU time consistently exceeds 10ms or script requests exceed 100,000/day.

---

## 11. Backup, Rollback & Cutover Plan

### 11.1 Rollback Guarantees
1. **Live Site Isolation:** The existing GitHub Pages storefront and Cloudflare DNS remains untouched throughout Stages 2 through 7.
2. **Original Project Safety:** `E:\website` and `E:\UniNova_Backup_Serverful_PreSupabase_Migration` remain read-only.
3. **Instant DNS Rollback:** Staging is verified on a subdomain (e.g. `staging.uninova.store`). The apex domain DNS target will only be changed after explicit user approval in Stage 8. Reverting DNS takes less than 60 seconds via Cloudflare DNS dashboard.

### 11.2 Database Backup Procedures
* In Supabase, automated daily backups are generated.
* A version-controlled repository of SQL migrations under `supabase/migrations/` ensures the complete database schema and all RLS policies can be re-provisioned deterministically from scratch into a fresh PostgreSQL instance at any time via `supabase db push`.

---

## 12. Stage 1 Sign-Off & Next Actions

This completes the Stage 1 Architecture and Migration Design.

### Actions Deferred to Stage 2 (Awaiting User Approval):
1. Initialize the Git repository in `E:\UWearNova` with an initial commit of the baseline code.
2. Setup Supabase project configuration files (`supabase/config.toml`, `supabase/migrations/`).
3. Formulate the consolidated SQL schema migration containing all 50 tables, indexes, constraints, and RLS policies.
4. Validate build compatibility of Next.js 15.1.0 with the chosen serverless adapter.

> [!IMPORTANT]
> **Stage 1 design is complete.** No files outside of documentation have been modified. Please review this design document and provide approval to proceed to **Stage 2 (Supabase Foundation & Schema Implementation)**.
