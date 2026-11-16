# UWEARNOVA Legacy Backend Archive Manifest

**Archival Date:** 2026-11-16  
**Status:** RETIRED & SAFELY ARCHIVED  
**Reason for Archival:** Completed 10-Stage Serverless / BaaS Migration to Next.js 15 + Supabase + Cloudflare R2  

---

## 1. Overview of Retired Components

The legacy serverful backend consisted of a monolithic Python FastAPI application with MySQL database and AWS S3 object storage. As of Stage 9, **100% of storefront and administrative operations have been decoupled from this architecture**.

| Legacy Component | Replaced By | Operational Benefit |
| :--- | :--- | :--- |
| **FastAPI Web Framework** (208 endpoints across 20 modules) | Supabase PostgREST & Next.js 15 App Router | Zero server maintenance, automatic OpenAPI generation, sub-20ms edge latency |
| **MySQL 8.0 Database** (50 tables via SQLAlchemy ORM) | Supabase PostgreSQL 17 with Row Level Security (RLS) | Built-in row-level security, identity PKs, PostgreSQL JSONB, real-time listeners |
| **Alembic Database Migrations** (MySQL schema revisions) | Supabase SQL Migrations (`supabase/migrations/*.sql`) | Plain reproducible SQL, standard Postgres DDL, version-controlled in Git |
| **Custom Auth & JWT Tokens** (Argon2id password hashing) | Supabase GoTrue Auth (`@supabase/ssr`) | Zero-management auth service, social logins ready, OTP/Magic link recovery |
| **AWS S3 + CloudFront CDN** (Boto3 multipart upload) | Cloudflare R2 (S3-compatible presigned PUT URLs) | **Zero egress fees**, direct browser-to-bucket uploads, no server CPU/bandwidth bottleneck |
| **AWS ECS Fargate + ALB** ($120+/mo infrastructure) | Next.js Standalone SSR + Supabase + Cloudflare (<$2/mo) | **>98% hosting cost reduction**, auto-scaling from zero to millions of requests |

---

## 2. Decoupling Verification Summary

- **Frontend HTTP Requests:** Scanned `frontend/src` — **0 active calls** to `localhost:8000` or `backend:8000`.
- **Legacy Fallback Guards:** `frontend/src/lib/api/client.ts` throws `ApiClientError` (`BACKEND_MIGRATED`) if deprecated endpoints are invoked.
- **Data Completeness:** 100% of baseline categories (19), collections (5), products (3), variants (4), inventory (82 units), and stock valuation (**PKR 901,750.00**) reconciled in Supabase PostgreSQL.
- **Automated Tests:** All 33 routes and 12 acceptance test suites verified.

---

## 3. Historical Audit & Rollback Instructions

If historical data inspection or emergency rollback to the serverful backend is ever required:

### How to Run Legacy Backend Locally:
```bash
cd backend
# 1. Activate Python virtual environment
.venv\Scripts\activate

# 2. Set database connection in .env
# DB_URL=mysql+aiomysql://root:password@localhost:3306/uninova

# 3. Start Uvicorn ASGI server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Permanent Backup Locations:
- Original Baseline Repository: `E:\website`
- Pre-Migration Snapshot: `E:\UniNova_Backup_Serverful_PreSupabase_Migration`
- Migration Workspace: `E:\UWearNova`
