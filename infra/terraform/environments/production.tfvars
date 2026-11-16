# ==============================================================================
# Production Environment Variables (High-Availability & Fault-Tolerant)
# ==============================================================================
environment               = "production"
aws_region                = "ap-southeast-1"
domain_name               = "uninova.pk"
backend_subdomain         = "api"
github_repo               = "org/uninova-fashion"

# High-Availability Multi-AZ Networking
enable_single_nat_gateway = false

# Resilient Multi-AZ RDS MySQL
db_instance_class         = "db.t4g.small"
db_allocated_storage      = 50
db_max_allocated_storage  = 200
db_multi_az               = true
db_backup_retention_days  = 30

# Redundant ECS Fargate Compute Across 2 AZs
backend_cpu               = 512  # 0.5 vCPU
backend_memory            = 1024 # 1.0 GB RAM
backend_desired_count     = 2

frontend_cpu              = 512  # 0.5 vCPU
frontend_memory           = 1024 # 1.0 GB RAM
frontend_desired_count    = 2
