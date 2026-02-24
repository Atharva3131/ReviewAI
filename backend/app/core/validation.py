"""
Input validation and sanitization service for security
"""
import re
import html
import bleach
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, field_validator
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.field = field
        self.details = details or {}
        super().__init__(self.message)


class InputSanitizer:
    """Service for sanitizing user inputs to prevent security vulnerabilities"""
    
    # Allowed HTML tags for rich text content (very restrictive)
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'a', 'span'
    ]
    
    # Allowed HTML attributes
    ALLOWED_HTML_ATTRIBUTES = {
        'a': ['href', 'title'],
        'span': ['class'],
    }
    
    # SQL injection patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
        r"(INFORMATION_SCHEMA|SYSOBJECTS|SYSCOLUMNS)",
        r"(\bxp_\w+)",
        r"(\bsp_\w+)",
    ]
    
    # XSS patterns to detect
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"onfocus\s*=",
        r"onblur\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<form[^>]*>",
        r"<input[^>]*>",
        r"<meta[^>]*>",
        r"<link[^>]*>",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
        r"..%2f",
        r"..%5c",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = None, allow_html: bool = False) -> str:
        """
        Sanitize string input to prevent XSS and other attacks
        
        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow safe HTML tags
            
        Returns:
            Sanitized string
            
        Raises:
            ValidationError: If input is invalid or potentially malicious
        """
        if not isinstance(value, str):
            raise ValidationError("Input must be a string", details={"type": type(value).__name__})
        
        # Check length
        if max_length and len(value) > max_length:
            raise ValidationError(
                f"Input too long (max {max_length} characters)", 
                details={"length": len(value), "max_length": max_length}
            )
        
        # Detect potential SQL injection
        cls._detect_sql_injection(value)
        
        # Detect potential XSS
        cls._detect_xss_attempts(value)
        
        # Detect path traversal
        cls._detect_path_traversal(value)
        
        # Sanitize based on HTML allowance
        if allow_html:
            # Use bleach to clean HTML
            sanitized = bleach.clean(
                value,
                tags=cls.ALLOWED_HTML_TAGS,
                attributes=cls.ALLOWED_HTML_ATTRIBUTES,
                strip=True
            )
        else:
            # Escape HTML entities
            sanitized = html.escape(value, quote=True)
        
        # Additional cleanup
        sanitized = cls._clean_unicode_control_chars(sanitized)
        sanitized = cls._normalize_whitespace(sanitized)
        
        return sanitized.strip()
    
    @classmethod
    def sanitize_email(cls, email: str) -> str:
        """
        Sanitize and validate email address
        
        Args:
            email: Email address to sanitize
            
        Returns:
            Sanitized email address
            
        Raises:
            ValidationError: If email is invalid
        """
        if not isinstance(email, str):
            raise ValidationError("Email must be a string")
        
        # Basic sanitization
        email = email.strip().lower()
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")
        
        # Check for suspicious patterns
        if any(pattern in email for pattern in ['..', '+', '--']):
            # Allow single dots and plus signs, but be suspicious of multiples
            if '..' in email or '--' in email:
                raise ValidationError("Email contains suspicious patterns")
        
        # Check length
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError("Email address too long")
        
        # Check domain part
        local, domain = email.rsplit('@', 1)
        if len(local) > 64:  # RFC 5321 limit
            raise ValidationError("Email local part too long")
        
        return email
    
    @classmethod
    def sanitize_url(cls, url: str, allowed_schemes: List[str] = None) -> str:
        """
        Sanitize and validate URL
        
        Args:
            url: URL to sanitize
            allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
            
        Returns:
            Sanitized URL
            
        Raises:
            ValidationError: If URL is invalid or uses disallowed scheme
        """
        if not isinstance(url, str):
            raise ValidationError("URL must be a string")
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        # Basic sanitization
        url = url.strip()
        
        # Parse URL
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {e}")
        
        # Check scheme
        if parsed.scheme.lower() not in allowed_schemes:
            raise ValidationError(
                f"URL scheme '{parsed.scheme}' not allowed", 
                details={"allowed_schemes": allowed_schemes}
            )
        
        # Check for suspicious patterns
        cls._detect_path_traversal(url)
        
        # Reconstruct URL to normalize it
        sanitized_url = urllib.parse.urlunparse(parsed)
        
        return sanitized_url
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal and other attacks
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
            
        Raises:
            ValidationError: If filename is invalid or potentially dangerous
        """
        if not isinstance(filename, str):
            raise ValidationError("Filename must be a string")
        
        # Basic sanitization
        filename = filename.strip()
        
        # Check for path traversal
        cls._detect_path_traversal(filename)
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        for char in dangerous_chars:
            if char in filename:
                raise ValidationError(f"Filename contains dangerous character: {char}")
        
        # Remove path separators
        if '/' in filename or '\\' in filename:
            raise ValidationError("Filename cannot contain path separators")
        
        # Check for reserved names (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
            'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
            'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = filename.split('.')[0].upper()
        if name_without_ext in reserved_names:
            raise ValidationError(f"Filename uses reserved name: {name_without_ext}")
        
        # Check length
        if len(filename) > 255:
            raise ValidationError("Filename too long (max 255 characters)")
        
        # Ensure filename is not empty after sanitization
        if not filename or filename in ['.', '..']:
            raise ValidationError("Invalid filename")
        
        return filename
    
    @classmethod
    def sanitize_json_field(cls, value: Any, field_name: str) -> Any:
        """
        Sanitize JSON field values recursively
        
        Args:
            value: Value to sanitize
            field_name: Name of the field (for error reporting)
            
        Returns:
            Sanitized value
        """
        if isinstance(value, str):
            return cls.sanitize_string(value, max_length=10000)
        elif isinstance(value, dict):
            return {
                cls.sanitize_string(k, max_length=100): cls.sanitize_json_field(v, f"{field_name}.{k}")
                for k, v in value.items()
            }
        elif isinstance(value, list):
            return [cls.sanitize_json_field(item, f"{field_name}[{i}]") for i, item in enumerate(value)]
        elif isinstance(value, (int, float, bool)) or value is None:
            return value
        else:
            # Convert other types to string and sanitize
            return cls.sanitize_string(str(value), max_length=1000)
    
    @classmethod
    def _detect_sql_injection(cls, value: str) -> None:
        """Detect potential SQL injection attempts"""
        value_lower = value.lower()
        
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                raise ValidationError(
                    "Input contains potentially malicious SQL patterns",
                    details={"pattern": pattern, "input_sample": value[:100]}
                )
    
    @classmethod
    def _detect_xss_attempts(cls, value: str) -> None:
        """Detect potential XSS attempts"""
        value_lower = value.lower()
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"Potential XSS detected: {pattern}")
                raise ValidationError(
                    "Input contains potentially malicious script patterns",
                    details={"pattern": pattern, "input_sample": value[:100]}
                )
    
    @classmethod
    def _detect_path_traversal(cls, value: str) -> None:
        """Detect potential path traversal attempts"""
        value_lower = value.lower()
        
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"Potential path traversal detected: {pattern}")
                raise ValidationError(
                    "Input contains potentially malicious path patterns",
                    details={"pattern": pattern, "input_sample": value[:100]}
                )
    
    @classmethod
    def _clean_unicode_control_chars(cls, value: str) -> str:
        """Remove Unicode control characters"""
        # Remove control characters except for common whitespace
        allowed_control_chars = {'\t', '\n', '\r'}
        cleaned = ''.join(
            char for char in value 
            if not (ord(char) < 32 and char not in allowed_control_chars)
        )
        return cleaned
    
    @classmethod
    def _normalize_whitespace(cls, value: str) -> str:
        """Normalize whitespace characters"""
        # Replace multiple whitespace with single space
        normalized = re.sub(r'\s+', ' ', value)
        return normalized


class InputValidator:
    """Service for validating business logic constraints"""
    
    @staticmethod
    def validate_rating(rating: int) -> int:
        """Validate review rating"""
        if not isinstance(rating, int):
            raise ValidationError("Rating must be an integer")
        
        if not (1 <= rating <= 5):
            raise ValidationError("Rating must be between 1 and 5")
        
        return rating
    
    @staticmethod
    def validate_sentiment_score(score: float) -> float:
        """Validate sentiment score"""
        if not isinstance(score, (int, float)):
            raise ValidationError("Sentiment score must be a number")
        
        if not (0.0 <= score <= 1.0):
            raise ValidationError("Sentiment score must be between 0.0 and 1.0")
        
        return float(score)
    
    @staticmethod
    def validate_urgency_level(level: str) -> str:
        """Validate urgency level"""
        allowed_levels = ['low', 'medium', 'high']
        
        if not isinstance(level, str):
            raise ValidationError("Urgency level must be a string")
        
        level = level.lower().strip()
        
        if level not in allowed_levels:
            raise ValidationError(
                f"Urgency level must be one of: {', '.join(allowed_levels)}",
                details={"allowed_levels": allowed_levels}
            )
        
        return level
    
    @staticmethod
    def validate_issue_categories(categories: List[str]) -> List[str]:
        """Validate issue categories"""
        allowed_categories = ['support', 'pricing', 'delivery', 'quality']
        
        if not isinstance(categories, list):
            raise ValidationError("Issue categories must be a list")
        
        if len(categories) > 4:
            raise ValidationError("Too many issue categories (max 4)")
        
        validated_categories = []
        for category in categories:
            if not isinstance(category, str):
                raise ValidationError("Each category must be a string")
            
            category = category.lower().strip()
            
            if category not in allowed_categories:
                raise ValidationError(
                    f"Invalid category '{category}'. Must be one of: {', '.join(allowed_categories)}",
                    details={"allowed_categories": allowed_categories}
                )
            
            if category not in validated_categories:
                validated_categories.append(category)
        
        return validated_categories
    
    @staticmethod
    def validate_phone_number(phone: str) -> str:
        """Validate and normalize phone number"""
        if not isinstance(phone, str):
            raise ValidationError("Phone number must be a string")
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Basic validation
        if not cleaned:
            raise ValidationError("Phone number cannot be empty")
        
        # Check for international format
        if cleaned.startswith('+'):
            if len(cleaned) < 8 or len(cleaned) > 16:
                raise ValidationError("Invalid international phone number length")
        else:
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValidationError("Invalid phone number length")
        
        return cleaned
    
    @staticmethod
    def validate_organization_name(name: str) -> str:
        """Validate organization name"""
        if not isinstance(name, str):
            raise ValidationError("Organization name must be a string")
        
        name = name.strip()
        
        if not name:
            raise ValidationError("Organization name cannot be empty")
        
        if len(name) < 2:
            raise ValidationError("Organization name must be at least 2 characters")
        
        if len(name) > 100:
            raise ValidationError("Organization name must be less than 100 characters")
        
        # Check for valid characters (letters, numbers, spaces, basic punctuation)
        if not re.match(r'^[a-zA-Z0-9\s\-\.\,\&\'\"]+$', name):
            raise ValidationError("Organization name contains invalid characters")
        
        return name


class SecurityValidator:
    """Additional security validations"""
    
    @staticmethod
    def validate_api_key_format(api_key: str) -> str:
        """Validate API key format"""
        if not isinstance(api_key, str):
            raise ValidationError("API key must be a string")
        
        # Check format: ra_<32 characters>
        if not re.match(r'^ra_[A-Za-z0-9_-]{32,}$', api_key):
            raise ValidationError("Invalid API key format")
        
        return api_key
    
    @staticmethod
    def validate_webhook_signature(signature: str, payload: str, secret: str) -> bool:
        """Validate webhook signature"""
        import hmac
        import hashlib
        
        if not all([signature, payload, secret]):
            return False
        
        # Calculate expected signature
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures using constant-time comparison
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def validate_csrf_token(token: str, session_token: str) -> bool:
        """Validate CSRF token"""
        import hmac
        
        if not token or not session_token:
            return False
        
        return hmac.compare_digest(token, session_token)


# Pydantic validators for use in schemas
def sanitize_string_validator(max_length: int = None, allow_html: bool = False):
    """Create a Pydantic validator for string sanitization"""
    def validator_func(cls, v):
        if v is None:
            return v
        return InputSanitizer.sanitize_string(v, max_length=max_length, allow_html=allow_html)
    return validator('*', pre=True, allow_reuse=True)(validator_func)


def sanitize_email_validator():
    """Create a Pydantic validator for email sanitization"""
    def validator_func(cls, v):
        if v is None:
            return v
        return InputSanitizer.sanitize_email(v)
    return validator('*', pre=True, allow_reuse=True)(validator_func)


def sanitize_url_validator(allowed_schemes: List[str] = None):
    """Create a Pydantic validator for URL sanitization"""
    def validator_func(cls, v):
        if v is None:
            return v
        return InputSanitizer.sanitize_url(v, allowed_schemes=allowed_schemes)
    return validator('*', pre=True, allow_reuse=True)(validator_func)
