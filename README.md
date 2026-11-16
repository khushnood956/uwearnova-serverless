# UniNova — Modern Fashion E-Commerce Platform

A production-engineered, luxury fashion e-commerce platform built with **Next.js 15 (App Router)**, **FastAPI (Modular Monolith)**, **MySQL 8.0**, and **AWS ECS Fargate**.

---

## Architecture Overview

```text
                                [ User / Browser ]
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼ (Port 3000)                           ▼ (Port 8000)
         [ Next.js Storefront ]                  [ FastAPI REST API ]
          - App Router (React 19)                 - Modular Monolith
          - Server & Client Components            - Pydantic v2 & SQLAlchemy 2.0
          - Tailwind CSS Design System            - Argon2id & PyJWT Auth
                    │                                       │
                    │                                       ▼ (Port 3306)
                    │                             [ MySQL 8.0 Database ]
                    │                              - InnoDB Foreign Keys
                    │                              - Decimal PKR Currency
                    │                                       │
                    └───────────► [ S3 / CloudFront CDN ] ◄─┘
                                   - Private Bucket (OAC)
                                   - Presigned Uploads
```

---

## Key Features

- **Storefront & Dynamic Categories:**
  - Multi-tier department hierarchy (Men, Women, Kids, Footwear, Accessories, Perfumes).
  - Database-driven categories with "Coming Soon" toggles and active filtering.
  - Persistent cart, saved wishlist, and search with responsive filters.

- **Cash on Delivery (COD) & Authoritative Pricing:**
  - Authoritative server-side price, coupon, and shipping calculation.
  - First-class COD payment flow: orders initialize as `placed` and `pending`, requiring staff/admin reconciliation upon courier delivery.
  - Idempotent checkout preventing duplicate charges or orders.

- **Authenticated Dashboard Ecosystem:**
  - **Customer Portal (`/account`):** Orders, status timeline, address book, 7-day returns, profile preferences, and security.
  - **Staff Workspaces (`/staff`):** Role-tailored queues for fulfillment packing/dispatch, warehouse stock intake, and customer support.
  - **Store Admin (`/admin`):** Catalogue management with **inline subcategory creation**, order status transitions, COD reconciliation, customer account management, and real-time sales reports.

- **Security & Integrity:**
  - OWASP-grade Argon2id password hashing and SHA-256 hashed refresh tokens.
  - Strict `APP_ENV` validation rejecting missing, empty, or unlisted environments.
  - Production secret key and database credential hardening.
  - Global unhandled exception sanitization preventing information leakage.

---

## Repository Structure

```
uninova/
├── .github/
│   └── workflows/
│       ├── frontend-gh-pages.yml      # Automated GitHub Pages static frontend deployment
│       ├── ci.yml                     # PR & push validation (pytest + next build)
│       ├── deploy-staging.yml         # Staging deployment via AWS IAM OIDC
│       └── deploy-production.yml      # Production release gate with circuit breaker
├── frontend/                          # Next.js 15 Storefront & Dashboards
│   ├── src/
│   │   ├── app/                       # Next.js App Router pages & layouts
│   │   ├── components/                # Reusable React UI components
│   │   ├── context/                   # Auth, Cart, Wishlist providers
│   │   ├── lib/                       # Typed API clients & utility functions
│   │   └── types/                     # TypeScript interfaces & domain schemas
│   ├── public/                        # Static assets, branding & .nojekyll
│   ├── Dockerfile                     # Multi-stage production container
│   ├── next.config.mjs                # Hybrid static export / server runtime config
│   ├── tailwind.config.ts             # Tailwind CSS design system
│   ├── tsconfig.json                  # Strict TypeScript configuration
│   └── package.json                   # Dependencies and build scripts
├── backend/                           # FastAPI Modular Monolith REST API
│   ├── app/
│   │   ├── api/v1/                    # Versioned REST routers & endpoints
│   │   ├── common/                    # Error handlers, pagination, envelopes
│   │   ├── core/                      # Config (Pydantic), security, database
│   │   └── modules/                   # Domain modules (auth, catalog, orders, etc.)
│   ├── migrations/                    # Alembic schema migrations
│   ├── tests/                         # Pytest test suite (181 tests)
│   ├── alembic.ini                    # Alembic configuration
│   ├── Dockerfile                     # Multi-stage Python 3.12 container
│   ├── pyproject.toml                 # Backend dependencies & tools
│   └── requirements.txt               # Pinned Python requirements
├── docs/
│   ├── backend/                       # Architecture, DB design, API contract, plans
│   └── AUDIT_REPORT.md                # Consolidated system & security audit
├── infra/
│   └── terraform/                     # Complete AWS Infrastructure as Code
│       ├── environments/              # Staging & Production tfvars
│       ├── ecs.tf                     # Fargate cluster, task definitions & ALB
│       ├── rds.tf                     # Amazon RDS MySQL 8.0 (KMS encrypted)
│       ├── s3_cloudfront.tf           # Private S3 media bucket & CloudFront OAC
│       └── vpc.tf                     # Multi-AZ 3-tier networking
├── logo/                              # Brand logos, icons, favicons & assets
├── docker-compose.yml                 # Local multi-container orchestration
├── .gitignore                         # Comprehensive monorepo ignore rules
└── .env.example                       # Root environment variable template
```
├── .env.example                       # Central environment configuration template
├── .gitignore                         # Git exclusion rules
├── docker-compose.yml                 # Local container orchestration
├── Dockerfile                         # Multi-stage Next.js production container
├── package.json                       # Frontend dependencies & scripts
└── tsconfig.json                      # TypeScript configuration
```

---

## Quick Start (Docker Compose)

The easiest way to run the complete stack locally (MySQL 8.0, Backend API, and Next.js Storefront) is using Docker Compose:

### 1. Clone & Configure Environment
```bash
git clone https://github.com/your-org/uninova.git
cd uninova

# Copy environment template
cp .env.example .env
```

### 2. Start Services
```bash
docker compose up --build -d
```

### 3. Apply Database Migrations
```bash
docker compose exec backend alembic upgrade head
```

### 4. Access Applications
- **Storefront:** [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger):** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## Manual Local Development

If you prefer running services directly on your host machine:

### Backend Setup (FastAPI)
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup (Next.js)
```bash
# In project root
npm ci

# Start Next.js development server
npm run dev
```

---

## Running Tests

### Backend Test Suite (Pytest)
```bash
cd backend
python -m pytest tests -v
```
*Current test suite status: **181 tests passing (100% pass rate)** covering auth, dynamic catalog, COD checkout, staff RBAC, and configuration security.*

### Frontend Typecheck & Build
```bash
# Check static TypeScript types
npx tsc --noEmit

# Verify production Next.js build
npm run build
```
*All 48 routes compile and prerender cleanly.*

---

## Environment Variables (`.env`)

UniNova uses explicit, strictly validated environment variables. A template is provided in [`.env.example`](./.env.example).

| Variable | Description | Default / Example |
|---|---|---|
| `APP_ENV` | Application environment (`development`, `test`, `staging`, `production`) | `development` |
| `SECRET_KEY` | 32+ character cryptographic signing key | Dev default (custom required in prod) |
| `DATABASE_URL` | Sync database connection string | `mysql+pymysql://...` |
| `DATABASE_URL_ASYNC` | Async database connection string | `mysql+aiomysql://...` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000,http://127.0.0.1:3000` |
| `NEXT_PUBLIC_API_URL` | Public API endpoint for frontend | `http://localhost:8000/api/v1` |
| `ONLINE_PAYMENT_PROVIDER` | Payment adapter (`none`, `mock`, `safepay`, `payfast`) | `none` (COD default) |

> [!CAUTION]
> Never commit `.env` or sensitive credentials to GitHub. Only `.env.example` should be tracked in version control.

---

## Deployment & Cloud Infrastructure

Complete Infrastructure as Code (Terraform) is located in [`infra/terraform/`](./infra/terraform/):
- **Staging (`environments/staging.tfvars`):** Cost-optimized with single NAT gateway, `db.t4g.micro` RDS, and 0.25 vCPU Fargate tasks (~$91/month).
- **Production (`environments/production.tfvars`):** Multi-AZ RDS MySQL, dual-AZ NAT gateways, and redundant Fargate tasks with circuit breaker rollback (~$244/month).

Refer to [`docs/backend/PRODUCTION_READINESS_REPORT.md`](./docs/backend/PRODUCTION_READINESS_REPORT.md) and [`docs/backend/LOCAL_DEPLOYMENT.md`](./docs/backend/LOCAL_DEPLOYMENT.md) for full operational guides.

---

## License

Private and proprietary. All rights reserved.
