# ==============================================================================
# AWS Secrets Manager: Database Credentials & Application Secrets
# ==============================================================================

# Database Credentials Secret
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.project_name}/${var.environment}/database"
  description             = "MySQL master connection credentials for UniNova ${var.environment}"
  recovery_window_in_days = var.environment == "production" ? 30 : 0

  tags = {
    Name = "${var.project_name}-${var.environment}-db-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    host     = aws_db_instance.mysql.address
    port     = aws_db_instance.mysql.port
    database = var.db_name
    username = var.db_username
    password = random_password.db_password.result
    sync_url = "mysql+pymysql://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.mysql.address}:${aws_db_instance.mysql.port}/${var.db_name}"
    async_url = "mysql+aiomysql://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.mysql.address}:${aws_db_instance.mysql.port}/${var.db_name}"
  })
}

# High-entropy JWT signing key
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

# Application Runtime Secrets
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${var.project_name}/${var.environment}/app-secrets"
  description             = "Runtime secrets (JWT Secret, API keys) for UniNova backend"
  recovery_window_in_days = var.environment == "production" ? 30 : 0

  tags = {
    Name = "${var.project_name}-${var.environment}-app-secrets"
  }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    SECRET_KEY                = random_password.jwt_secret.result
    ONLINE_PAYMENT_PROVIDER   = "none"
    PAYMENT_WEBHOOK_SECRET    = "uninova-payment-webhook-secret-placeholder"
    AWS_S3_BUCKET_NAME        = aws_s3_bucket.media.bucket
    AWS_CLOUDFRONT_DOMAIN     = aws_cloudfront_distribution.media.domain_name
  })
}
