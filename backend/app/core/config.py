"""
Configuration settings for Revive AI
"""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ReviewAI"
    APP_ENV: str = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Decision Model
    DECISION_MODEL_PROVIDER: str = os.getenv("DECISION_MODEL_PROVIDER", "mock")
    LAYA_MODEL_PATH: Optional[str] = os.getenv("LAYA_MODEL_PATH")
    ML_MODEL_PATH: Optional[str] = os.getenv("ML_MODEL_PATH")

    # Database Settings (RDS PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/revive_ai"
    )
    DB_HOST: Optional[str] = os.getenv("DB_HOST")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "revive_ai")
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_SSL: bool = os.getenv("DB_SSL", "false").lower() == "true"

    # Redis Settings (ElastiCache / Local)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_HOST: Optional[str] = os.getenv("REDIS_HOST")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"

    # CORS Configuration
    ALLOWED_HOSTS: str = os.getenv("CORS_ALLOWED_ORIGINS", os.getenv("ALLOWED_HOSTS", "http://localhost:3000,http://localhost:8000"))

    @property
    def allowed_hosts_list(self) -> List[str]:
        """Parse ALLOWED_HOSTS string into a list"""
        if isinstance(self.ALLOWED_HOSTS, str):
            return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]
        return self.ALLOWED_HOSTS

    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: Optional[str] = os.getenv("AWS_S3_BUCKET")
    AWS_S3_PREFIX: str = os.getenv("AWS_S3_PREFIX", "reviewai/")
    AWS_SECRETS_MANAGER_SECRET_NAME: Optional[str] = os.getenv("AWS_SECRETS_MANAGER_SECRET_NAME")

    # Amazon Bedrock Settings
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    BEDROCK_REGION: str = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-east-1"))
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", os.getenv("DEFAULT_LLM_PROVIDER", "bedrock"))
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "bedrock"))

    # Legacy LLM Keys (Optional)
    MISTRAL_API_KEY: Optional[str] = os.getenv("MISTRAL_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

    # External Services
    SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY")
    WHATSAPP_API_KEY: Optional[str] = os.getenv("WHATSAPP_API_KEY")

    # Stripe Configuration
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Webhook Security
    GOOGLE_WEBHOOK_SECRET: Optional[str] = os.getenv("GOOGLE_WEBHOOK_SECRET")
    CRM_WEBHOOK_SECRET: Optional[str] = os.getenv("CRM_WEBHOOK_SECRET")

    # Background Tasks
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379"))
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379"))

    # Monitoring & Logging
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development"))

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
