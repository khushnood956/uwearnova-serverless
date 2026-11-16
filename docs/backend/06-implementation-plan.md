# 06 — Full-Stack Implementation Plan

## Delivery rule

Exactly one module per Antigravity CLI execution. No subagents. No parallel implementation. After completing one module, stop and wait for the user's next instruction. Update this plan only with verified status.

The sequence is dependency-aware. Some module boundaries may be adjusted after repository inspection, but do not merge multiple modules into one execution.

## Phase 0 — Discovery and architecture freeze

| ID | Module | Scope | Acceptance criteria | Status |
|---|---|---|---|---|
| M00 | Repository and architecture audit | Inspect actual frontend, routes, contexts, data types, build scripts, repo structure, current docs; confirm backend location and Next.js runtime | Verified current-state report; no code changes; decisions recorded | Completed |
| M01 | Documentation and workspace setup | Create separate backend docs, backend plan, API/DB/RBAC/AWS docs, env example and project boundaries | Docs remain separate; frontend untouched; plan tracks status | Completed |

## Phase 1 — Backend foundation

| ID | Module | Scope | Acceptance criteria | Status |
|---|---|---|---|---|
| M02 | Backend project scaffold | FastAPI app, settings, logging, error handling, versioned router, health/readiness endpoints | Starts locally; tests pass; OpenAPI available | Completed |
| M03 | MySQL and migrations | Docker MySQL dev service, SQLAlchemy setup, Alembic, connection config, migration test | App connects to MySQL; migration upgrade/downgrade verified | Completed |
| M04 | Identity and authentication | User/customer/staff identity, password hashing, login/logout/session strategy, reset/verification foundations | Auth tests pass; no secrets in client storage | Completed |
| M05 | RBAC and audit foundation | Roles, permissions, route dependencies, audit service | Unauthorized API calls rejected; permission tests cover role matrix | Completed |

## Phase 2 — Core commerce data

| ID | Module | Scope | Acceptance criteria | Status |
|---|---|---|---|---|
| M06 | Categories and collections | Category tree, collection records and public APIs | CRUD permissions; public reads; validation | Completed |
| M07 | Product catalogue | Products, variants, SKU, price, status, attributes and public product APIs | Existing frontend catalogue can be represented; filters/pagination tested | Completed |
| M08 | Product media storage | Storage abstraction, S3 adapter, presigned upload flow, image metadata | Local and AWS configuration documented; access controlled | Completed |
| M09 | Inventory | Stock, reservations, movements, low-stock thresholds | Transaction-safe stock changes; audit/movement history | Completed |
| M10 | Cart and wishlist APIs | Authenticated cart, guest-cart strategy, merge behavior, wishlist sync | No client-supplied price trusted; merge tests pass | Completed |

## Phase 3 — Order lifecycle

| ID | Module | Scope | Acceptance criteria | Status |
|---|---|---|---|---|
| M11 | Shipping configuration and quote | Shipping methods, zones/rules as required, delivery fee quote | Server-calculated quote and validation | Completed |
| M12 | Checkout and order creation | Checkout quote, address snapshot, immutable order items, idempotency, stock transaction | Duplicate submissions do not create duplicate orders | Completed |
| M13 | COD workflow | COD eligibility, confirmation state, delivery collection status, COD reconciliation fields | COD order lifecycle tested end-to-end | Completed |
| M14 | Online payment adapter foundation | Provider interface, webhook verification/deduplication, sandbox integration only after provider selected | No fake payment success; provider-specific behavior isolated | Completed |
| M15 | Fulfillment and shipment tracking | Packing, dispatch, courier adapter interface, tracking events | Valid state transitions and shipment history | Completed |
| M16 | Returns, exchanges and refunds | Request, review, resolution, inventory restock checkpoint, refund adapter boundary | Policy-driven transitions and audit records | Completed |

## Phase 4 — Dashboards and operations APIs

| ID | Module | Scope | Acceptance criteria | Status |
|---|---|---|---|---|
| M17 | Customer account APIs | Profile, addresses, orders, returns, wishlist and security | Ownership isolation tests pass | Completed |
| M18 | Admin catalogue/inventory APIs | Product, category, collection and stock management | Permission matrix enforced | Completed |
| M19 | Admin order/customer/payment APIs | Order queues, customer lookup, payment states and reconciliation views | Sensitive data restricted; audit records created | Completed |
| M20 | Staff operations APIs | Role-specific order, fulfillment, inventory, support and returns work queues | Staff cannot perform unauthorized admin actions | Completed |
| M21 | Promotions/reviews/content APIs | Coupons, reviews, campaigns and content management | Rules validated server-side | Completed |
| M22 | Reports and analytics APIs | Sales, order, inventory and payment aggregates | Aggregates reconcile with source records and date filters | Completed |

## Phase 5 — Frontend integration

| ID | Module | Scope | Acceptance criteria | Status |
|---|---|---|---|---|
| M23 | Typed API client and auth integration | Base client, session handling, errors, loading states | No scattered duplicated API logic | Completed |
| M24 | Public catalogue integration | Replace local catalogue reads incrementally with API-backed data | Existing storefront browsing works | Completed |
| M25 | Cart and wishlist integration | Backend persistence, guest merge and recovery | Existing behavior preserved; cross-device sync for signed-in users | Completed |
| M26 | Customer account dashboard | Customer routes and account workflows | Customer can only access own records | Completed |
| M27 | Admin dashboard UI | Admin navigation, overview, catalogue, inventory, orders, customers, payments, staff, settings | Real API data; permission-aware navigation | Completed |
| M28 | Staff dashboard UI | Role-based work queues and task screens | UI and API enforce same permission policy | Completed |
| M29 | Checkout/payment/shipping integration | Server quote, COD, selected online provider sandbox, tracking | Full test order lifecycle works | Completed |
| M30 | Operational content and policy pages | Shipping/returns/FAQ/contact and relevant content backed by configured data where needed | No contradictory hardcoded policy values | Completed |

## Phase 6 — Quality and AWS deployment

| ID | Module | Scope | Acceptance criteria | Status |
|---|---|---|---|---|
| M31 | Security and privacy review | Auth, RBAC, CSRF/CORS, rate limits, validation, secrets, uploads, OWASP checks | Findings documented and critical issues fixed | Completed |
| M32 | Automated test coverage | Unit, API integration, MySQL integration, frontend component and E2E flows | Critical journeys pass in CI | Completed |
| M33 | Docker and local environment | Reproducible frontend/backend/MySQL setup; optional Redis only if used | Clean-machine setup documented and tested | Completed |
| M34 | AWS infrastructure as code | VPC, networking, RDS, S3, ECR, ECS, frontend hosting, IAM, secrets, logs | Staging infra reproducible from code | Completed |
| M35 | CI/CD and staging deployment | Automated build, tests, image publish, migrations, deploy, smoke tests, rollback | Repeatable staging deployment | Completed |
| M36 | Production readiness and launch | Domain/TLS, backups/restore, alarms, budgets, security, provider/courier live configuration | Go-live checklist signed off; rollback/restore procedures tested | Completed |

## Rules for module status

- `Pending`: not started.
- `In Progress`: currently being implemented.
- `Blocked`: dependency or external decision prevents completion.
- `Completed`: acceptance criteria actually verified.
- Never mark complete based only on generated code or an agent's assertion.
- Record tests and commands actually run in a separate `IMPLEMENTATION_LOG.md`.
- Do not claim production readiness until M36 is complete and real AWS deployment has been verified.

## External decisions that must not be invented

- Final brand/domain name.
- AWS region and monthly budget.
- Payment provider(s), merchant eligibility, fees and settlement process.
- Courier provider(s), serviceability and API access.
- Return/exchange policy and COD confirmation rules.
- Guest checkout requirements.
- Whether one warehouse or multiple inventory locations are needed.
- Whether staff need MFA at launch.
