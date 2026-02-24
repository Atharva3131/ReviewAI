# Staging-specific backend configuration
# This file is used when deploying to the staging environment

terraform {
  backend "s3" {
    bucket         = "revive-ai-terraform-state"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "revive-ai-terraform-locks"
  }
}
