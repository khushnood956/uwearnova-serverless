# ==============================================================================
# Security Groups: Least-Privilege Network Access
# ==============================================================================

# 1. Application Load Balancer Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Controls public inbound traffic to Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP public ingress (redirected to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS secure public ingress"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic to ECS targets"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-sg"
  }
}

# 2. ECS Frontend Service Security Group
resource "aws_security_group" "ecs_frontend" {
  name        = "${var.project_name}-${var.environment}-ecs-frontend-sg"
  description = "Allows ingress from ALB to Next.js container on port 3000"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Inbound from ALB only"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow outbound traffic for image pulls and API calls"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-frontend-sg"
  }
}

# 3. ECS Backend Service Security Group
resource "aws_security_group" "ecs_backend" {
  name        = "${var.project_name}-${var.environment}-ecs-backend-sg"
  description = "Allows ingress from ALB to FastAPI container on port 8000"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Inbound from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Inbound from Frontend tasks (if internal server-side calls)"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_frontend.id]
  }

  egress {
    description = "Allow outbound to RDS, S3, Secrets Manager, and Internet via NAT"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-backend-sg"
  }
}

# 4. RDS MySQL Database Security Group (Strictly Isolated)
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Permits MySQL ingress strictly from the backend ECS task security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MySQL port 3306 strictly from Backend ECS tasks"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_backend.id]
  }

  egress {
    description = "No outbound required for RDS"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}
