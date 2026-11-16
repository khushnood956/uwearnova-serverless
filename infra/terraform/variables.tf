variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-southeast-1" # Singapore (closest latency to Pakistan context)
}

variable "environment" {
  description = "Target deployment environment (staging or production)"
  type        = string
  default     = "staging"
}

variable "project_name" {
  description = "Project identifier used for resource naming"
  type        = string
  default     = "uninova"
}

variable "domain_name" {
  description = "Root domain name for UniNova store (e.g. uninova.pk)"
  type        = string
  default     = "uninova.pk"
}

variable "backend_subdomain" {
  description = "Subdomain for backend API (e.g. api.uninova.pk or api.staging.uninova.pk)"
  type        = string
  default     = "api"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to span for high availability"
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (ALB & NAT Gateways)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_app_subnet_cidrs" {
  description = "CIDR blocks for private application subnets (ECS tasks)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "private_db_subnet_cidrs" {
  description = "CIDR blocks for private database subnets (RDS MySQL)"
  type        = list(string)
  default     = ["10.0.20.0/24", "10.0.21.0/24"]
}

variable "enable_single_nat_gateway" {
  description = "Use a single NAT Gateway across all private subnets to minimize costs (Recommended for Staging)"
  type        = bool
  default     = true
}

# RDS Settings
variable "db_instance_class" {
  description = "Instance class for RDS MySQL"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB for RDS MySQL"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum storage in GB for autoscaling RDS MySQL"
  type        = number
  default     = 100
}

variable "db_multi_az" {
  description = "Enable Multi-AZ replication for RDS (Recommended for Production)"
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  description = "Days of automated RDS backups to retain"
  type        = number
  default     = 7
}

variable "db_name" {
  description = "MySQL database name"
  type        = string
  default     = "uninova_db"
}

variable "db_username" {
  description = "MySQL root master username"
  type        = string
  default     = "uninova_admin"
}

# ECS Fargate Settings
variable "backend_cpu" {
  description = "Fargate CPU units for backend task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "backend_memory" {
  description = "Fargate Memory in MB for backend task"
  type        = number
  default     = 512
}

variable "backend_desired_count" {
  description = "Desired number of running backend tasks"
  type        = number
  default     = 1
}

variable "frontend_cpu" {
  description = "Fargate CPU units for frontend task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Fargate Memory in MB for frontend task"
  type        = number
  default     = 512
}

variable "frontend_desired_count" {
  description = "Desired number of running frontend tasks"
  type        = number
  default     = 1
}

# GitHub OIDC
variable "github_repo" {
  description = "GitHub repository identifier for OIDC trust (e.g. org/uninova-fashion)"
  type        = string
  default     = "org/uninova-fashion"
}
