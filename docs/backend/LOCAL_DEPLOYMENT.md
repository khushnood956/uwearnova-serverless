# UniNova Local Container Deployment & Developer Operations Guide (M33)

This guide documents the local containerized deployment architecture for the **UniNova E-Commerce Platform**, comprising the MySQL 8.0 database, the FastAPI backend REST API, and the Next.js App Router storefront.

---

## 1. Architecture & Services Overview

The local environment is orchestrated via Docker Compose (`docker-compose.yml`), managing three interdependent services connected on an internal Docker bridge network:

```
[ Next.js Storefront ] (Port 3000)
         │
         ▼ (HTTP: http://localhost:8000/api/v1)
[ FastAPI Backend API ] (Port 8000)
         │
         ▼ (TCP: mysql:3306)
[ MySQL 8.0 Database ] (Port 3306, Persistent Volume `mysql_data`)
```

- **`mysql`**: Official MySQL 8.0 container configured with healthchecks (`mysqladmin ping`) and a persistent named volume (`mysql_data`).
- **`backend`**: Lightweight Python 3.12-slim multi-stage build running Uvicorn with auto-healthcheck, depending on the database becoming healthy before initialization.
- **`frontend`**: Multi-stage Node 20-alpine container running Next.js 15 production server on port 3000, depending on the backend service.

---

## 2. Prerequisites

- **Docker Desktop** (Windows/macOS) or **Docker Engine 24+** and **Docker Compose v2+** (Linux).
- Free host ports:
  - `3000`: Next.js Storefront
  - `8000`: FastAPI Backend API
  - `3306`: MySQL Database

---

## 3. Starting the Local Container Stack

### 3.1 Build and Start All Services
Run the following command in the project root:

```powershell
docker compose up --build -d
```

### 3.2 Verify Container Status & Health
Inspect running containers and health probes:

```powershell
docker compose ps
```

Expected output:
```
NAME                IMAGE               COMMAND                  SERVICE             STATUS                    PORTS
uninova_mysql       mysql:8.0           "docker-entrypoint.s…"   mysql               Up (healthy)              0.0.0.0:3306->3306/tcp
uninova_backend     website-backend     "uvicorn app.main:ap…"   backend             Up (healthy)              0.0.0.0:8000->8000/tcp
uninova_frontend    website-frontend    "npm run start"          frontend            Up                        0.0.0.0:3000->3000/tcp
```

### 3.3 Tail Container Logs
```powershell
# Tail all services
docker compose logs -f

# Tail backend service only
docker compose logs -f backend

# Tail frontend service only
docker compose logs -f frontend
```

---

## 4. Database Migrations & Data Initialization

Once `uninova_mysql` and `uninova_backend` are healthy, apply database migrations:

### 4.1 Execute Alembic Migrations
```powershell
docker compose exec backend alembic upgrade head
```

### 4.2 Verify Applied Migrations
```powershell
docker compose exec backend alembic current
```

### 4.3 Interactive MySQL Terminal (Optional)
To inspect database tables and records directly:
```powershell
docker compose exec mysql mysql -u uninova_user -puninova_secure_password uninova_db
```

---

## 5. End-to-End Local Verification Checkpoints

Validate the local deployment against these 15 operational checkpoints:

| # | Checkpoint | Target URL / Command | Expected Result |
|---|---|---|---|
| **1** | Backend Health Probe | `curl http://localhost:8000/health` | `{"status":"healthy","database":"connected"}` |
| **2** | Backend OpenAPI Docs | `http://localhost:8000/api/v1/docs` | Interactive Swagger UI loaded |
| **3** | Storefront Homepage | `http://localhost:3000` | Clean luxury layout with departments rendered |
| **4** | Dynamic Categories | `GET /api/v1/departments/active-hierarchy` | Men, Women, Kids and child categories returned |
| **5** | Product Catalogue | `http://localhost:3000/collections/all` | Active products retrieved from backend |
| **6** | Product Details Page | `http://localhost:3000/product/monolith-oversized-wool-blazer` | Pricing, size selector, and stock state displayed |
| **7** | Cart Persistence | Add item to cart at `/product/...` | Header cart count updates; `/cart` displays variant |
| **8** | Customer Auth | `POST /api/v1/auth/customer/login` | JWT access token & refresh token returned |
| **9** | Customer Account | `http://localhost:3000/account` | Orders, Profile, Addresses, Wishlist tabs accessible |
| **10** | Staff Workqueues | `http://localhost:3000/staff` | Role-tailored fulfillment & support queues |
| **11** | Admin Portal | `http://localhost:3000/admin` | Catalogue, Orders, Customers, Analytics tabs |
| **12** | Shipping Quotes | `POST /api/v1/shipping/quote` | Courier quote & free shipping threshold evaluated |
| **13** | Cash on Delivery (COD) | Submit checkout with `payment_method="cod"` | Order `placed`, `payment_status="pending"` |
| **14** | COD Reconciliation | `POST /api/v1/orders/{order_number}/payments/cod-confirm` | Finance operator updates payment status to `paid` |
| **15** | Order Tracking | `http://localhost:3000/checkout/success?order=UNV-...` | Authoritative order summary with status timeline |

---

## 6. Database Reset Procedure

To completely wipe local database data and reinitialize from scratch:

```powershell
# 1. Stop and remove containers and persistent volumes
docker compose down -v

# 2. Re-create and start services
docker compose up -d

# 3. Wait for MySQL to become healthy, then apply migrations
docker compose exec backend alembic upgrade head
```

---

## 7. Troubleshooting Guide

### 7.1 Port Already in Use (3306, 8000, 3000)
- **Symptom:** `bind: address already in use` error when running `docker compose up`.
- **Fix:** Identify and stop the local process holding the port:
  - Windows: `Get-NetTCPConnection -LocalPort 3306` followed by `Stop-Process -Id <PID>`.
  - Or remap host port in `docker-compose.yml` (e.g. `"3307:3306"`).

### 7.2 Backend Fails to Connect to MySQL on Startup
- **Symptom:** `pymysql.err.OperationalError: Can't connect to MySQL server on 'mysql'`.
- **Fix:** The `depends_on` configuration in `docker-compose.yml` requires `condition: service_healthy`. Ensure MySQL container healthcheck has passed (`docker compose ps`).

### 7.3 Production Secret Validation Error
- **Symptom:** Backend container crashes with `ValueError: In production (APP_ENV=production), SECRET_KEY must be a cryptographically secure random string...`
- **Fix:** When running with `APP_ENV=production`, provide a custom 32+ character `SECRET_KEY` and non-default `MYSQL_PASSWORD` in your `.env` file.

### 7.4 Next.js Build Static Page Fetch Warnings
- **Symptom:** Next.js build shows warnings: `Could not load backend products for ... [ApiClientError]: fetch failed`.
- **Explanation:** During `next build`, Next.js attempts static page pre-generation. The static fallback handles missing backend data during build time without failing the build. Once containers are running, client fetches query the live backend dynamically.
