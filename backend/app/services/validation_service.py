"""
Validation and sanitization service for review content
"""

import html
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import bleach
from profanity_check import predict as is_profane

from app.models.review import ReviewPlatform


class ValidationService:
    """Service for validating and sanitizing review content"""

    # Allowed HTML tags for review content
    ALLOWED_TAGS = ["p", "br", "strong", "em", "u"]
    ALLOWED_ATTRIBUTES = {}

    # Common spam indicators
    SPAM_KEYWORDS = {
        "click here",
        "free money",
        "make money fast",
        "work from home",
        "buy now",
        "limited time",
        "act now",
        "guaranteed",
        "risk free",
        "no obligation",
        "call now",
        "order now",
        "visit our website",
    }

    # Platform-specific validation rules
    PLATFORM_RULES = {
        ReviewPlatform.GOOGLE: {
            "max_content_length": 5000,
            "min_content_length": 10,
            "allow_html": False,
            "require_rating": True,
        },
        ReviewPlatform.YELP: {
            "max_content_length": 5000,
            "min_content_length": 15,
            "allow_html": False,
            "require_rating": True,
        },
        ReviewPlatform.FACEBOOK: {
            "max_content_length": 8000,
            "min_content_length": 5,
            "allow_html": True,
            "require_rating": False,
        },
        ReviewPlatform.TRUSTPILOT: {
            "max_content_length": 2500,
            "min_content_length": 20,
            "allow_html": False,
            "require_rating": True,
        },
    }

    @staticmethod
    def validate_review_content(
        content: Optional[str], platform: ReviewPlatform, rating: int
    ) -> Dict[str, Any]:
        """Validate review content comprehensively"""

        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "sanitized_content": content,
            "spam_score": 0.0,
            "quality_score": 0.0,
        }

        if not content or not content.strip():
            if (
                ValidationService.PLATFORM_RULES[platform].get("require_rating")
                and rating
            ):
                # Rating-only review is acceptable for some platforms
                validation_result["quality_score"] = 0.3
                return validation_result
            else:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Review content is required")
                return validation_result

        content = content.strip()
        platform_rules = ValidationService.PLATFORM_RULES.get(platform, {})

        # Length validation
        min_length = platform_rules.get("min_content_length", 10)
        max_length = platform_rules.get("max_content_length", 5000)

        if len(content) < min_length:
            validation_result["errors"].append(
                f"Review content too short (minimum {min_length} characters)"
            )
            validation_result["is_valid"] = False

        if len(content) > max_length:
            validation_result["errors"].append(
                f"Review content too long (maximum {max_length} characters)"
            )
            validation_result["is_valid"] = False

        # Sanitize content
        sanitized = ValidationService._sanitize_content(
            content, platform_rules.get("allow_html", False)
        )
        validation_result["sanitized_content"] = sanitized

        # Spam detection
        spam_score = ValidationService._calculate_spam_score(content)
        validation_result["spam_score"] = spam_score

        if spam_score > 0.7:
            validation_result["errors"].append("Content appears to be spam")
            validation_result["is_valid"] = False
        elif spam_score > 0.4:
            validation_result["warnings"].append(
                "Content may contain promotional material"
            )

        # Quality assessment
        quality_score = ValidationService._calculate_quality_score(content, rating)
        validation_result["quality_score"] = quality_score

        if quality_score < 0.2:
            validation_result["warnings"].append("Review content quality is low")

        # Profanity check
        if ValidationService._contains_excessive_profanity(content):
            validation_result["warnings"].append(
                "Review contains inappropriate language"
            )

        # URL validation
        urls = ValidationService._extract_urls(content)
        if urls:
            validation_result["warnings"].append(f"Review contains {len(urls)} URL(s)")
            # Could implement URL validation/filtering here

        return validation_result

    @staticmethod
    def validate_customer_info(
        customer_name: Optional[str], customer_email: Optional[str]
    ) -> Dict[str, Any]:
        """Validate customer information"""

        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "sanitized_name": customer_name,
            "sanitized_email": customer_email,
        }

        # Name validation
        if customer_name:
            sanitized_name = ValidationService._sanitize_name(customer_name)
            validation_result["sanitized_name"] = sanitized_name

            if len(sanitized_name) > 100:
                validation_result["errors"].append("Customer name too long")
                validation_result["is_valid"] = False

            if not re.match(r"^[a-zA-Z\s\-\.\']+$", sanitized_name):
                validation_result["warnings"].append(
                    "Customer name contains unusual characters"
                )

        # Email validation
        if customer_email:
            email_validation = ValidationService._validate_email(customer_email)
            validation_result["sanitized_email"] = email_validation["sanitized_email"]

            if not email_validation["is_valid"]:
                validation_result["errors"].append("Invalid email format")
                validation_result["is_valid"] = False

        return validation_result

    @staticmethod
    def validate_rating(rating: int, platform: ReviewPlatform) -> Dict[str, Any]:
        """Validate review rating"""

        validation_result = {"is_valid": True, "errors": [], "warnings": []}

        if not isinstance(rating, int):
            validation_result["errors"].append("Rating must be an integer")
            validation_result["is_valid"] = False
            return validation_result

        if rating < 1 or rating > 5:
            validation_result["errors"].append("Rating must be between 1 and 5")
            validation_result["is_valid"] = False

        return validation_result

    @staticmethod
    def _sanitize_content(content: str, allow_html: bool = False) -> str:
        """Sanitize review content"""

        # HTML escape if HTML not allowed
        if not allow_html:
            content = html.escape(content)
        else:
            # Clean HTML with bleach
            content = bleach.clean(
                content,
                tags=ValidationService.ALLOWED_TAGS,
                attributes=ValidationService.ALLOWED_ATTRIBUTES,
                strip=True,
            )

        # Remove excessive whitespace
        content = re.sub(r"\s+", " ", content).strip()

        # Remove control characters
        content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", content)

        return content

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize customer name"""

        # Remove HTML
        name = html.escape(name)

        # Remove excessive whitespace
        name = re.sub(r"\s+", " ", name).strip()

        # Title case
        name = name.title()

        return name

    @staticmethod
    def _validate_email(email: str) -> Dict[str, Any]:
        """Validate and sanitize email"""

        result = {"is_valid": False, "sanitized_email": email.lower().strip()}

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if re.match(email_pattern, result["sanitized_email"]):
            result["is_valid"] = True

        return result

    @staticmethod
    def _calculate_spam_score(content: str) -> float:
        """Calculate spam probability score"""

        score = 0.0
        content_lower = content.lower()

        # Check for spam keywords
        spam_keyword_count = sum(
            1 for keyword in ValidationService.SPAM_KEYWORDS if keyword in content_lower
        )
        score += min(spam_keyword_count * 0.2, 0.6)

        # Check for excessive capitalization
        if len(content) > 20:
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if caps_ratio > 0.5:
                score += 0.3

        # Check for excessive punctuation
        punct_count = sum(1 for c in content if c in "!?.")
        if punct_count > len(content) * 0.1:
            score += 0.2

        # Check for repeated characters
        if re.search(r"(.)\1{4,}", content):
            score += 0.2

        # Check for excessive URLs
        url_count = len(ValidationService._extract_urls(content))
        if url_count > 2:
            score += min(url_count * 0.15, 0.4)

        return min(score, 1.0)

    @staticmethod
    def _calculate_quality_score(content: str, rating: int) -> float:
        """Calculate content quality score"""

        score = 0.0

        # Length factor
        length = len(content)
        if length >= 50:
            score += 0.3
        elif length >= 20:
            score += 0.2
        else:
            score += 0.1

        # Sentence structure
        sentences = content.split(".")
        if len(sentences) > 1:
            score += 0.2

        # Word variety
        words = content.lower().split()
        unique_words = set(words)
        if len(words) > 0:
            variety_ratio = len(unique_words) / len(words)
            score += min(variety_ratio * 0.3, 0.3)

        # Rating-content consistency
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "love",
            "perfect",
            "wonderful",
        ]
        negative_words = [
            "bad",
            "terrible",
            "awful",
            "hate",
            "worst",
            "horrible",
            "disappointing",
        ]

        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if rating >= 4 and positive_count > negative_count:
            score += 0.2
        elif rating <= 2 and negative_count > positive_count:
            score += 0.2
        elif rating == 3:
            score += 0.1  # Neutral reviews are acceptable

        return min(score, 1.0)

    @staticmethod
    def _contains_excessive_profanity(content: str) -> bool:
        """Check for excessive profanity"""
        try:
            # Using profanity-check library
            return is_profane(content)
        except Exception:
            # Fallback to basic word list check
            profane_words = ["damn", "hell", "shit", "fuck", "bitch", "ass"]
            content_lower = content.lower()
            profane_count = sum(1 for word in profane_words if word in content_lower)
            return profane_count > 2

    @staticmethod
    def _extract_urls(content: str) -> List[str]:
        """Extract URLs from content"""

        url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        urls = re.findall(url_pattern, content)

        # Also check for www. patterns
        www_pattern = r"www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        www_urls = re.findall(www_pattern, content)

        return urls + www_urls

    @staticmethod
    def validate_external_id(external_id: str, platform: ReviewPlatform) -> bool:
        """Validate external review ID format"""

        if not external_id or len(external_id.strip()) == 0:
            return False

        # Platform-specific ID validation
        if platform == ReviewPlatform.GOOGLE:
            # Google review IDs are typically long alphanumeric strings
            return (
                len(external_id) > 10
                and external_id.replace("-", "").replace("_", "").isalnum()
            )

        elif platform == ReviewPlatform.YELP:
            # Yelp review IDs have specific format
            return len(external_id) > 15 and external_id.replace("-", "").isalnum()

        # Generic validation for other platforms
        return (
            len(external_id) <= 255
            and external_id.replace("-", "").replace("_", "").isalnum()
        )

    @staticmethod
    def validate_review_url(url: str, platform: ReviewPlatform) -> bool:
        """Validate review URL format"""

        if not url:
            return True  # URL is optional

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False

            # Platform-specific URL validation
            if platform == ReviewPlatform.GOOGLE:
                return "google" in parsed.netloc.lower()
            elif platform == ReviewPlatform.YELP:
                return "yelp" in parsed.netloc.lower()
            elif platform == ReviewPlatform.FACEBOOK:
                return "facebook" in parsed.netloc.lower()
            elif platform == ReviewPlatform.TRUSTPILOT:
                return "trustpilot" in parsed.netloc.lower()

            return True  # Generic URL validation passed

        except Exception:
            return False
