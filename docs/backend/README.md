# UniNova Backend & Full-Stack Blueprint

This documentation suite establishes the architecture, database schema, API conventions, dashboard roles, security principles, AWS deployment roadmap, and phased implementation sequence for the UniNova e-commerce platform.

---

## 1. Documentation Index

| Document | Path | Core Responsibility |
|---|---|---|
| **Architecture** | [`01-backend-architecture.md`](./01-backend-architecture.md) | FastAPI modular monolith architecture, layers, boundaries, and coding standards |
| **Database Design** | [`02-database-design.md`](./02-database-design.md) | MySQL 8.0 entities, relationships, constraints, indexes, Decimal currency rules |
| **Dashboards & RBAC** | [`03-dashboards-and-rbac.md`](./03-dashboards-and-rbac.md) | Customer portal, Staff operations, and Store admin dashboard routes & permissions |
| **API Contract** | [`04-api-contract.md`](./04-api-contract.md) | `/api/v1` REST conventions, success/error envelopes, pagination, OpenAPI |
| **AWS Deployment** | [`05-aws-deployment.md`](./05-aws-deployment.md) | AWS target infrastructure (ECS Fargate, RDS MySQL, S3, CloudFront, Route 53) |
| **Implementation Plan** | [`06-implementation-plan.md`](./06-implementation-plan.md) | 37-module sequential delivery tracker (M00 to M36) |
| **Repository Audit** | [`REPOSITORY_AUDIT.md`](./REPOSITORY_AUDIT.md) | M00 verified audit of existing Next.js frontend, runtimes, and local toolchains |
| **Implementation Log** | [`IMPLEMENTATION_LOG.md`](./IMPLEMENTATION_LOG.md) | Execution log recording actual commands, verification evidence, and decisions |
| **Master Prompt** | [`../../AGENT_BACKEND_INSTRUCTIONS.md`](../../AGENT_BACKEND_INSTRUCTIONS.md) | Execution guidelines and constraints for AI engineering agents |
| **Environment Template**| [`../../.env.example`](../../.env.example) | Central environment configuration template |

---

## 2. Project Boundaries & Documentation Separation

1. **Frontend Concept & Plan**:
   - The original frontend concept brief (`fashion_ecommerce_concept_brief_performance_focused.md`) and original modular frontend plan (`IMPLEMENTATION_PLAN.md`) remain untouched at the repository root.
   - Do NOT merge frontend and backend plans.
2. **Backend Documentation**:
   - All backend design documents live under `docs/backend/`.
   - Implementation tracking is recorded strictly in `06-implementation-plan.md` and `IMPLEMENTATION_LOG.md`.
3. **Backend Source Location**:
   - All future backend code will live inside the `backend/` directory (to be created in M02).
   - The frontend remains at `src/` and `package.json`.

---

## 3. Technology Stack & Key Decisions Summary

- **Backend Framework:** Python + FastAPI (Modular Monolith)
- **Database Engine:** MySQL 8.0-compatible (InnoDB, foreign keys, explicit indexes)
- **ORM & Migrations:** SQLAlchemy 2.x (async engine) + Alembic migrations
- **Data Validation:** Pydantic v2
- **Currency & Precision:** Strict use of `Decimal` for all pricing in PKR
- **Authentication & RBAC:** Session/JWT-based with server-enforced role permissions for Customer, Staff, and Store Admin
- **Object Storage:** S3-compatible abstraction; AWS S3 in production
- **AWS Compute:** Amazon ECS on AWS Fargate (backend API container + frontend container)
- **AWS Database:** Amazon RDS for MySQL in private VPC subnets with automated backups

---

## 4. Delivery Rules

- **Strictly One Module per Execution:** Implement only one module per turn.
- **No Subagents:** Single-agent direct execution.
- **Verification First:** Never mark a module completed without running real tests, type checks, and verifying acceptance criteria.
