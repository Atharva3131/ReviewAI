# Optional non-production values. Keep credentials out of this file.
aws_region           = "us-east-1"
project_name         = "reviewai-staging"
environment          = "staging"
desired_count        = 1
db_instance_class    = "db.t4g.micro"
db_allocated_storage = 20
bedrock_model_id     = "anthropic.claude-3-haiku-20240307-v1:0"
