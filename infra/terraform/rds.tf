# ==============================================================================
# Amazon RDS for MySQL 8.0
# Private database subnets, automated backups, encrypted at rest via KMS
# ==============================================================================

# DB Subnet Group spanning private database subnets across 2 AZs
resource "aws_db_subnet_group" "rds" {
  name        = "${var.project_name}-${var.environment}-db-subnet-group"
  description = "Private database subnet group for UniNova MySQL"
  subnet_ids  = aws_subnet.private_db[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet-group"
  }
}

# Parameter Group configured for UTF-8 (multilingual & emoji support)
resource "aws_db_parameter_group" "mysql8" {
  name   = "${var.project_name}-${var.environment}-mysql8-params"
  family = "mysql8.0"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-mysql8-params"
  }
}

# High-entropy random password generated for master user
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# RDS MySQL Instance
resource "aws_db_instance" "mysql" {
  identifier        = "${var.project_name}-${var.environment}-mysql"
  engine            = "mysql"
  engine_version    = "8.0"
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.rds.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.mysql8.name

  # High availability & backup rules
  multi_az                = var.db_multi_az
  backup_retention_period = var.db_backup_retention_days
  backup_window           = "20:00-21:00" # UTC (off-peak Pakistan 01:00 AM PKT)
  maintenance_window      = "Sun:21:30-Sun:22:30"
  auto_minor_version_upgrade = true

  # Security restrictions
  publicly_accessible = false
  deletion_protection = var.environment == "production" ? true : false
  skip_final_snapshot = var.environment == "production" ? false : true
  final_snapshot_identifier = "${var.project_name}-${var.environment}-mysql-final-snapshot"

  tags = {
    Name = "${var.project_name}-${var.environment}-mysql"
  }
}
