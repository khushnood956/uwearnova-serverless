# UniNova: Full Supabase + Cloudflare Migration

**Purpose:** Complete architectural migration of the existing UniNova e-commerce application.  
**Strategy:** Replace FastAPI + MySQL with Supabase; retain and adapt the existing Next.js application.  
**Initial budget target:** Under US$5/month, using free allowances where practical.  
**Traffic estimate:** Under 1,000 visitors/month initially; under 5,000 after early marketing.  
**Status:** Target architecture and implementation specification. This document does not imply that migration or deployment has occurred.

---

## 1. Objective and non-negotiable constraints

Migrate the existing application to:

- Next.js for storefront, admin UI and application/server-side layer.
- Supabase PostgreSQL as the sole application database.
- Supabase Auth for customer and staff authentication.
- PostgreSQL Row Level Security (RLS) for data access control.
- Cloudflare R2 for product images and other media.
- Cloudflare DNS, SSL and CDN.
- Cloudflare Pages/Workers for hosting, only after testing compatibility with the exact existing Next.js application.

This is a **full migration**. The final live application must not depend on FastAPI or MySQL.

Preserve existing UI, business rules, customer workflows and admin functionality wherever valid. Do not redesign the website or remove features merely because the backend is changing.

### Existing project context

- The user has a separate copied project containing the same frontend/backend code and has connected that copy to GitHub.
- A basic frontend deployment is live through GitHub Pages from the copied codebase.
- The domain is already owned/managed through Cloudflare.
- The existing live site must remain untouched while migration and staging occur.
- Work only in the designated copied migration workspace.
- Do not assume Terraform files mean AWS infrastructure is deployed.
- Do not assume Docker is running; the local Docker Engine previously failed to connect.
- Previous reports disagreed about the Git repository state. Verify `Test-Path .git`, `git status` and `git log -1` in the actual workspace before relying on any report.
- Do not overwrite, delete or clean up the original project or its backup.

## 2. Traffic and budget assumptions

| Stage | Planning estimate |
|---|---:|
| Initial, no active marketing | Under 1,000 visitors/month |
| After early marketing | Under 5,000 visitors/month |

These are estimates, not guaranteed limits. Visitors are not equivalent to page views, database requests, image requests or orders. Monitor actual consumption.

### Initial cost target

| Component | Initial plan | Target |
|---|---|---:|
| Next.js hosting | Cloudflare Pages/Workers free allowance, if compatible | $0 |
| PostgreSQL | Supabase Free | $0 |
| Authentication | Supabase Auth within free limits | $0 |
| Media | Cloudflare R2 within free allowance | $0 |
| DNS, SSL, CDN | Cloudflare Free | $0 |
| Email | Defer paid integration until needed; assess free allowance | $0 initially |
| **Total target** | | **Under $5/month** |

This is a target, not a guarantee. Verify current official pricing, quotas and regional availability before provisioning. Do not silently add paid services.

**Free-tier trade-offs:** Supabase Free projects may pause after inactivity and do not provide the same backup/recovery guarantees as paid production plans. Free quotas can be exceeded. Before accepting meaningful customer orders, evaluate paid database hosting and independent backups. Do not sacrifice data durability merely to keep the bill below $5.

## 3. Target architecture

```text
Customer / Staff Browser
          |
          | HTTPS
          v
Cloudflare DNS + SSL + CDN
          |
          v
Next.js application
Cloudflare Pages / Workers (after compatibility test)
          |
          +------ Supabase
          |         |-- PostgreSQL
          |         |-- Supabase Auth
          |         |-- Row Level Security
          |         |-- SQL functions / RPC
          |         |-- Edge Functions where appropriate
          |
          +------ Cloudflare R2
          |         |-- Product images
          |         |-- Banners and category media
          |
          +------ External providers when configured
                    |-- Transactional email
                    |-- Payment gateway
                    |-- Courier integration
```

| Responsibility | Target owner |
|---|---|
| Storefront/admin UI | Existing Next.js app |
| Server-rendered pages | Next.js runtime |
| HTTP application endpoints | Next.js Route Handlers |
| Suitable form mutations | Next.js Server Actions |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| Row-level authorization | PostgreSQL RLS |
| Atomic business operations | PostgreSQL functions/RPC |
| Asynchronous/external tasks | Supabase Edge Functions or Cloudflare Workers, chosen by workload |
| Product media | Cloudflare R2 |
| DNS/SSL/CDN | Cloudflare |
| Email/payment/courier | External providers when actually configured |

Avoid unnecessary microservices, Kubernetes, Redis, brokers or multiple always-on servers. The expected traffic does not justify that complexity by default.

## 4. Hosting compatibility gate

The existing project has previously been reported to use Next.js 15.1.0, React 19, TypeScript 5.7.2 and Tailwind 3.4.16. Verify actual versions from `package.json` and the lockfile.

Before choosing a Cloudflare adapter:

1. Inspect SSR, dynamic routes, Route Handlers, Server Actions, middleware, image optimization, Node-specific APIs, filesystem access, native dependencies and runtime assumptions.
2. Read current official Cloudflare documentation for supported Next.js versions and deployment options.
3. Test the exact existing version and app in staging.
4. Verify build, runtime, caching, environment variables, Supabase server-side access and image delivery.
5. Document incompatibilities and the smallest safe fixes.

Do not assume every Next.js 15.x version works with every adapter. If Next.js 15.1.0 is incompatible, evaluate the smallest safe upgrade within Next.js. Do not switch frameworks or adopt an experimental adapter without documenting the risks and obtaining approval.

If Cloudflare cannot reliably host the existing application within budget, present the lowest-cost viable alternative before changing architecture.

## 5. MySQL to PostgreSQL migration

Supabase PostgreSQL becomes the only live application database after cutover.

### Inventory and schema conversion

Inspect every SQLAlchemy model, table, column, index, unique constraint, foreign key, relationship, enum, trigger, view, query and Alembic migration. Determine the actual current schema rather than assuming the migrations describe the live database.

Map MySQL types and behavior to PostgreSQL equivalents. Review:

- Auto-increment/identity behavior.
- Timestamp and timezone semantics.
- Decimal precision and currency calculations.
- JSON fields.
- Collation and case sensitivity.
- Nullability and defaults.
- Foreign-key and delete behavior.
- MySQL-specific SQL syntax.

Use version-controlled Supabase SQL migrations. Add appropriate constraints and indexes based on real query patterns, particularly catalogue filters, product lookup, orders, inventory, customers and admin queues.

Recommended defaults for new schema elements:
- UUID primary keys unless compatibility requires preserving existing IDs.
- `timestamptz` for real-world timestamps.
- `numeric(precision, scale)` for money; never floating point for monetary values.
- Explicit currency handling, with PKR as the default only if consistent with existing business rules.
- Foreign keys, unique constraints and check constraints where appropriate.
- UTC internally.

Do not blindly convert the schema. Preserve business semantics and document deliberate changes.

### Data migration rehearsal

1. Export a safe copy of existing MySQL data.
2. Import into a disposable/staging Supabase project.
3. Preserve relevant customers, products, variants, inventory, orders, order items, coupons, reviews, addresses and staff data.
4. Reconcile row counts per table.
5. Verify foreign-key relationships and orphan records.
6. Compare financial totals and inventory quantities.
7. Manually inspect representative records.
8. Record exceptions and resolutions.
9. Repeat until the process is reliable.

Never delete or alter the original MySQL database during rehearsal.

## 6. Authentication: custom JWT to Supabase Auth

Supabase Auth replaces the old custom authentication service. Preserve customer and staff login, registration, session persistence/refresh, logout, account status, password reset and staff authorization behavior.

The old backend has previously been reported to use Argon2id and PyJWT. Verify the actual implementation and stored hash format.

### Password migration

Supabase supports password-hash import workflows for supported formats, but compatibility must be tested against the exact Argon2 encoding and parameters.

1. Inspect algorithm, parameters and encoded hash format.
2. Verify compatibility with Supabase's currently supported import format.
3. Test using a disposable account.
4. Confirm the existing password authenticates.
5. If incompatible, design a secure staged migration or password-reset process.
6. Never export/log plaintext passwords or use reversible/weak replacements.

### Roles and permissions

Authentication is not authorization.

- Supabase Auth identifies the user.
- RLS enforces row-level access.
- Server-side code protects privileged workflows.
- Role/permission data must come from trusted database records or securely managed claims.
- Never trust browser-supplied roles, user IDs, prices, discounts or ownership.
- Users must not be able to update their own role or permission records.
- Preserve the existing granular staff permission model; do not collapse all staff into one generic admin role.
- Keep service-role credentials out of browser bundles.

## 7. RLS and database privileges — mandatory

Enable RLS on every table exposed through the Supabase API. Default to deny.

Policy principles:
- Customers access only their own private records.
- Customers can read only public/active catalogue data intended for public use.
- Customers cannot edit product prices, inventory, order status, payment status or staff records.
- Staff access follows the existing role/permission matrix.
- Admin access is appropriately scoped.
- Anonymous users cannot read private customer, order or staff data.
- Hiding a UI control is never an authorization boundary.

Test each relevant table using:
1. Anonymous user.
2. Customer A.
3. Customer B.
4. Staff with limited permissions.
5. Staff with relevant permissions.
6. Administrator.
7. Expired/revoked session.

Prove Customer A cannot read or modify Customer B's records through direct API requests as well as the UI.

Never expose the service-role key. Prefer narrowly scoped SQL functions and server-side operations. For any `SECURITY DEFINER` function, use a safe `search_path`, validate the caller and inputs, and grant execution only to intended roles. Review SQL grants as well as RLS policies.

## 8. Replace FastAPI business logic

Use the smallest suitable combination of:
- Supabase client queries for safe, policy-governed access.
- Next.js Route Handlers for server-side HTTP endpoints and integrations.
- Server Actions for appropriate application mutations.
- PostgreSQL functions/RPC for atomic database workflows.
- Supabase Edge Functions or Cloudflare Workers for suitable asynchronous/external tasks.

Do not mechanically create one function per old endpoint. Inventory frontend dependencies and preserve required API behavior.

### Transactional operations

At minimum, review and implement atomic transactions for:
- Checkout and order creation.
- Inventory reservation/deduction.
- Coupon validation/redemption.
- Order cancellation and stock restoration.
- Returns/exchanges where stock or financial records change.
- Payment confirmation and order status transitions.
- Refund records, if supported.

Checkout must validate product/variant availability and price using trusted data, calculate totals server-side, create order and order items, and reserve/deduct stock atomically. Failure must roll back the transaction. Concurrent checkouts must not oversell stock.

Never trust browser-supplied prices, discounts, shipping charges or final totals.

### API security

- Validate inputs with schemas.
- Enforce authentication and authorization server-side.
- Rate-limit login, password reset, checkout and abuse-prone operations.
- Avoid leaking stack traces or database details.
- Use safe errors and structured logs.
- Never log passwords, tokens, payment secrets or unnecessary sensitive customer data.

## 9. Cloudflare R2 media

R2 stores the actual image files. PostgreSQL stores object keys and metadata, not image binaries.

Suggested bucket: `product-media`  
Suggested media domain: `images.<owned-domain>`

Confirm the real domain before configuration.

Suggested object keys:

```text
products/{product_id}/{image_id}.webp
products/{product_id}/variants/{variant_id}/{image_id}.webp
categories/{category_id}/{image_id}.webp
banners/{banner_id}/{image_id}.webp
brands/{brand_id}/{image_id}.webp
```

Use generated stable object keys, not raw customer-provided filenames.

Store relevant metadata in PostgreSQL:
- Object key.
- Media type and file size.
- Width and height.
- Alt text.
- Display order and primary-image flag.
- Related product/category/banner ID.
- Created timestamp.

### Secure upload flow

1. Authorized staff member requests upload.
2. Next.js server validates session, role and permission.
3. Server validates file type, actual file content, size and dimensions.
4. Server generates a short-lived R2 presigned upload URL or uses a secure server-mediated upload.
5. Browser uploads directly to R2 using the temporary URL.
6. Server verifies the upload and records metadata in PostgreSQL.

R2 credentials must never be sent to the browser. Public access should be enabled only for intended storefront assets. Use signed access for private media if required.

Implement safe replacement/deletion so database records and R2 objects do not become inconsistent. Use modern formats/responsive sizes where supported, lazy-load below-the-fold images, and configure appropriate caching. Keep the media base URL configurable.

### Existing image migration

Inventory all current media sources. Copy images to R2 without deleting the source. Verify object counts, sizes and retrieval. Update database keys/URLs, test catalogue/product/admin pages and retain a rollback mapping until accepted.

## 10. Email, payments and courier services

Do not present simulated integrations as operational.

### Email
The previous audit identified missing/incomplete outbound email delivery. A stored reset token does not send an email.

When configured:
- Select a transactional provider based on current price and regional availability.
- Verify sender/domain.
- Store API keys server-side.
- Implement templates for password reset, order confirmation and status changes.
- Handle retries and provider failures without duplicate messages.
- Do not claim an email was sent until provider acceptance.

### Payments
- Preserve Cash on Delivery if it is already supported.
- A mock payment provider is not a live integration.
- Add a real gateway only after credentials, callback/webhook requirements and reconciliation rules are available.
- Verify webhooks server-side and make processing idempotent.
- Never mark an order paid based only on a browser redirect.

### Courier
Simulated tracking is not live tracking. Integrate a courier only when API access and credentials exist. Validate webhook events and store provider references/tracking events.

## 11. Frontend integration and performance

Preserve the existing visual design and workflows. Replace the data/authentication layer.

Inventory:
- Every frontend API call and its FastAPI endpoint.
- localStorage/sessionStorage usage.
- Static/mock fallbacks and simulated actions.
- Customer and admin routes.
- Existing image URL and upload logic.

Replace old API calls and JWT/session handling. Ensure privileged operations execute server-side. Preserve loading, empty, error and success states. Connect catalogue, variants, cart, wishlist, checkout, account and admin features to real data. Remove production mock fallbacks only after the corresponding real implementation passes tests.

Performance requirements:
- Use SSR/SSG where appropriate.
- Cache public catalogue data carefully.
- Never publicly cache private customer/admin responses.
- Avoid unnecessary client-side database requests.
- Paginate large admin lists.
- Index real filters/sorts.
- Optimize and lazy-load product images.
- Avoid unnecessary large dependencies.
- Measure Core Web Vitals after deployment.

## 12. Environments and secrets

Maintain separate local, staging and production configuration.

Illustrative variables (confirm exact SDK requirements):

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY

SUPABASE_SERVICE_ROLE_KEY       # server only
CLOUDFLARE_ACCOUNT_ID
R2_ACCESS_KEY_ID                # server only
R2_SECRET_ACCESS_KEY            # server only
R2_BUCKET_NAME
R2_PUBLIC_BASE_URL

EMAIL_PROVIDER_API_KEY           # when configured
PAYMENT_PROVIDER_SECRET          # when configured
```

Rules:
- Never commit real secrets.
- Never use `NEXT_PUBLIC_` for a secret.
- Keep actual `.env` files out of Git.
- Keep `.env.example` placeholders only.
- Configure secrets separately in each environment.
- Rotate any credential that may have been exposed.
- Never print secret values in logs/reports.

## 13. Migrations and development workflow

Use Supabase CLI and version-controlled SQL migrations. Suggested structure (adapt to the actual repo):

```text
supabase/
  config.toml
  migrations/
  seed.sql
```

Every schema change must be represented by a migration. Do not rely only on manual dashboard edits. Migrations must work on a clean staging project. Seed data is for development/test only; never commit real customer data. Review migration SQL before production use.

Keep staging and production Supabase projects separate.

## 14. Testing and acceptance

A successful frontend build is not proof of a successful migration. Test complete business workflows and security boundaries.

### Build
- TypeScript checks pass.
- Lint checks pass.
- Production build succeeds.
- No unresolved imports or missing required environment variables.
- No production workflow uses mock backend data.
- No secrets appear in client bundles.

### Authentication and authorization
- Registration/login, refresh and logout work.
- Existing customer migration strategy is verified.
- Password reset works once email is configured.
- Disabled users cannot perform privileged operations.
- Staff roles and permissions are preserved.
- Anonymous access is appropriately restricted.
- Customer A cannot access Customer B's private data.
- Customers cannot modify prices, stock, order/payment status or staff permissions.
- Limited staff cannot perform unauthorized actions.
- Direct API calls cannot bypass intended permissions.

### Commerce
- Catalogue, products and variants load from PostgreSQL.
- Cart totals use trusted product data.
- Coupon rules are enforced server-side.
- Checkout creates a consistent order.
- Concurrent checkout cannot oversell stock.
- Failed checkout rolls back partial writes.
- Order history is customer-scoped.
- COD works if supported.
- Mock payment is clearly unavailable until replaced.

### Media
- Authorized staff can upload images.
- Images serve through the intended media domain.
- Unauthorized users cannot upload/delete.
- Images persist across refresh/deployment.
- Replacement/deletion leaves consistent metadata.
- Mobile image loading is acceptable.

### Admin
Test every existing module intended to remain, such as products, categories, inventory, orders, coupons, customers, reviews, CMS, analytics, POS, returns/exchanges and staff management, where present.

For each feature, report one status:
- Implemented and runtime-tested.
- Implemented but not runtime-tested.
- Partially implemented.
- Simulated/placeholder.
- Not implemented.

### Deployment
- Staging deploy succeeds over HTTPS.
- Environment variables are correct.
- No secrets are exposed.
- Logs/errors are usable.
- DNS rollback plan exists.
- Existing live site remains available until approval.

## 15. Deployment, DNS and rollback

### Before cutover
1. Deploy to staging using a staging Supabase project and R2 configuration.
2. Run all acceptance tests.
3. Test mobile and desktop.
4. Test admin workflows with separate roles.
5. Verify media delivery.
6. Reconcile database row counts, financial totals and stock.
7. Confirm backup/export and restore procedure.
8. Record current DNS records and GitHub Pages configuration.
9. Prepare rollback steps.

### Cutover
- Change DNS only after explicit user approval.
- Preserve the old GitHub Pages deployment and source.
- Do not delete old hosting configuration during cutover.
- Monitor errors, checkout success, database load and image delivery.
- Restore previous DNS target if a critical issue requires rollback.

No DNS change is part of routine code migration.

## 16. Backups and recovery

Before launch:
- Document database export and backup procedures.
- Store backups securely outside the database project.
- Test restore against a disposable project.
- Preserve SQL migrations/schema in Git.
- Document R2 object inventory and media backup strategy.
- Keep recovery credentials under owner control.
- Define backup frequency and retention.

Do not claim backups are configured until a backup exists and a restore test succeeds.

## 17. Cost and monitoring

Monitor:
- Supabase database size and compute.
- API usage and egress.
- Auth usage.
- R2 storage and operations.
- Cloudflare Workers/Pages usage.
- Image bandwidth/cache hit rate.
- Email volume.
- Failed logins and suspicious traffic.
- Checkout failures and database errors.

Set alerts before plan limits. At the expected traffic level, optimize for simplicity and low fixed cost. Upgrade only when actual usage, reliability or security needs justify it.

## 18. Do not misrepresent functionality

Previously identified risks that must be re-verified:
- Mock payment is not live payment processing.
- Simulated courier tracking is not live tracking.
- Stored password-reset tokens do not prove email delivery.
- TypeScript compilation does not prove backend workflows.
- Terraform files do not prove AWS resources are deployed.
- A successful database connection does not prove RLS is secure.
- A successful upload does not prove permissions and deletion are correct.

Do not remove functionality without documenting the impact and obtaining approval.

## 19. Strict rules for the implementation agent

1. Work only in the designated copied migration workspace.
2. Inspect actual code before proposing or changing it.
3. Do not assume paths, models, endpoints, schema or environment variables.
4. Do not rewrite the whole application in one pass.
5. Do not make unrelated UI redesigns.
6. Do not remove business features to simplify migration.
7. Do not modify the existing live GitHub Pages deployment or primary DNS.
8. Do not delete FastAPI, MySQL, old migrations or old configuration until the replacement is tested and approved.
9. Do not add paid services without explaining recurring cost and receiving approval.
10. Never expose service-role, R2, payment or email secrets.
11. Never bypass RLS to make a feature work.
12. Never trust client-supplied prices, totals, discounts, stock or roles.
13. Do not claim tests passed unless actually executed and output inspected.
14. Do not claim runtime verification based only on static inspection or compilation.
15. Do not silently change framework or hosting adapter.
16. Keep changes small, reviewable and reversible.
17. Update documentation and environment examples.
18. After each stage, report changed files, commands, test results, unresolved issues and risks.
19. Stop for approval before destructive operations, production data changes, DNS changes or infrastructure removal.
20. If requirements are ambiguous, inspect and report rather than inventing behavior.

## 20. Staged execution plan

Do not execute all stages in one pass. Complete each stage, report results and wait for approval before the next stage.

### Stage 0 — Read-only discovery (start here)

Produce:
- Actual repository and Git status.
- Verified framework/runtime versions.
- Frontend route and API-call inventory.
- FastAPI endpoint inventory.
- SQLAlchemy model/table inventory.
- Authentication/RBAC inventory.
- Media/image storage inventory.
- Environment variable names only (never values).
- Mock/simulated functionality inventory.
- Hosting/runtime compatibility assessment.
- Risks, unknowns and dependencies.

**No code changes, package installs, migrations, cloud resources, DNS changes or deletions.**

### Stage 1 — Architecture and migration design

Produce:
- Final target architecture.
- MySQL-to-PostgreSQL mapping.
- Authentication/password migration plan.
- RLS policy matrix by table and role.
- API/business-logic replacement matrix.
- R2 bucket/object-key/upload design.
- Hosting compatibility decision.
- Environment/secret plan.
- Current-pricing-based cost estimate.
- Backup and rollback plan.

Wait for approval before provisioning or modifying resources.

### Stage 2 — Supabase foundation

Create a separate staging Supabase project. Configure Auth, SQL migrations, schema, indexes, constraints and RLS. Add safe test data. Test policies for anonymous, customer and staff roles. Do not import production data yet.

### Stage 3 — Data migration rehearsal

Export a safe data copy, transform and import into staging, reconcile counts/relationships/financial totals/stock, test sample password migration, document incompatibilities and repeat until reliable.

### Stage 4 — Backend replacement

Replace FastAPI-dependent operations with secure Next.js server operations, Supabase queries and transactional PostgreSQL functions. Add validation, authorization, rate limits and safe logs. Run integration tests.

### Stage 5 — R2 integration

Configure staging R2 bucket and media domain, secure uploads, migrate sample media, verify display/cache/replacement/deletion. Keep old media intact until acceptance.

### Stage 6 — Frontend integration

Replace old API and auth handling while preserving UI. Connect required customer/admin workflows. Remove production mock fallbacks only after real implementations pass tests. Verify responsive behavior and performance.

### Stage 7 — Staging acceptance

Run all tests in Section 14. Produce a feature-by-feature verification report. Resolve critical/high-severity issues before proceeding.

### Stage 8 — Production preparation and cutover

Create production resources, apply reviewed migrations, migrate final data/media, configure secrets, deploy, run acceptance checks and obtain explicit approval. Change DNS only after approval. Monitor and retain rollback capability.

### Stage 9 — Retire old backend

Only after stable production operation and explicit approval:
- Take final backups/exports.
- Confirm no live frontend or scheduled task calls FastAPI.
- Confirm no required data exists only in MySQL.
- Archive old backend source and migration history.
- Remove obsolete deployed services only after an agreed retention/rollback period.
- Never delete the old project copy or backups.

## 21. Definition of done

Migration is complete only when:
- Storefront/admin run on the new hosting architecture.
- Supabase PostgreSQL is the sole live application database.
- Supabase Auth replaces custom authentication.
- RLS and server-side authorization pass negative security tests.
- Required customer/staff workflows use the new architecture.
- Checkout and inventory are transactionally safe.
- Product media is stored/served through R2.
- No production workflow depends on FastAPI or MySQL.
- Simulated integrations are not represented as real.
- Staging and production pass acceptance tests.
- Backup and restore procedures have been tested.
- DNS cutover was explicitly approved and completed.
- Old system is retained safely until the new system is stable.
- Actual usage and monthly cost are measured and documented.

---

## 22. First instruction to the coding agent

**Start with Stage 0 only.**

Perform a read-only audit of the copied UniNova repository and produce the discovery report specified in Stage 0. Do not edit files, install packages, run migrations, create cloud resources, change DNS, delete code or modify deployment settings.

Clearly distinguish:
- Verified facts from assumptions.
- Implemented features from simulated features.
- Static checks from runtime-tested behavior.
- Existing deployment from merely defined infrastructure.
- Confirmed compatibility from compatibility that still needs testing.

After presenting the report, stop and wait for approval before Stage 1.
