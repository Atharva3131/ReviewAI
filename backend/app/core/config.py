"""
Configuration settings for Revive AI
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Revive AI"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/revive_ai"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # CORS
    ALLOWED_HOSTS: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Parse ALLOWED_HOSTS string into a list"""
        if isinstance(self.ALLOWED_HOSTS, str):
            return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
        return self.ALLOWED_HOSTS
    
    # LLM Settings
    MISTRAL_API_KEY: Optional[str] = os.getenv("MISTRAL_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    DEFAULT_LLM_PROVIDER: str = "openai"
    
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
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379")
    
    # Monitoring & Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        env_file = ".env"


settings = Settings()
