# Application Secrets
resource "aws_secretsmanager_secret" "app_secrets" {
  name = "${var.project_name}/app-secrets"
  
  tags = {
    Name = "${var.project_name}-app-secrets"
  }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    SECRET_KEY             = random_password.secret_key.result
    MASTER_ENCRYPTION_KEY  = random_password.encryption_key.result
    OPENAI_API_KEY        = var.openai_api_key
    GEMINI_API_KEY        = var.gemini_api_key
    SENDGRID_API_KEY      = var.sendgrid_api_key
  })
}

# Random passwords for application secrets
resource "random_password" "secret_key" {
  length  = 64
  special = true
}

resource "random_password" "encryption_key" {
  length  = 44  # Base64 encoded 32 bytes
  special = false
}

# JWT Signing Key
resource "aws_secretsmanager_secret" "jwt_key" {
  name = "${var.project_name}/jwt-signing-key"
  
  tags = {
    Name = "${var.project_name}-jwt-key"
  }
}

resource "aws_secretsmanager_secret_version" "jwt_key" {
  secret_id     = aws_secretsmanager_secret.jwt_key.id
  secret_string = random_password.jwt_key.result
}

resource "random_password" "jwt_key" {
  length  = 64
  special = true
}

# API Keys Secret
resource "aws_secretsmanager_secret" "api_keys" {
  name = "${var.project_name}/api-keys"
  
  tags = {
    Name = "${var.project_name}-api-keys"
  }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    OPENAI_API_KEY    = var.openai_api_key
    GEMINI_API_KEY    = var.gemini_api_key
    SENDGRID_API_KEY  = var.sendgrid_api_key
  })
}

# Variables for sensitive data (to be provided via terraform.tfvars or environment)
variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gemini_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sendgrid_api_key" {
  description = "SendGrid API key"
  type        = string
  sensitive   = true
  default     = ""
}

# KMS Key for additional encryption
resource "aws_kms_key" "main" {
  description             = "KMS key for ${var.project_name}"
  deletion_window_in_days = 7
  
  tags = {
    Name = "${var.project_name}-kms-key"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project_name}"
  target_key_id = aws_kms_key.main.key_id
}

# Outputs
output "kms_key_id" {
  description = "KMS key ID"
  value       = aws_kms_key.main.key_id
}

output "kms_key_arn" {
  description = "KMS key ARN"
  value       = aws_kms_key.main.arn
}