# Terraform Workspaces Configuration
# This file manages environment-specific configurations using Terraform workspaces

# Workspace-specific variables
locals {
  workspace_config = {
    production = {
      vpc_cidr = "10.0.0.0/16"
      public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
      private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
      enable_nat_gateway = true
      nat_gateway_count = 2
    }
    staging = {
      vpc_cidr = "10.1.0.0/16"
      public_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24"]
      private_subnet_cidrs = ["10.1.10.0/24", "10.1.11.0/24"]
      enable_nat_gateway = true
      nat_gateway_count = 1
    }
    dev = {
      vpc_cidr = "10.2.0.0/16"
      public_subnet_cidrs = ["10.2.1.0/24", "10.2.2.0/24"]
      private_subnet_cidrs = ["10.2.10.0/24", "10.2.11.0/24"]
      enable_nat_gateway = true
      nat_gateway_count = 1
    }
  }

  # Select configuration based on current workspace
  current_config = lookup(local.workspace_config, terraform.workspace, local.workspace_config["production"])
  
  # Environment-specific naming
  env_prefix = "${var.project_name}-${var.environment}"
}

# Output current workspace information
output "workspace_name" {
  description = "Current Terraform workspace"
  value       = terraform.workspace
}

output "environment" {
  description = "Current environment"
  value       = var.environment
}
