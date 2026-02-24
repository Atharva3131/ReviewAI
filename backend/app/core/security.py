"""
Security utilities for JWT authentication and password hashing
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import secrets
import string
import hashlib
import hmac
import re

from app.core.config import settings


# Password hashing context with multiple schemes for security
pwd_context = CryptContext(
    schemes=["bcrypt", "pbkdf2_sha256"],
    deprecated="auto",
    bcrypt__rounds=12,  # Higher rounds for better security
    pbkdf2_sha256__rounds=100000  # OWASP recommended rounds
)

# JWT settings
ALGORITHM = "HS256"

# Common weak passwords to reject
WEAK_PASSWORDS = {
    "password", "123456", "password123", "admin", "qwerty", 
    "letmein", "welcome", "monkey", "dragon", "master",
    "password1", "123456789", "12345678", "1234567890"
}


class SecurityService:
    """Service for handling authentication and security operations"""
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token with enhanced security"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        # Add security claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(16),  # JWT ID for token tracking
            "iss": "revive-ai",  # Issuer
            "aud": "revive-ai-api"  # Audience
        })
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create JWT refresh token with longer expiration"""
        data = {
            "sub": user_id,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(16),
            "iss": "revive-ai",
            "aud": "revive-ai-api"
        }
        return jwt.encode(data, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token with enhanced validation"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[ALGORITHM],
                audience="revive-ai-api",
                issuer="revive-ai"
            )
            
            # Additional validation
            if not payload.get("sub"):
                raise JWTError("Missing subject claim")
            
            if not payload.get("jti"):
                raise JWTError("Missing JWT ID claim")
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
    
    @staticmethod
    def get_user_id_from_token(token: str) -> str:
        """Extract user ID from JWT token"""
        payload = SecurityService.verify_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user_id
    
    @staticmethod
    def get_organization_id_from_token(token: str) -> str:
        """Extract organization ID from JWT token"""
        payload = SecurityService.verify_token(token)
        org_id: str = payload.get("org_id")
        
        if org_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing organization",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return org_id
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash with timing attack protection"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            # Perform dummy verification to prevent timing attacks
            pwd_context.verify("dummy_password", hashed_password)
            return False
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password with salt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def generate_password_reset_token() -> str:
        """Generate secure password reset token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_verification_token() -> str:
        """Generate email verification token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """Generate secure random password"""
        # Ensure we have at least one character from each category
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # Start with one character from each category
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest randomly
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength with comprehensive checks"""
        
        # Basic checks
        checks = {
            "length": len(password) >= 8,
            "max_length": len(password) <= 128,
            "uppercase": bool(re.search(r'[A-Z]', password)),
            "lowercase": bool(re.search(r'[a-z]', password)),
            "digit": bool(re.search(r'\d', password)),
            "special": bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password)),
            "no_whitespace": not bool(re.search(r'\s', password)),
            "not_common": password.lower() not in WEAK_PASSWORDS,
            "no_sequential": not SecurityService._has_sequential_chars(password),
            "no_repeated": not SecurityService._has_repeated_chars(password, 3)
        }
        
        # Calculate score
        score = sum(checks.values())
        max_score = len(checks)
        
        # Determine strength
        strength_ratio = score / max_score
        if strength_ratio >= 0.9:
            strength = "Very Strong"
        elif strength_ratio >= 0.8:
            strength = "Strong"
        elif strength_ratio >= 0.6:
            strength = "Medium"
        elif strength_ratio >= 0.4:
            strength = "Weak"
        else:
            strength = "Very Weak"
        
        # Password is valid if it meets minimum requirements
        is_valid = (
            checks["length"] and 
            checks["max_length"] and
            checks["uppercase"] and 
            checks["lowercase"] and 
            checks["digit"] and
            checks["not_common"] and
            checks["no_whitespace"]
        )
        
        return {
            "is_valid": is_valid,
            "score": score,
            "max_score": max_score,
            "strength": strength,
            "checks": checks,
            "recommendations": SecurityService._get_password_recommendations(checks)
        }
    
    @staticmethod
    def _has_sequential_chars(password: str, min_length: int = 3) -> bool:
        """Check for sequential characters (abc, 123, etc.)"""
        for i in range(len(password) - min_length + 1):
            substr = password[i:i + min_length].lower()
            
            # Check for sequential letters
            if all(ord(substr[j]) == ord(substr[0]) + j for j in range(len(substr))):
                return True
            
            # Check for sequential numbers
            if substr.isdigit() and all(int(substr[j]) == int(substr[0]) + j for j in range(len(substr))):
                return True
        
        return False
    
    @staticmethod
    def _has_repeated_chars(password: str, max_repeat: int = 3) -> bool:
        """Check for repeated characters"""
        for i in range(len(password) - max_repeat + 1):
            if len(set(password[i:i + max_repeat])) == 1:
                return True
        return False
    
    @staticmethod
    def _get_password_recommendations(checks: Dict[str, bool]) -> List[str]:
        """Get password improvement recommendations"""
        recommendations = []
        
        if not checks["length"]:
            recommendations.append("Use at least 8 characters")
        if not checks["uppercase"]:
            recommendations.append("Include at least one uppercase letter")
        if not checks["lowercase"]:
            recommendations.append("Include at least one lowercase letter")
        if not checks["digit"]:
            recommendations.append("Include at least one number")
        if not checks["special"]:
            recommendations.append("Include at least one special character")
        if not checks["not_common"]:
            recommendations.append("Avoid common passwords")
        if not checks["no_whitespace"]:
            recommendations.append("Remove spaces and whitespace")
        if not checks["no_sequential"]:
            recommendations.append("Avoid sequential characters (abc, 123)")
        if not checks["no_repeated"]:
            recommendations.append("Avoid repeated characters (aaa, 111)")
        
        return recommendations
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_csrf_token(token: str, expected_token: str) -> bool:
        """Verify CSRF token with timing attack protection"""
        return hmac.compare_digest(token, expected_token)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate API key"""
        return f"ra_{secrets.token_urlsafe(32)}"  # ra_ prefix for Revive AI
    
    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """Constant time string comparison to prevent timing attacks"""
        return hmac.compare_digest(a.encode(), b.encode())


class TokenData:
    """Token data structure with enhanced security"""
    
    def __init__(self, user_id: str, organization_id: str, email: str, role: str):
        self.user_id = user_id
        self.organization_id = organization_id
        self.email = email
        self.role = role
        self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JWT payload"""
        return {
            "sub": self.user_id,
            "org_id": self.organization_id,
            "email": self.email,
            "role": self.role,
            "type": "access"
        }


class SecurityAuditLog:
    """Security audit logging"""
    
    @staticmethod
    async def log_login_attempt(
        email: str, 
        success: bool, 
        ip_address: str, 
        user_agent: str,
        failure_reason: str = None
    ):
        """Log login attempt for security monitoring"""
        from app.core.redis import redis_client
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "login_attempt",
            "email": email,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "failure_reason": failure_reason
        }
        
        # Store in Redis for real-time monitoring
        await redis_client.set_json(
            f"security_log:{secrets.token_urlsafe(8)}",
            log_entry,
            expire=7 * 24 * 60 * 60  # 7 days
        )
    
    @staticmethod
    async def log_password_change(user_id: str, ip_address: str):
        """Log password change event"""
        from app.core.redis import redis_client
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "password_change",
            "user_id": user_id,
            "ip_address": ip_address
        }
        
        await redis_client.set_json(
            f"security_log:{secrets.token_urlsafe(8)}",
            log_entry,
            expire=30 * 24 * 60 * 60  # 30 days
        )


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


class AuthorizationError(Exception):
    """Custom authorization error"""
    pass
