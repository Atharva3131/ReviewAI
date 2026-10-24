resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "postgres" {
  identifier                  = "${var.project_name}-postgres"
  engine                      = "postgres"
  engine_version              = "15"
  instance_class              = var.db_instance_class
  allocated_storage           = var.db_allocated_storage
  max_allocated_storage       = 100
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = var.db_name
  username                    = var.db_username
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.main.name
  vpc_security_group_ids      = [aws_security_group.rds.id]
  publicly_accessible         = false
  backup_retention_period     = 1
  deletion_protection         = false
  skip_final_snapshot         = true
  final_snapshot_identifier   = "${var.project_name}-final"
  apply_immediately           = true
}

output "rds_master_secret_arn" {
  description = "AWS-managed RDS master secret ARN; contains the password, never the password itself"
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}
