# UniNova Security Review & Vulnerability Assessment (M31)

**Audit Date:** November 2026  
**Scope:** UniNova E-Commerce Platform (FastAPI Backend, Next.js Frontend, MySQL Database, Docker Architecture)  
**Status:** Audit Completed & In-Scope Remediations Applied

---

## 1. Executive Summary

A comprehensive security review was conducted across the UniNova application codebase to evaluate authentication, authorization (RBAC), API security, commerce logic, media handling, and infrastructure readiness prior to local containerization and staging/production deployment.

No critical, unmitigated remote code execution (RCE) or direct SQL injection vulnerabilities exist in the application. Critical safeguards have been verified and tightened:
- Secret keys and default database credentials are now strictly validated against production deployment.
- Unhandled exceptions are globally caught to prevent database error and stack trace leakage.
- Commerce calculations (prices, discounts, shipping fees) are strictly authoritative on the backend.

---

## 2. Authentication & Credential Management

| Component | Architecture & Controls | Assessment |
|---|---|---|
| **Password Hashing** | Uses `Argon2id` via the `argon2-cffi` library (`time_cost=3`, `memory_cost=64MB`, `parallelism=4`, `salt_len=16`). Compliant with OWASP guidelines. | **SECURE** |
| **Access Tokens** | Short-lived JSON Web Tokens (HS256) with 30-minute default expiration containing `sub`, `user_type`, `iat`, `exp`, and `type="access"` claims. | **SECURE** |
| **Refresh Tokens** | High-entropy 36-byte cryptographically secure random tokens (`secrets.token_urlsafe(36)`). Raw tokens are returned to clients; only SHA-256 hashes are persisted in the database (`refresh_tokens.token_hash`). | **SECURE** |
| **Token Revocation** | Dedicated `/api/v1/auth/customer/logout` and `/api/v1/auth/staff/logout` endpoints revoke active refresh tokens immediately by marking them revoked or deleting them. | **SECURE** |
| **Password Reset** | Cryptographic one-time reset tokens with 60-minute expiration, invalidated upon successful password reset. | **SECURE** |

---

## 3. Authorization & Role-Based Access Control (RBAC)

| Control Area | Implementation Details | Assessment |
|---|---|---|
| **Customer Ownership** | Customer endpoints (`/api/v1/customers/me`, `/orders/me`, `/cart`, `/wishlist`, `/returns`) strictly bind database queries to `current_customer.id` resolved from verified access tokens. Customers cannot read or mutate other customers' data. | **SECURE** |
| **Administrative & Staff Roles** | Staff roles (`admin`, `order_manager`, `fulfillment_staff`, `inventory_manager`, `customer_support`, `catalog_editor`, `finance_operator`) are validated via `require_staff_roles(...)` and permission helper functions. | **SECURE** |
| **Privilege Escalation** | Staff creation and role assignments are restricted exclusively to `admin` users. Non-admin staff cannot promote themselves or alter permissions. | **SECURE** |
| **Least Privilege Workqueues** | Staff members only have access to endpoints and workqueues matching their assigned roles (e.g. `catalog_editor` cannot initiate refunds or alter COD statuses). | **SECURE** |

---

## 4. API & Application Security

| Threat / Control | Mitigation Mechanism | Assessment |
|---|---|---|
| **SQL Injection (SQLi)** | 100% of database queries use SQLAlchemy 2.0 ORM expressions (`select()`, `insert()`, `update()`, `delete()`) with parameterized variable bindings. Zero raw string concatenation in SQL queries. | **SECURE** |
| **Cross-Site Scripting (XSS)** | Backend operates as pure JSON REST API (`application/json`). Frontend utilizes React/Next.js JSX auto-escaping; no `dangerouslySetInnerHTML` is used for untrusted user inputs. | **SECURE** |
| **Cross-Origin Resource Sharing (CORS)** | `CORSMiddleware` configured with explicit origin allowlist loaded from `CORS_ORIGINS` environment variable (defaults to `http://localhost:3000`). Wildcard `*` in production is disallowed. | **SECURE** |
| **Input Validation** | All request payloads and query parameters are strictly typed and validated using Pydantic v2 schemas. Invalid types or unexpected fields return standard `422 VALIDATION_ERROR`. | **SECURE** |
| **Information Leakage** | Exception handlers in `app/common/errors.py` catch all unhandled `Exception` instances and return sanitized `500 INTERNAL_SERVER_ERROR` payloads without exposing Python traces or SQL operational errors. | **REMEDIATED** |

---

## 5. Commerce & Business Logic Security

| Risk | Mitigation Mechanism | Assessment |
|---|---|---|
| **Client-Side Price Manipulation** | Frontend submits only `variant_id` and `quantity`. Order line prices are looked up directly from the database `product_variants` and `products` records during checkout. | **SECURE** |
| **Discount / Coupon Tampering** | Discounts are calculated exclusively server-side. Promotion validity, expiry dates, minimum order thresholds, and usage limits are verified in database transactions. | **SECURE** |
| **Duplicate Checkout / Race Conditions** | Checkout endpoint accepts optional `Idempotency-Key` header, caching order results to prevent duplicate payment / charge creation. Stock checks verify available inventory prior to order reservation. | **SECURE** |
| **Cash on Delivery (COD) Integrity** | COD orders are placed in `payment_status="pending"` and `order_status="placed"`. COD cannot be marked `paid` without staff/admin operational reconciliation (`POST /api/v1/orders/{order_number}/payments/cod-confirm`). | **SECURE** |
| **Refund Authorization** | Refunds are guarded by `admin` or `finance_operator` roles, requiring audit notes and verifying that order payment was previously collected. | **SECURE** |

---

## 6. Media & File Upload Security

| Threat / Control | Mitigation Mechanism | Assessment |
|---|---|---|
| **File Size Restriction** | Maximum upload size enforced at `10 MB` (`MEDIA_UPLOAD_MAX_BYTES`). Larger payloads are rejected immediately. | **SECURE** |
| **MIME-Type Validation** | Strict allowlist: `image/jpeg`, `image/png`, `image/webp`, `image/avif`. Non-image files (executable scripts, HTML, SVG) are rejected. | **SECURE** |
| **Direct S3 Uploads** | Direct AWS S3 presigned PUT URLs with a short 15-minute time-to-live (`PRESIGNED_URL_EXPIRE_SECONDS = 900`). CloudFront domain CDN delivery ensures private S3 bucket contents are not exposed publicly. | **SECURE** |

---

## 7. Infrastructure & Environment Security

| Control Area | Status & Implemented Safeguards |
|---|---|
| **Secret Key Hardening** | `Settings` model in `app/core/config.py` enforces that in `APP_ENV=production`, `SECRET_KEY` cannot be the development default and must be at least 32 characters long. Default database credentials raise validation errors on production startup. |
| **Credential Storage** | `.env` and `.env.local` are explicitly ignored in `.gitignore`. Sample configuration templates (`.env.example`) provide placeholder documentation without secrets. |
| **Container Isolation** | Docker containers run with unprivileged user permissions where appropriate and isolate database ports within the internal Docker bridge network. |

---

## 8. Remediation Log (M31 Actions Taken)

1. **Production Secret Enforcement:** Added Pydantic `model_validator(mode="after")` to `app/core/config.py` rejecting default `SECRET_KEY` and default `MYSQL_PASSWORD` when `APP_ENV == "production"`.
2. **Global Exception Sanitization:** Added `@app.exception_handler(Exception)` in `app/common/errors.py` returning standard `500 INTERNAL_SERVER_ERROR` JSON payloads to prevent leaking database exception messages or stack traces to clients.
3. **CORS Explicit Origin Parsing:** Validated comma-separated string parsing for `CORS_ORIGINS` to prevent malformed origin configurations.

---

## 9. Unresolved Risks & Operational Recommendations (Pre-M34)

| Risk | Severity | Recommendation for Production Deployment (M34/M35) |
|---|---|---|
| **Distributed Rate Limiting** | Low / Medium | Current in-memory rate limiting operates per process. In multi-container ECS/Fargate deployment, rate limiting should utilize Redis / AWS WAF. |
| **Database Encryption at Rest** | Low | Enable AWS RDS MySQL encryption at rest using AWS KMS managed customer keys (KMS CMK). |
| **Secrets Management** | Low | Migrate production database credentials and JWT secret keys from environment variables to AWS Secrets Manager or AWS SSM Parameter Store with automatic rotation. |
