# ==============================================================================
# Staging Environment Variables (Cost-Optimized)
# ==============================================================================
environment               = "staging"
aws_region                = "ap-southeast-1"
domain_name               = "staging.uninova.pk"
backend_subdomain         = "api"
github_repo               = "org/uninova-fashion"

# Cost-Optimized Networking
enable_single_nat_gateway = true

# Cost-Optimized RDS MySQL
db_instance_class         = "db.t4g.micro"
db_allocated_storage      = 20
db_multi_az               = false
db_backup_retention_days  = 7

# Minimal ECS Fargate Compute
backend_cpu               = 256  # 0.25 vCPU
backend_memory            = 512  # 0.5 GB RAM
backend_desired_count     = 1

frontend_cpu              = 256  # 0.25 vCPU
frontend_memory           = 512  # 0.5 GB RAM
frontend_desired_count    = 1
