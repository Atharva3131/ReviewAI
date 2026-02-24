# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  
  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# RDS Parameter Group for PostgreSQL with pgvector
resource "aws_db_parameter_group" "postgres_pgvector" {
  family = "postgres15"
  name   = "${var.project_name}-postgres-pgvector"
  
  parameter {
    name  = "shared_preload_libraries"
    value = "vector"
  }
  
  parameter {
    name  = "log_statement"
    value = "all"
  }
  
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
  
  tags = {
    Name = "${var.project_name}-postgres-pgvector"
  }
}

# RDS Instance
resource "aws_db_instance" "postgres" {
  identifier = "${var.project_name}-postgres"
  
  # Engine
  engine         = "postgres"
  engine_version = "15.4"
  
  # Instance
  instance_class    = "db.t3.medium"
  allocated_storage = 100
  max_allocated_storage = 1000
  storage_type      = "gp3"
  storage_encrypted = true
  
  # Database
  db_name  = "revive_ai"
  username = "postgres"
  password = random_password.db_password.result
  
  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  
  # Backup
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
  
  # Performance Insights
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  
  # Parameter Group
  parameter_group_name = aws_db_parameter_group.postgres_pgvector.name
  
  # Deletion Protection
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${var.project_name}-postgres-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  tags = {
    Name = "${var.project_name}-postgres"
  }
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store database password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}/database-password"
  
  tags = {
    Name = "${var.project_name}-db-password"
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

# Store database URL in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_url" {
  name = "${var.project_name}/database-url"
  
  tags = {
    Name = "${var.project_name}-db-url"
  }
}

resource "aws_secretsmanager_secret_version" "db_url" {
  secret_id = aws_secretsmanager_secret.db_url.id
  secret_string = "postgresql://${aws_db_instance.postgres.username}:${random_password.db_password.result}@${aws_db_instance.postgres.endpoint}/${aws_db_instance.postgres.db_name}"
}

# IAM Role for RDS Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-rds-monitoring-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-rds-monitoring-role"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Outputs
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.postgres.port
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.postgres.db_name
}