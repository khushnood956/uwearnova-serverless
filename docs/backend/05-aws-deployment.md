# 05 — AWS Deployment and Operations

## 1. Goal

Deploy UniNova as a secure, maintainable AWS-hosted store. The application should be portable: Dockerized services, environment-based configuration, standard MySQL, S3-compatible object storage abstraction and infrastructure-as-code. Avoid relying on local machine state.

## 2. Recommended AWS target

A practical initial AWS architecture:

```text
Customers
   |
Route 53 + ACM (domain and TLS)
   |
CloudFront (+ WAF when justified)
   |-------------------------------|
   |                               |
Next.js hosting                 API origin
(Amplify Hosting or             Application Load Balancer
container hosting)                  |
                                    v
                              ECS Fargate
                              FastAPI container
                                    |
                  |-----------------|----------------|
                  v                 v                v
              RDS MySQL          S3 bucket       Optional SQS
              private subnet    product media   async jobs
                  |
             automated backups

Supporting:
ECR | Secrets Manager | CloudWatch | IAM | VPC | Security Groups
Optional ElastiCache Redis only when justified by measured need.
```

### Recommended starting choices

- **Backend compute:** Amazon ECS on AWS Fargate, running the FastAPI Docker image.
- **Container registry:** Amazon ECR.
- **Database:** Amazon RDS for MySQL, private networking, automated backups.
- **Product images/uploads:** Amazon S3 with private bucket and controlled access; serve through CloudFront.
- **Frontend hosting:** evaluate AWS Amplify Hosting for the existing Next.js app. If its runtime/build constraints do not fit the actual app, deploy the Next.js standalone container on ECS. Make this decision after inspecting Next.js version, server features and build output.
- **TLS/domain:** Route 53 and AWS Certificate Manager.
- **Secrets:** AWS Secrets Manager or SSM Parameter Store SecureString.
- **Logs/metrics/alarms:** CloudWatch.
- **Async jobs:** SQS only when durable background work is required.
- **Cache:** ElastiCache only after profiling shows a cache/rate-limit need.

Do not add API Gateway in front of ALB by default. Do not add EKS/Kubernetes. Keep the first deployment simple.

AWS's own containerized web application guidance describes CloudFront, S3, ALB, ECS/Fargate, Route 53 and managed security/monitoring as a scalable web application pattern. Select the services that fit this store rather than copying a reference architecture wholesale:
- https://docs.aws.amazon.com/solutions/building-a-containerized-and-scalable-web-application-on-aws/
- https://docs.aws.amazon.com/solutions/web-store-on-aws/

## 3. Environment strategy

Maintain separate configurations for:
- Local development
- Automated testing / CI
- Staging
- Production

Never point tests or local development at production data. Production credentials must not be committed or copied into `.env.example`.

## 4. Networking and security

- Put RDS in private subnets; disable public accessibility.
- Permit database ingress only from the backend task security group.
- Put application services behind the intended HTTPS entry point.
- Use least-privilege IAM task roles.
- Keep S3 buckets private; use controlled CloudFront access and presigned upload/download flows where required.
- Encrypt database storage, S3 objects and backups.
- Store credentials in Secrets Manager/SSM, not container images or source.
- Use TLS for all public traffic and secure internal connections where applicable.
- Add AWS WAF rules based on risk and budget; do not assume WAF replaces application security.
- Configure CORS for exact production/staging frontend origins.
- Use rate limits and abuse controls for authentication, checkout and public forms.

## 5. Deployment pipeline

Proposed pipeline:
1. Push to Git repository.
2. CI runs lint, type checks, unit/integration tests and frontend/backend builds.
3. Build Docker image.
4. Scan dependencies/image.
5. Push immutable image tag to ECR.
6. Apply reviewed database migrations as a controlled deployment step.
7. Deploy ECS service.
8. Wait for health checks.
9. Run smoke tests.
10. Roll back application deployment if health checks fail.

Use GitHub Actions with AWS OIDC federation rather than long-lived AWS access keys where practical. Store infrastructure definitions in version control using AWS CDK, Terraform or CloudFormation. Choose one IaC tool; do not mix tools without reason.

## 6. Database operations

- Automated RDS backups and a documented retention policy.
- Test restore procedures before production launch.
- Use a separate migration job/task with controlled permissions.
- Do not run destructive migrations automatically without review and backup.
- Monitor CPU, connections, storage, slow queries and backup status.
- Plan connection pooling and SQLAlchemy pool limits against RDS connection limits.
- Consider Multi-AZ for production availability based on budget and recovery requirements.

## 7. Cost discipline

The initial architecture should avoid unnecessary always-on services:
- Start with modest ECS task sizing and scale from measured CPU/memory/latency.
- Select an RDS instance/storage configuration appropriate to actual expected traffic and budget.
- Do not provision Redis, OpenSearch, EKS or multiple worker services without a proven requirement.
- Set AWS Budgets and billing alerts before public launch.
- Use S3 lifecycle rules for obsolete media/exports.
- Review CloudWatch log retention and data-transfer costs.
- Understand that Multi-AZ, NAT gateways, load balancers, CloudFront, WAF and managed services have costs; estimate them for the selected AWS region before provisioning.

No AWS monthly cost should be stated as fact until region, instance sizes, traffic, storage, availability and data transfer assumptions are known.

## 8. Production readiness checklist

- [ ] Custom domain and HTTPS.
- [ ] Production secrets stored outside source control.
- [ ] Private RDS networking.
- [ ] Automated backup and restore test.
- [ ] Health and readiness checks.
- [ ] CloudWatch logs, metrics and alarms.
- [ ] Error monitoring and alert routing.
- [ ] CI/CD with rollback path.
- [ ] Migration procedure.
- [ ] Admin MFA/strong authentication policy.
- [ ] Least-privilege staff roles.
- [ ] Rate limits and webhook verification.
- [ ] S3 access policy and upload validation.
- [ ] Privacy, shipping, returns and terms pages reviewed.
- [ ] Payment provider merchant onboarding and live webhook tests, if online payments are enabled.
- [ ] COD order confirmation and reconciliation tested.
- [ ] Load, security and end-to-end tests.
- [ ] AWS Budget alerts configured.
