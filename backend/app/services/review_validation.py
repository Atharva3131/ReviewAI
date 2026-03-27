"""
Review validation and sanitization service
"""

import html
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import bleach

from app.schemas.review import ReviewIngest


class ReviewValidationService:
    """Service for validating and sanitizing review data"""

    # Allowed HTML tags for review content (very restrictive)
    ALLOWED_TAGS = []  # No HTML tags allowed
    ALLOWED_ATTRIBUTES = {}

    # Suspicious patterns that might indicate spam or fake reviews
    SPAM_PATTERNS = [
        r"(https?://[^\s]+)",  # URLs
        r"(\b\w+@\w+\.\w+\b)",  # Email addresses
        r"(\b\d{3}[-.]?\d{3}[-.]?\d{4}\b)",  # Phone numbers
        r"(\$\d+|\d+\$)",  # Price mentions
        r"(buy now|click here|visit|website)",  # Promotional language
    ]

    # Profanity filter (basic list - in production use a comprehensive library)
    PROFANITY_WORDS = {
        "damn",
        "hell",
        "crap",
        "stupid",
        "idiot",
        "moron",
        "dumb",
        "suck",
        "sucks",
        "terrible",
        "awful",
        "horrible",
        "worst",
    }

    @staticmethod
    def validate_and_sanitize(review_data: ReviewIngest) -> Tuple[Dict, List[str]]:
        """
        Validate and sanitize review data
        Returns: (sanitized_data, warnings)
        """
        warnings = []
        sanitized = {}

        # Basic field validation
        sanitized["platform"] = review_data.platform
        sanitized["external_id"] = ReviewValidationService._sanitize_string(
            review_data.external_id, max_length=255
        )
        sanitized["review_url"] = ReviewValidationService._validate_url(
            review_data.review_url
        )

        # Customer information
        sanitized["customer_name"] = ReviewValidationService._sanitize_name(
            review_data.customer_name
        )
        sanitized["customer_email"] = ReviewValidationService._
