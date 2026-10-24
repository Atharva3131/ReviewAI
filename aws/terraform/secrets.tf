resource "random_password" "secret_key" {
  length  = 64
  special = false
}

resource "random_password" "encryption_key" {
  length  = 44
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name = "${var.project_name}/app"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    SECRET_KEY            = random_password.secret_key.result
    MASTER_ENCRYPTION_KEY = random_password.encryption_key.result
  })
}
