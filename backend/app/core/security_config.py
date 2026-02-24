"""
Security configuration and settings for Revive AI
"""
import os
from typing import Dict, List, Optional
from pydantic import BaseSettings, field_validator
from enum import Enum


class SecurityLevel(Enum):
    """Security level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecuritySettings(BaseSettings):
    """Security-specific settings"""
    
    # General Security
    SECURITY_LEVEL: SecurityLevel = SecurityLevel.HIGH
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_CSRF_PROTECTION: bool = True
    ENABLE_INPUT_SANITIZATION: bool = True
    ENABLE_SQL_INJECTION_PROTECTION: bool = True
    ENABLE_XSS_PROTECTION: bool = True
    
    # Rate Limiting
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_DDOS_PROTECTION: bool = True
    GLOBAL_RATE_LIMIT_PER_MINUTE: int = 1000
    BURST_RATE_LIMIT_PER_SECOND: int = 20
    
    # IP Filtering
    ENABLE_IP_WHITELIST: bool = False
    IP_WHITELIST: List[str] = []
    IP_BLACKLIST: List[str] = []
    
    # Authentication & Authorization
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_DURATION_MINUTES: int = 15
    
    # Session Security
    SESSION_TIMEOUT_MINUTES: int = 60
    ENABLE_SESSION_ROTATION: bool = True
    
    # Content Security Policy
    CSP_DEFAULT_SRC: List[str] = ["'self'"]
    CSP_SCRIPT_SRC: List[str] = ["'self'", "'unsafe-inline'"]
    CSP_STYLE_SRC: List[str] = ["'self'", "'unsafe-inline'"]
    CSP_IMG_SRC: List[str] = ["'self'", "data:", "https:"]
    CSP_FONT_SRC: List[str] = ["'self'", "data:"]
    CSP_CONNECT_SRC: List[str] = ["'self'"]
    
    # HSTS (HTTP Strict Transport Security)
    HSTS_MAX_AGE: int = 31536000  # 1 year
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    HSTS_PRELOAD: bool = True
    
    # CORS
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    CORS_EXPOSE_HEADERS: List[str] = [
        "X-Request-ID", 
        "X-Process-Time", 
        "X-RateLimit-Limit", 
        "X-RateLimit-Remaining",
        "X-CSRF-Token"
    ]
    
    # Audit Logging
    ENABLE_AUDIT_LOGGING: bool = True
    AUDIT_LOG_SENSITIVE_ENDPOINTS: bool = True
    AUDIT_LOG_FAILED_ATTEMPTS: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 90
    
    # File Upload Security
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_EXTENSIONS: List[str] = [".csv", ".json", ".txt"]
    SCAN_UPLOADED_FILES: bool = True
    
    # API Security
    ENABLE_API_KEY_AUTHENTICATION: bool = True
    API_KEY_HEADER_NAME: str = "X-API-Key"
    API_KEY_ROTATION_DAYS: int = 90
    
    # Webhook Security
    WEBHOOK_SIGNATURE_HEADER: str = "X-Signature"
    WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS: int = 300  # 5 minutes
    
    # Database Security
    DB_CONNECTION_TIMEOUT: int = 30
    DB_QUERY_TIMEOUT: int = 60
    DB_MAX_CONNECTIONS: int = 20
    ENABLE_DB_QUERY_LOGGING: bool = False  # Only enable in development
    
    # Encryption
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    ENABLE_DATA_ENCRYPTION_AT_REST: bool = True
    
    # Monitoring & Alerting
    ENABLE_SECURITY_MONITORING: bool = True
    SECURITY_ALERT_THRESHOLD_MINUTES: int = 5
    MAX_FAILED_REQUESTS_PER_MINUTE: int = 50
    
    # Development/Testing
    DISABLE_SECURITY_IN_TESTS: bool = False
    SECURITY_BYPASS_TOKEN: Optional[str] = None
    
    class Config:
        env_prefix = "SECURITY_"
        env_file = ".env"
    
    @field_validator("SECURITY_LEVEL", pre=True)
    def validate_security_level(cls, v):
        if isinstance(v, str):
            return SecurityLevel(v.lower())
        return v
    
    @field_validator("IP_WHITELIST", "IP_BLACKLIST", pre=True)
    def validate_ip_lists(cls, v):
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v or []
    
    @field_validator("CSP_DEFAULT_SRC", "CSP_SCRIPT_SRC", "CSP_STYLE_SRC", "CSP_IMG_SRC", 
              "CSP_FONT_SRC", "CSP_CONNECT_SRC", pre=True)
    def validate_csp_lists(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v or []


class SecurityPolicies:
    """Security policies and rules"""
    
    # Password complexity rules
    PASSWORD_RULES = {
        "min_length": 8,
        "max_length": 128,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_digits": True,
        "require_special_chars": True,
        "forbidden_patterns": [
            "password", "123456", "qwerty", "admin", "user",
            "letmein", "welcome", "monkey", "dragon"
        ],
        "max_repeated_chars": 3,
        "max_sequential_chars": 3
    }
    
    # Rate limiting policies by endpoint category
    RATE_LIMIT_POLICIES = {
        "authentication": {
            "requests_per_minute": 10,
            "burst_requests": 3,
            "lockout_duration_minutes": 15
        },
        "api_general": {
            "requests_per_minute": 100,
            "burst_requests": 20,
            "lockout_duration_minutes": 5
        },
        "api_premium": {
            "requests_per_minute": 500,
            "burst_requests": 50,
            "lockout_duration_minutes": 1
        },
        "webhooks": {
            "requests_per_minute": 1000,
            "burst_requests": 100,
            "lockout_duration_minutes": 1
        }
    }
    
    # Content Security Policy templates
    CSP_TEMPLATES = {
        "strict": {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'"],
            "img-src": ["'self'", "data:"],
            "font-src": ["'self'"],
            "connect-src": ["'self'"],
            "object-src": ["'none'"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"]
        },
        "moderate": {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "data:"],
            "connect-src": ["'self'"],
            "object-src": ["'none'"],
            "frame-ancestors": ["'none'"]
        },
        "relaxed": {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["*", "data:"],
            "font-src": ["*", "data:"],
            "connect-src": ["*"]
        }
    }
    
    # Security headers configuration
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cross-Origin-Embedder-Policy": "require-corp",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Permissions-Policy": (
            "camera=(), microphone=(), geolocation=(), "
            "interest-cohort=(), payment=(), usb=(), "
            "bluetooth=(), magnetometer=(), gyroscope=(), "
            "accelerometer=()"
        )
    }
    
    # Audit logging configuration
    AUDIT_EVENTS = {
        "authentication": {
            "login_success": {"level": "info", "retention_days": 30},
            "login_failure": {"level": "warning", "retention_days": 90},
            "logout": {"level": "info", "retention_days": 30},
            "password_change": {"level": "info", "retention_days": 90},
            "account_lockout": {"level": "error", "retention_days": 90}
        },
        "authorization": {
            "access_granted": {"level": "info", "retention_days": 30},
            "access_denied": {"level": "warning", "retention_days": 90},
            "privilege_escalation": {"level": "error", "retention_days": 365}
        },
        "data_access": {
            "sensitive_data_access": {"level": "info", "retention_days": 90},
            "bulk_data_export": {"level": "warning", "retention_days": 365},
            "unauthorized_access_attempt": {"level": "error", "retention_days": 365}
        },
        "system": {
            "configuration_change": {"level": "warning", "retention_days": 365},
            "security_policy_change": {"level": "error", "retention_days": 365},
            "system_error": {"level": "error", "retention_days": 90}
        }
    }


class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_security_config(settings: SecuritySettings) -> Dict[str, List[str]]:
        """Validate security configuration and return warnings/errors"""
        warnings = []
        errors = []
        
        # Check security level consistency
        if settings.SECURITY_LEVEL == SecurityLevel.HIGH:
            if not settings.ENABLE_CSRF_PROTECTION:
                warnings.append("CSRF protection should be enabled for HIGH security level")
            if not settings.ENABLE_INPUT_SANITIZATION:
                warnings.append("Input sanitization should be enabled for HIGH security level")
            if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 60:
                warnings.append("Access token expiration should be <= 60 minutes for HIGH security")
        
        # Check password policy
        if settings.PASSWORD_MIN_LENGTH < 8:
            errors.append("Password minimum length should be at least 8 characters")
        
        # Check rate limiting
        if settings.ENABLE_RATE_LIMITING and settings.GLOBAL_RATE_LIMIT_PER_MINUTE > 10000:
            warnings.append("Global rate limit seems very high - consider lowering it")
        
        # Check CORS configuration
        if "*" in settings.CORS_ALLOW_ORIGINS and settings.CORS_ALLOW_CREDENTIALS:
            errors.append("Cannot use wildcard CORS origins with credentials enabled")
        
        # Check HSTS configuration
        if settings.HSTS_MAX_AGE < 31536000:  # 1 year
            warnings.append("HSTS max-age should be at least 1 year (31536000 seconds)")
        
        return {"warnings": warnings, "errors": errors}
    
    @staticmethod
    def get_security_recommendations(settings: SecuritySettings) -> List[str]:
        """Get security recommendations based on current configuration"""
        recommendations = []
        
        if settings.SECURITY_LEVEL != SecurityLevel.HIGH:
            recommendations.append("Consider upgrading to HIGH security level for production")
        
        if not settings.ENABLE_AUDIT_LOGGING:
            recommendations.append("Enable audit logging for compliance and security monitoring")
        
        if not settings.ENABLE_DDOS_PROTECTION:
            recommendations.append("Enable DDoS protection for better resilience")
        
        if len(settings.IP_WHITELIST) == 0 and settings.ENABLE_IP_WHITELIST:
            recommendations.append("Configure IP whitelist or disable IP whitelisting")
        
        if settings.API_KEY_ROTATION_DAYS > 90:
            recommendations.append("Consider more frequent API key rotation (< 90 days)")
        
        return recommendations


# Global security settings instance
security_settings = SecuritySettings()

# Validate configuration on import
validation_result = SecurityValidator.validate_security_config(security_settings)
if validation_result["errors"]:
    raise ValueError(f"Security configuration errors: {validation_result['errors']}")

if validation_result["warnings"]:
    import logging
    logger = logging.getLogger(__name__)
    for warning in validation_result["warnings"]:
        logger.warning(f"Security configuration warning: {warning}")
