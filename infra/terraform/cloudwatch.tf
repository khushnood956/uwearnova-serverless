# ==============================================================================
# Amazon CloudWatch: Metrics, Dashboards, and Operational Alarms
# ==============================================================================

# 1. ECS Backend CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "backend_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-backend-cpu-high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Triggered when backend ECS CPU exceeds 80% for 5 minutes"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }
}

# 2. ECS Backend Memory Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "backend_memory_high" {
  alarm_name          = "${var.project_name}-${var.environment}-backend-memory-high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Triggered when backend ECS Memory exceeds 85% for 5 minutes"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }
}

# 3. ALB 5XX Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-alb-5xx-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Triggered when ALB records more than 10 5XX errors in 5 minutes"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}

# 4. RDS Free Storage Space Alarm (< 5 GB)
resource "aws_cloudwatch_metric_alarm" "rds_low_storage" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-low-storage"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 5368709120 # 5 GB in bytes
  alarm_description   = "Triggered when RDS MySQL free storage falls below 5 GB"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.mysql.identifier
  }
}
