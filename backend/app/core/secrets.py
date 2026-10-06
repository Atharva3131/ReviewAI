"""
AWS Secrets Manager Helper
Allows loading JSON secrets from AWS Secrets Manager at application startup
when running in AWS ECS environments.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


def fetch_aws_secret(secret_name: str, region_name: str = "us-east-1") -> Optional[Dict[str, Any]]:
    """Fetch and parse JSON secret from AWS Secrets Manager"""
    if not BOTO3_AVAILABLE or not secret_name:
        return None

    try:
        client = boto3.client("secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_name)
        if "SecretString" in response:
            secret = json.loads(response["SecretString"])
            logger.info(f"Successfully retrieved secret '{secret_name}' from AWS Secrets Manager")
            return secret
    except Exception as e:
        logger.warning(f"Could not fetch secret '{secret_name}' from AWS Secrets Manager: {e}")
    return None


def inject_secrets_to_env(secret_name: Optional[str] = None, region_name: str = "us-east-1") -> None:
    """Fetch AWS secret and inject key-values into os.environ if not already present"""
    s_name = secret_name or os.getenv("AWS_SECRETS_MANAGER_SECRET_NAME")
    if not s_name:
        return

    secrets = fetch_aws_secret(s_name, region_name=region_name)
    if secrets and isinstance(secrets, dict):
        for key, val in secrets.items():
            if key not in os.environ and val is not None:
                os.environ[key] = str(val)
        logger.info(f"Injected {len(secrets)} key(s) from Secrets Manager into environment variables")
