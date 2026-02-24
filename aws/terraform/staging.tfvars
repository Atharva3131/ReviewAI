# Staging environment configuration for Revive AI
# This file contains staging-specific configuration values

# Basic Configuration
aws_region    = "us-east-1"
environment   = "staging"
project_name  = "revive-ai"
domain_name   = "staging.revive-ai.com"

# Monitoring and alerting
alert_email = "staging-alerts@revive-ai.com"

# Database Configuration (smaller instances for staging)
postgres_instance_class = "db.t3.small"
postgres_allocated_storage = 20
postgres_max_allocated_storage = 100
postgres_backup_retention_period = 3
postgres_backup_window = "03:00-04:00"
postgres_maintenance_window = "sun:04:00-sun:05:00"
postgres_deletion_protection = false
postgres_skip_final_snapshot = true

# Redis Configuration (smaller for staging)
redis_node_type = "cache.t3.small"
redis_num_cache_clusters = 1
redis_parameter_group_name = "default.redis7"
redis_port = 6379
redis_at_rest_encryption_enabled = true
redis_transit_encryption_enabled = false

# ECS Configuration (smaller for staging)
ecs_cpu = "512"
ecs_memory = "1024"
ecs_desired_count = 1
ecs_min_capacity = 1
ecs_max_capacity = 3
ecs_enable_execute_command = true

# Auto Scaling Configuration
scale_up_threshold = 80
scale_down_threshold = 20
scale_up_cooldown = 180
scale_down_cooldown = 300

# Load Balancer Configuration
alb_enable_deletion_protection = false
alb_idle_timeout = 60
alb_enable_http2 = true

# CloudFront Configuration
cloudfront_price_class = "PriceClass_100"
cloudfront_minimum_protocol_version = "TLSv1.2_2021"
cloudfront_default_ttl = 300
cloudfront_max_ttl = 3600

# Monitoring and Logging
enable_container_insights = true
log_retention_days = 7
enable_detailed_monitoring = false
enable_performance_insights = false

# Security Configuration
enable_deletion_protection = false
enable_backup_encryption = true
enable_storage_encryption = true
enable_waf = false
enable_shield_advanced = false

# Networking
enable_nat_gateway = true
enable_vpn_gateway = false
enable_flow_logs = false

# Cost Optimization
enable_spot_instances = false
enable_reserved_instances = false

# Backup and Disaster Recovery
backup_retention_period = 3
enable_cross_region_backup = false
enable_point_in_time_recovery = false

# Compliance and Governance
enable_config = false
enable_cloudtrail = false
enable_guardduty = false
enable_security_hub = false

# Tags
additional_tags = {
  Owner       = "DevOps Team"
  CostCenter  = "Engineering"
  Environment = "Staging"
  Purpose     = "Testing"
  AutoShutdown = "Enabled"
}
