# ==============================================================================
# Terraform Outputs
# ==============================================================================

output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "ecr_backend_repository_url" {
  description = "ECR repository URL for backend container images"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  description = "ECR repository URL for frontend container images"
  value       = aws_ecr_repository.frontend.repository_url
}

output "rds_endpoint" {
  description = "Private RDS MySQL endpoint"
  value       = aws_db_instance.mysql.address
}

output "s3_media_bucket_name" {
  description = "S3 bucket name for product and media storage"
  value       = aws_s3_bucket.media.bucket
}

output "cloudfront_domain_name" {
  description = "CloudFront CDN domain name for media asset delivery"
  value       = aws_cloudfront_distribution.media.domain_name
}

output "github_deployer_role_arn" {
  description = "IAM Role ARN for GitHub Actions OIDC authentication"
  value       = aws_iam_role.github_oidc_deployer.arn
}

output "secrets_manager_db_arn" {
  description = "Secrets Manager ARN for database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}
