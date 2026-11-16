# UniNova AWS Infrastructure, CI/CD, and Production Readiness Report (M34, M35, M36)

**Evaluation Date:** November 2026  
**Target Platform:** Amazon Web Services (AWS) — Region `ap-southeast-1` (Singapore)  
**IaC Tool:** Terraform (`>= 1.5.0`)  
**CI/CD Engine:** GitHub Actions with AWS IAM OIDC Federation  
**Assessment Outcome:** **READY FOR STAGING PROVISIONING / PENDING CLIENT GO-LIVE APPROVAL**

---

## 1. Executive Summary

This report establishes the complete AWS production architecture, infrastructure-as-code definitions, automated deployment pipelines, staging verification procedures, and final operational readiness checklist for the **UniNova Fashion E-Commerce Platform**.

All infrastructure specifications have been codified declaratively using Terraform in `infra/terraform/`. Continuous integration, container image publishing, migration execution, and rolling ECS deployments with automated rollback are codified in `.github/workflows/`.

In accordance with strict project constraints:
- **No live AWS resources have been provisioned without explicit approval.**
- Zero hardcoded production secrets exist in version control.
- Clear separation is enforced between cost-conscious Staging and high-availability Production configurations.

---

## 2. AWS Target Architecture & Infrastructure as Code (M34)

### 2.1 Architecture Diagram

```text
                                  [ Internet Traffic ]
                                           │
                                           ▼
                               [ Route 53 + ACM TLS ]
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     │                                           │
        [ Storefront & API Routing ]               [ Static Media Delivery ]
                     │                                           │
                     ▼                                           ▼
         [ Application Load Balancer ]              [ CloudFront CDN (OAC) ]
                     │                                           │
         ┌───────────┴───────────┐                               │
         │                       │                               │
         ▼ (Port 3000)           ▼ (Port 8000)                   ▼
   [ ECS Fargate:          [ ECS Fargate:                 [ Private S3 Bucket:
     Next.js Frontend ]      FastAPI Backend ]              uninova-media ]
                                 │
                                 ▼ (Port 3306 - Private Ingress Only)
                           [ Amazon RDS:
                             MySQL 8.0 (gp3, KMS Encrypted) ]
```

### 2.2 Network Topology & Security Tiering
- **VPC (`10.0.0.0/16`):** Dual-AZ design (`ap-southeast-1a`, `ap-southeast-1b`).
- **Public Subnets (`10.0.1.0/24`, `10.0.2.0/24`):** Hosts the Application Load Balancer and NAT Gateway.
- **Private Application Subnets (`10.0.10.0/24`, `10.0.11.0/24`):** Hosts ECS Fargate tasks (Next.js and FastAPI). Outbound internet access via NAT Gateway for container image pulling and external courier/payment webhooks. No public IPs assigned.
- **Private Database Subnets (`10.0.20.0/24`, `10.0.21.0/24`):** Strictly isolated subnets containing Amazon RDS MySQL 8.0. Zero route to the internet; ingress permitted exclusively on port 3306 from the Backend ECS security group.

### 2.3 Codified Terraform Modules (`infra/terraform/`)
| File | Managed AWS Resources |
|---|---|
| `main.tf` | Terraform provider configuration, AWS region, default tagging strategy (`Project=UniNova`, `Environment=...`). |
| `variables.tf` | Configurable parameters for compute, database tiers, networking CIDRs, and domains. |
| `vpc.tf` | VPC, Internet Gateway, public/private route tables, NAT Gateways, subnet associations. |
| `security_groups.tf` | Ingress/egress rules for ALB, Frontend ECS, Backend ECS, and RDS MySQL. |
| `rds.tf` | RDS MySQL 8.0, DB Subnet Group, UTF8MB4 parameter group, automated backups (7-30 days), KMS encryption. |
| `ecr.tf` | Container registries for backend and frontend with vulnerability scanning and 7-day image lifecycle expiration. |
| `s3_cloudfront.tf` | S3 media bucket, public access block, CloudFront Origin Access Control (OAC), CDN caching behavior. |
| `secrets.tf` | AWS Secrets Manager secrets for database credentials and application JWT/runtime tokens. |
| `iam.tf` | ECS Execution Role, Backend Task Role (S3 least-privilege), and GitHub Actions OIDC deployer role. |
| `ecs.tf` | ECS Cluster, task definitions (FastAPI + Next.js), ALB target groups, healthcheck probes, and circuit breaker rollback. |
| `cloudwatch.tf` | Metric alarms for ECS CPU/Memory (>80%), ALB 5XX errors, and RDS low storage (<5 GB). |
| `outputs.tf` | ALB DNS name, ECR URLs, RDS endpoint, S3 bucket name, CloudFront domain, OIDC role ARN. |

---

## 3. Realistic Monthly Cost Estimate

The infrastructure has been designed with cost-consciousness as a first-class requirement. 

### 3.1 Cost Breakdown: Staging vs. Production

| Service / Resource | Staging Configuration (Cost-Optimized) | Staging Monthly Cost | Production Configuration (High-Availability) | Production Monthly Cost |
|---|---|---|---|---|
| **ECS Fargate Compute** | 1x Backend (0.25 vCPU, 0.5 GB) + 1x Frontend (0.25 vCPU, 0.5 GB) | **$15.00** | 2x Backend (0.5 vCPU, 1 GB) + 2x Frontend (0.5 vCPU, 1 GB) across 2 AZs | **$60.00** |
| **Amazon RDS MySQL 8.0** | `db.t4g.micro` (Single-AZ, 20 GB gp3 storage) | **$16.50** | `db.t4g.small` (Multi-AZ, 50 GB gp3 storage, 30-day backups) | **$72.00** |
| **Application Load Balancer** | 1x ALB + 1 LCU | **$22.50** | 1x ALB + 2 LCUs | **$26.00** |
| **NAT Gateway** | 1x Single NAT Gateway (`enable_single_nat_gateway = true`) | **$32.50** | 2x Multi-AZ NAT Gateways (High-Availability) | **$65.00** |
| **Amazon S3 (Media Storage)** | 10 GB standard storage + PUT/GET requests | **$0.50** | 50 GB standard storage + frequent PUT/GET requests | **$1.80** |
| **CloudFront CDN** | Under AWS Free Tier (1 TB data transfer free) | **$0.00** | ~100 GB egress beyond free tier | **$8.50** |
| **CloudWatch Logs & Metrics** | 7-day retention, 3 log streams | **$3.00** | 30-day retention, Container Insights, 4 Alarms | **$8.00** |
| **AWS Secrets Manager** | 2 secrets ($0.40/secret/month) | **$0.80** | 2 secrets + KMS customer managed key | **$1.80** |
| **Route 53 & ACM** | 1 Hosted Zone (ACM TLS certs are free) | **$0.50** | 1 Hosted Zone | **$0.50** |
| **TOTAL ESTIMATED MONTHLY** | — | **~$91.30 / mo** | — | **~$243.60 / mo** |

> [!NOTE]
> The figures above are engineering estimates based on official AWS APAC (Singapore) on-demand pricing. Actual AWS billing may vary depending on data transfer volume, courier webhook frequencies, and promotional tier status.

### 3.2 Key Cost-Saving Strategies Implemented
1. **Single NAT Gateway in Staging:** Using `enable_single_nat_gateway = true` in `staging.tfvars` eliminates a redundant NAT gateway, saving **$32.50/month**.
2. **ECR Lifecycle Rules:** Untagged container images are purged after 7 days; tagged images are capped at 30, preventing runaway ECR storage costs.
3. **CloudFront Price Class 100:** Restricts edge distribution to North America, Europe, and Asia, cutting CDN delivery costs by ~40% compared to global edge classes.
4. **ECS Circuit Breaker:** Deployment failures automatically roll back within minutes without leaving orphan task replicas consuming compute.

---

## 4. Continuous Integration & Deployment Pipeline (M35)

Continuous deployment is implemented using **GitHub Actions** with **AWS IAM OIDC Federation** (zero long-lived AWS keys stored in GitHub repository secrets).

```
[ Developer Git Push ]
         │
         ├──► [ PR / main / develop ] ──► CI Workflow (.github/workflows/ci.yml)
         │                                  ├── Backend Pytest Suite (162 tests)
         │                                  ├── Frontend Static Typecheck (tsc)
         │                                  └── Next.js Production Build (48 pages)
         │
         ├──► [ Push to 'develop' ] ──► Deploy Staging (.github/workflows/deploy-staging.yml)
         │                                  ├── AWS OIDC Authentication
         │                                  ├── Build & Push Docker Images to ECR
         │                                  ├── Run Alembic Migrations (`run-task`)
         │                                  ├── ECS Rolling Deployment
         │                                  └── Automated Healthcheck Smoke Probe
         │
         └──► [ Release / Tag ] ─────► Deploy Production (.github/workflows/deploy-production.yml)
                                            ├── Protected Environment Approval Gate
                                            ├── Explicit Confirmation String Check
                                            ├── Build Release Tag Images
                                            ├── Run Production Migrations
                                            ├── ECS Rolling Deploy with Circuit Breaker
                                            └── Live Production Smoke Probe
```

---

## 5. Staging Verification Matrix

Prior to production traffic cutover, the staging deployment must pass all 15 operational checkpoints using synthetic test data:

| # | Operational Checkpoint | Target Endpoint / Action | Staging Verification Criteria |
|---|---|---|---|
| **1** | DNS & TLS Termination | `https://api.staging.uninova.pk/health` | Valid SSL/TLS certificate; returns HTTP 200 with DB status `connected`. |
| **2** | Storefront Frontend | `https://staging.uninova.pk` | Next.js server rendered; responsive layout loaded cleanly. |
| **3** | Dynamic Categories | `/api/v1/departments/active-hierarchy` | Men, Women, Kids and child categories returned dynamically. |
| **4** | Catalogue Browsing | `/collections/all` | Live products loaded from staging RDS MySQL. |
| **5** | Product Details | `/product/{slug}` | Real pricing in PKR, variant SKU selection, stock status visible. |
| **6** | Customer Registration/Auth | `POST /api/v1/auth/customer/register` | Customer created; JWT tokens issued and refresh token hashed in DB. |
| **7** | Customer Dashboard | `https://staging.uninova.pk/account` | Orders, profile, address book, and security settings accessible. |
| **8** | Cart & Wishlist Sync | Add items to cart / wishlist | Backend persistent cart syncs across sessions. |
| **9** | Delivery Quote Resolution | `POST /api/v1/shipping/quote` | Calculates PKR 350 fee or evaluates PKR 5,000 free shipping threshold. |
| **10** | Cash on Delivery Checkout | `POST /api/v1/orders/checkout` | Order placed with status `placed`, payment `pending`, inventory decremented. |
| **11** | Staff Workqueues | `https://staging.uninova.pk/staff` | Role-tailored queues for fulfillment and customer support tickets. |
| **12** | Admin Catalogue CRUD | `/admin/products/new` | Product creation with inline subcategory creation verified. |
| **13** | COD Payment Reconciliation | `POST .../payments/cod-confirm` | Finance operator marks payment status as `paid` upon delivery. |
| **14** | Media Upload & CDN Delivery | S3 Presigned URL + CloudFront | Uploaded product images served via `https://{cloudfront_domain}/...`. |
| **15** | Circuit Breaker Rollback | Fault injection test | Unhealthy task fails healthcheck; ECS automatically restores prior task. |

---

## 6. Production Readiness & Go/No-Go Checklist (M36)

### 6.1 Application Layer
- [x] **Typed API Integration:** Frontend communicates with FastAPI backend via strongly-typed endpoints.
- [x] **Dynamic Categories:** Department & category hierarchy fully database-driven with coming soon toggles.
- [x] **Authentication & RBAC:** Customer ownership isolated; 7 staff roles enforced via backend least-privilege checks.
- [x] **Authoritative Pricing:** All line items, discounts, and shipping charges computed exclusively server-side.
- [x] **COD Workflow:** Cash on delivery operates with pending payment status and staff reconciliation.
- [x] **Idempotency Safeguards:** Checkout enforces `Idempotency-Key` headers to prevent double-charging.

### 6.2 Infrastructure Layer
- [x] **Infrastructure as Code:** 100% of AWS resources codified in modular Terraform files.
- [x] **Database Isolation:** RDS MySQL placed in private subnets with zero public internet route.
- [x] **Encryption at Rest & Transit:** HTTPS/TLS via ALB and CloudFront; KMS encryption on RDS and S3.
- [x] **Automated Backups:** Daily RDS snapshots with 30-day retention and point-in-time recovery enabled.
- [x] **Monitoring & Alarms:** CloudWatch metric alarms for ECS CPU/Memory, ALB 5XX, and RDS storage deficits.

### 6.3 Business Operations & Policies
- [x] **Pricing & Currency:** Authoritative PKR currency format across all catalogue and checkout flows.
- [x] **Shipping & Delivery:** PKR 5,000 free-shipping threshold and standard courier delivery configured.
- [x] **Policy Pages:** Dynamic CMS pages for Privacy Policy, Terms of Service, and Returns Policy.
- [x] **Staff Accounts:** Default system roles seeded; least-privilege workqueues separated from admin settings.

---

## 7. Final Go/No-Go Launch Recommendation

| Component | Status | Recommendation |
|---|---|---|
| **Local Application Quality** | **VERIFIED** | 162 backend tests passing (100%), 48 Next.js pages compiled cleanly. |
| **Docker & Containers** | **VERIFIED** | Multi-stage Dockerfiles for backend and frontend validated locally. |
| **Terraform IaC Definitions** | **READY** | Validated modular architecture for staging and production. |
| **CI/CD Automation** | **READY** | GitHub Actions workflows with AWS OIDC authentication ready for deployment. |
| **Live AWS Provisioning** | **PAUSED (AWAITING APPROVAL)** | Requires client AWS credentials, domain DNS delegation, and explicit sign-off. |

### Final Recommendation:
**GO FOR STAGING INFRASTRUCTURE PROVISIONING upon configuration of AWS account credentials and Route 53 domain delegation.**  
**NO-GO FOR PRODUCTION TRAFFIC CUTOVER until Staging Verification Matrix is 100% executed and signed off.**
