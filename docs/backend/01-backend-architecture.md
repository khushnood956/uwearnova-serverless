# 01 — Backend Architecture

## 1. Objective

Build a secure, maintainable and deployable backend for the existing UniNova Next.js storefront. The first release is a modular monolith, not a microservices system. Keep clear domain boundaries so individual modules can be extracted later only if scale or team structure justifies it.

## 2. Selected stack

| Layer | Choice | Notes |
|---|---|---|
| Storefront | Existing Next.js + TypeScript | Preserve existing routes, UI, styling and client state where practical |
| Backend API | Python + FastAPI | REST API, OpenAPI documentation |
| Database | MySQL 8.0-compatible engine | Local Docker for development; Amazon RDS for AWS |
| ORM | SQLAlchemy 2.x | Explicit transactions and relationships |
| Migrations | Alembic | All schema changes version-controlled |
| Validation | Pydantic v2 | Request/response schemas |
| DB driver | `asyncmy` with SQLAlchemy async engine, or a verified compatible MySQL driver | Select one after checking package/runtime compatibility |
| Cache / rate limits | Redis, optional | Add only for a concrete requirement; AWS ElastiCache in production if justified |
| Background jobs | Start with a simple worker abstraction; AWS SQS for durable async work when needed | Do not introduce Celery/Redis/SQS without a defined job requirement |
| Object storage | S3-compatible object storage | Local S3-compatible adapter may be used in development; AWS S3 in production |
| Authentication | Backend-managed customer/staff accounts | Secure HttpOnly cookies for browser sessions where compatible; document CSRF strategy |
| Containerization | Docker | Same app image locally and in AWS |
| Testing | pytest + HTTPX + test MySQL | Test real MySQL behavior, not SQLite-only assumptions |

Pin dependencies and verify versions during implementation. Do not blindly copy versions from old project notes.

## 3. Architecture

```text
Browser
  |
  v
Next.js storefront / dashboards
  |
  | HTTPS + JSON REST API
  v
FastAPI modular monolith
  |-- Authentication and authorization
  |-- Catalog and product variants
  |-- Inventory
  |-- Cart and wishlist
  |-- Checkout and orders
  |-- Payments
  |-- Shipping
  |-- Customers
  |-- Promotions
  |-- Returns and exchanges
  |-- Reviews
  |-- Notifications
  |-- Admin and staff operations
  |
  +---- MySQL (system of record)
  +---- S3 (product and campaign media)
  +---- Optional Redis (cache / rate limits)
  +---- Optional SQS worker (durable asynchronous tasks)
```

## 4. Suggested backend layout

Adapt to the repository after inspection; do not force a rewrite if a sound structure already exists.

```text
backend/
  app/
    main.py
    core/
      config.py
      database.py
      security.py
      dependencies.py
      logging.py
    api/
      v1/
        router.py
    modules/
      auth/
      users/
      customers/
      staff/
      catalog/
      categories/
      inventory/
      cart/
      wishlist/
      checkout/
      orders/
      payments/
      shipping/
      promotions/
      returns/
      reviews/
      notifications/
      analytics/
      audit/
    common/
      errors.py
      pagination.py
      permissions.py
      storage/
      integrations/
  migrations/
  tests/
  Dockerfile
  pyproject.toml
  .env.example
```

Each domain module should own its router, schemas, service logic and data-access code. Avoid giant route files and circular imports. Keep business rules in services, not in HTTP route handlers.

## 5. Engineering rules

- MySQL is the source of truth for transactional business data.
- Use Decimal for money. Never use floating-point arithmetic for prices, taxes, discounts or totals.
- Store monetary amounts in a defined currency context; default store currency is PKR. Store currency codes explicitly where useful.
- Store timestamps in UTC; render in the user's local timezone.
- Use database transactions for order placement, inventory reservation/decrement and payment state changes.
- Use idempotency keys or equivalent deduplication for checkout and payment webhook processing.
- Never trust totals, discounts, stock or role claims sent by the browser. Recalculate on the backend.
- Use explicit response schemas; never serialize ORM objects blindly.
- Validate all uploaded files and use presigned S3 uploads where appropriate.
- Keep secrets out of source control and frontend bundles.
- Log operational events without logging passwords, session tokens, payment secrets or unnecessary personal data.
- Add audit records for sensitive admin/staff actions.
- Use pagination and bounded filters for list endpoints.
- Add indexes based on query patterns and verify with EXPLAIN for important queries.
- Do not introduce microservices, Kubernetes, Kafka, Elasticsearch or other infrastructure without a demonstrated need.

## 6. Authentication and security baseline

- Separate customer and staff authorization capabilities, even if they share the user identity table.
- Hash passwords with Argon2id or another maintained password-hashing algorithm configured appropriately.
- Use secure, HttpOnly, SameSite cookies for browser sessions when the deployment topology supports it; define CSRF protection for state-changing requests.
- If token-based auth is selected, implement short-lived access tokens, refresh rotation, revocation and secure storage. Do not store long-lived tokens in localStorage.
- Enforce authorization on every protected backend endpoint. Hiding UI controls is not authorization.
- Rate-limit login, password reset, checkout-sensitive and public form endpoints.
- Add account lockout/throttling carefully to avoid denial-of-service abuse.
- Verify email ownership before enabling sensitive account operations if email verification is part of the release.
- Staff accounts must support disable/revoke actions and role/permission changes.
- Record login and security events without exposing credentials.
- Use OWASP ASVS / API Security Top 10 as a review checklist.

## 7. Payment and courier integration boundaries

Implement provider interfaces/adapters. Do not hardcode one provider before merchant availability, fees, settlement behavior and Pakistan support are verified.

Payment adapter responsibilities:
- Create/initialize payment where applicable.
- Verify provider callback/webhook signatures.
- Normalize provider statuses.
- Persist provider reference IDs and reconciliation data.
- Make webhook processing idempotent.
- Never store raw card data.

COD is a first-class payment method with configurable order confirmation and verification rules. COD orders must not be marked paid merely because they were placed.

Courier adapter responsibilities:
- Serviceability check where supported.
- Shipment/consignment creation.
- Label/reference storage.
- Tracking status normalization.
- Cancellation/return support where provider APIs allow it.

The store must remain usable with COD even if no online payment provider has been selected.

## 8. Definition of backend readiness

Backend readiness requires migrations, tests, documented environment variables, health/readiness endpoints, secure configuration, API documentation, container build, integration with the real frontend and a repeatable deployment procedure. A successful local build alone is not production readiness.
