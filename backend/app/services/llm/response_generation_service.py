"""
LLM Response Generation Service

This service provides high-level interfaces for generating responses using LLMs,
including content sanitization, validation, and caching.
"""

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from .base_provider import LLMError, LLMMessage, LLMModel, LLMRequest, LLMResponse
from .prompt_templates import TemplateManager, TemplateType, get_template_manager
from .provider_factory import LLMProvider, get_default_llm_provider, get_llm_provider


@dataclass
class GenerationRequest:
    """High-level request for response generation"""

    template_type: TemplateType
    variables: Dict[str, Any]
    model: Optional[LLMModel] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    provider: Optional[LLMProvider] = None
    use_cache: bool = True
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GenerationResponse:
    """High-level response from generation service"""

    content: str
    template_id: str
    provider: LLMProvider
    model: str
    usage: Dict[str, int]
    response_time: float
    cached: bool = False
    sanitized: bool = False
    validation_passed: bool = True
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class ContentSanitizer:
    """Content sanitization and validation"""

    def __init__(self):
        # Patterns for potentially harmful content
        self.harmful_patterns = [
            r"\b(?:password|credit card|ssn|social security)\b",
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card pattern
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
            r"<script[^>]*>.*?</script>",  # Script tags
            r"javascript:",  # JavaScript URLs
            r"on\w+\s*=",  # Event handlers
        ]

        # Compile patterns for efficiency
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.harmful_patterns
        ]

        # Profanity filter (basic implementation)
        self.profanity_words = {
            "damn",
            "hell",
            "crap",
            "stupid",
            "idiot",
            "moron",
            # In production, use a comprehensive profanity filter library
        }

    def sanitize_content(self, content: str) -> Dict[str, Any]:
        """
        Sanitize content and return sanitization results

        Args:
            content: Content to sanitize

        Returns:
            Dictionary with sanitized content and flags
        """
        original_content = content
        sanitized_content = content
        issues_found = []

        # Remove potentially harmful patterns
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(sanitized_content):
                issues_found.append(f"harmful_pattern_{i}")
                sanitized_content = pattern.sub("[REDACTED]", sanitized_content)

        # Basic profanity filtering
        words = sanitized_content.split()
        for i, word in enumerate(words):
            if word.lower().strip(".,!?;:") in self.profanity_words:
                words[i] = "*" * len(word)
                issues_found.append("profanity")

        sanitized_content = " ".join(words)

        # Remove excessive whitespace
        sanitized_content = re.sub(r"\s+", " ", sanitized_content).strip()

        return {
            "original_content": original_content,
            "sanitized_content": sanitized_content,
            "was_sanitized": len(issues_found) > 0,
            "issues_found": issues_found,
            "sanitization_score": 1.0 - (len(issues_found) / 10.0),  # Simple scoring
        }

    def validate_content(
        self, content: str, content_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Validate content quality and appropriateness

        Args:
            content: Content to validate
            content_type: Type of content (email, review_response, etc.)

        Returns:
            Validation results
        """
        validation_results = {
            "is_valid": True,
            "issues": [],
            "quality_score": 1.0,
            "recommendations": [],
        }

        # Length validation
        if len(content.strip()) < 10:
            validation_results["issues"].append("content_too_short")
            validation_results["is_valid"] = False

        if len(content) > 2000:  # Configurable limit
            validation_results["issues"].append("content_too_long")
            validation_results["recommendations"].append(
                "Consider shortening the message"
            )

        # Content type specific validation
        if content_type == "email":
            if "subject:" not in content.lower():
                validation_results["recommendations"].append(
                    "Consider adding a subject line"
                )

        elif content_type == "review_response":
            if "thank" not in content.lower():
                validation_results["recommendations"].append(
                    "Consider thanking the customer"
                )

        # Calculate quality score
        quality_factors = []

        # Sentence structure
        sentences = content.split(".")
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(
            len(sentences), 1
        )
        if 5 <= avg_sentence_length <= 25:
            quality_factors.append(1.0)
        else:
            quality_factors.append(0.7)

        # Politeness indicators
        polite_words = ["please", "thank", "appreciate", "sorry", "apologize"]
        politeness_score = sum(
            1 for word in polite_words if word in content.lower()
        ) / len(polite_words)
        quality_factors.append(min(politeness_score * 2, 1.0))

        # Professional tone
        professional_indicators = ["sincerely", "regards", "best", "respectfully"]
        professional_score = sum(
            1 for word in professional_indicators if word in content.lower()
        ) / len(professional_indicators)
        quality_factors.append(min(professional_score * 2, 1.0))

        validation_results["quality_score"] = sum(quality_factors) / len(
            quality_factors
        )

        return validation_results


class ResponseCache:
    """Simple in-memory cache for LLM responses"""

    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)

    def _generate_cache_key(self, request: GenerationRequest) -> str:
        """Generate a cache key for a request"""
        # Create a hash of the request parameters
        cache_data = {
            "template_type": request.template_type.value,
            "variables": request.variables,
            "model": request.model.value if request.model else None,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def get(self, request: GenerationRequest) -> Optional[GenerationResponse]:
        """Get cached response if available and not expired"""
        if not request.use_cache:
            return None

        cache_key = self._generate_cache_key(request)

        if cache_key in self.cache:
            cached_data = self.cache[cache_key]

            # Check if expired
            if datetime.now(timezone.utc) - cached_data["timestamp"] > self.ttl:
                del self.cache[cache_key]
                return None

            # Return cached response
            response_data = cached_data["response"]
            response_data["cached"] = True
            return GenerationResponse(**response_data)

        return None

    def set(self, request: GenerationRequest, response: GenerationResponse):
        """Cache a response"""
        if not request.use_cache:
            return

        # Clean cache if too large
        if len(self.cache) >= self.max_size:
            # Remove oldest entries
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1]["timestamp"])
            for key, _ in sorted_items[: self.max_size // 4]:  # Remove 25%
                del self.cache[key]

        cache_key = self._generate_cache_key(request)

        # Store response data (excluding cached flag)
        response_data = {
            "content": response.content,
            "template_id": response.template_id,
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
            "response_time": response.response_time,
            "sanitized": response.sanitized,
            "validation_passed": response.validation_passed,
            "metadata": response.metadata,
            "created_at": response.created_at,
        }

        self.cache[cache_key] = {
            "response": response_data,
            "timestamp": datetime.now(timezone.utc),
        }

    def clear(self):
        """Clear all cached responses"""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now(timezone.utc)
        expired_count = sum(
            1 for data in self.cache.values() if now - data["timestamp"] > self.ttl
        )

        return {
            "total_entries": len(self.cache),
            "expired_entries": expired_count,
            "active_entries": len(self.cache) - expired_count,
            "max_size": self.max_size,
            "ttl_hours": self.ttl.total_seconds() / 3600,
        }


class LLMResponseGenerationService:
    """Main service for generating LLM responses"""

    def __init__(self):
        self.template_manager = get_template_manager()
        self.sanitizer = ContentSanitizer()
        self.cache = ResponseCache()

        # Rate limiting (simple implementation)
        self.rate_limits = {"requests_per_minute": 60, "requests_per_hour": 1000}
        self.request_history = []

    async def generate_review_response(
        self,
        rating: int,
        review_content: str,
        customer_name: str = "Valued Customer",
        business_type: str = "business",
        **kwargs,
    ) -> GenerationResponse:
        """Generate a response to a customer review"""
        request = GenerationRequest(
            template_type=TemplateType.REVIEW_RESPONSE,
            variables={
                "rating": rating,
                "review_content": review_content,
                "customer_name": customer_name,
                "business_type": business_type,
            },
            **kwargs,
        )

        return await self.generate_response(request)

    async def generate_recovery_email(
        self,
        customer_name: str,
        issue_type: str,
        concerns: str,
        solution: str,
        contact_info: str,
        customer_value: str = "valued",
        **kwargs,
    ) -> GenerationResponse:
        """Generate a customer recovery email"""
        request = GenerationRequest(
            template_type=TemplateType.RECOVERY_EMAIL,
            variables={
                "customer_name": customer_name,
                "issue_type": issue_type,
                "concerns": concerns,
                "solution": solution,
                "contact_info": contact_info,
                "customer_value": customer_value,
            },
            **kwargs,
        )

        return await self.generate_response(request)

    async def generate_apology_message(
        self,
        customer_name: str,
        issue_description: str,
        impact: str,
        our_fault: str,
        corrective_actions: str,
        prevention: str = "improved processes",
        **kwargs,
    ) -> GenerationResponse:
        """Generate a sincere apology message"""
        request = GenerationRequest(
            template_type=TemplateType.APOLOGY_MESSAGE,
            variables={
                "customer_name": customer_name,
                "issue_description": issue_description,
                "impact": impact,
                "our_fault": our_fault,
                "corrective_actions": corrective_actions,
                "prevention": prevention,
            },
            **kwargs,
        )

        return await self.generate_response(request)

    async def generate_discount_offer(
        self,
        customer_name: str,
        discount_percentage: int,
        discount_code: str,
        expiry_date: str,
        min_purchase: str = "No minimum",
        offer_reason: str = "loyalty",
        focus_area: str = "any purchase",
        **kwargs,
    ) -> GenerationResponse:
        """Generate a discount offer message"""
        request = GenerationRequest(
            template_type=TemplateType.DISCOUNT_OFFER,
            variables={
                "customer_name": customer_name,
                "discount_percentage": discount_percentage,
                "discount_code": discount_code,
                "expiry_date": expiry_date,
                "min_purchase": min_purchase,
                "offer_reason": offer_reason,
                "focus_area": focus_area,
            },
            **kwargs,
        )

        return await self.generate_response(request)

    async def generate_response(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate a response using LLM

        Args:
            request: Generation request

        Returns:
            Generated response

        Raises:
            LLMError: If generation fails
        """
        start_time = time.time()

        # Check rate limits
        self._check_rate_limits()

        # Check cache first
        cached_response = self.cache.get(request)
        if cached_response:
            return cached_response

        try:
            # Get appropriate template
            template = self._select_template(request.template_type)

            # Render template
            rendered = self.template_manager.render_template(
                template.id, request.variables
            )

            # Create LLM request
            llm_request = LLMRequest(
                messages=[
                    LLMMessage(role="system", content=rendered["system_prompt"]),
                    LLMMessage(role="user", content=rendered["user_prompt"]),
                ],
                model=request.model or LLMModel.MOCK_MODEL,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            # Get LLM provider
            if request.provider:
                provider = get_llm_provider(request.provider)
            else:
                provider = get_default_llm_provider()

            # Generate response
            llm_response = await provider.generate_response(llm_request)

            # Sanitize content
            sanitization_result = self.sanitizer.sanitize_content(llm_response.content)

            # Validate content
            content_type = self._get_content_type(request.template_type)
            validation_result = self.sanitizer.validate_content(
                sanitization_result["sanitized_content"], content_type
            )

            # Create response
            response = GenerationResponse(
                content=sanitization_result["sanitized_content"],
                template_id=template.id,
                provider=llm_response.provider,
                model=llm_response.model,
                usage=llm_response.usage,
                response_time=time.time() - start_time,
                sanitized=sanitization_result["was_sanitized"],
                validation_passed=validation_result["is_valid"],
                metadata={
                    "template_name": template.name,
                    "template_version": template.version,
                    "sanitization_score": sanitization_result["sanitization_score"],
                    "quality_score": validation_result["quality_score"],
                    "validation_issues": validation_result["issues"],
                    "recommendations": validation_result["recommendations"],
                    **(request.metadata or {}),
                },
            )

            # Update template metrics
            self.template_manager.update_template_metrics(
                template.id,
                success=validation_result["is_valid"],
                response_time=response.response_time,
                customer_satisfaction=None,  # Would be updated later based on feedback
            )

            # Cache response
            self.cache.set(request, response)

            return response

        except Exception as e:
            if isinstance(e, LLMError):
                raise
            else:
                raise LLMError(
                    f"Response generation failed: {str(e)}", LLMProvider.MOCK
                )

    def _select_template(self, template_type: TemplateType):
        """Select the best template for the given type"""
        # Get active templates of the specified type
        templates = self.template_manager.get_templates_by_type(template_type)
        active_templates = [
            t for t in templates if t.status.value in ["active", "testing"]
        ]

        if not active_templates:
            raise ValueError(f"No active templates found for type: {template_type}")

        # For now, select the first active template
        # In production, this could implement A/B testing logic
        return active_templates[0]

    def _get_content_type(self, template_type: TemplateType) -> str:
        """Map template type to content type for validation"""
        mapping = {
            TemplateType.REVIEW_RESPONSE: "review_response",
            TemplateType.RECOVERY_EMAIL: "email",
            TemplateType.APOLOGY_MESSAGE: "apology",
            TemplateType.DISCOUNT_OFFER: "offer",
            TemplateType.FOLLOW_UP: "follow_up",
            TemplateType.SURVEY_REQUEST: "survey",
            TemplateType.ESCALATION_NOTICE: "escalation",
            TemplateType.GENERIC_RESPONSE: "general",
        }
        return mapping.get(template_type, "general")

    def _check_rate_limits(self):
        """Check if rate limits are exceeded"""
        now = datetime.now(timezone.utc)

        # Clean old requests
        self.request_history = [
            timestamp
            for timestamp in self.request_history
            if now - timestamp < timedelta(hours=1)
        ]

        # Check limits
        recent_requests = [
            timestamp
            for timestamp in self.request_history
            if now - timestamp < timedelta(minutes=1)
        ]

        if len(recent_requests) >= self.rate_limits["requests_per_minute"]:
            raise LLMError(
                "Rate limit exceeded: too many requests per minute", LLMProvider.MOCK
            )

        if len(self.request_history) >= self.rate_limits["requests_per_hour"]:
            raise LLMError(
                "Rate limit exceeded: too many requests per hour", LLMProvider.MOCK
            )

        # Add current request
        self.request_history.append(now)

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "cache_stats": self.cache.get_stats(),
            "rate_limits": self.rate_limits,
            "recent_requests": len(self.request_history),
            "template_count": len(self.template_manager.templates),
            "active_templates": len(self.template_manager.get_active_templates()),
        }

    def clear_cache(self):
        """Clear response cache"""
        self.cache.clear()

    def update_rate_limits(self, requests_per_minute: int, requests_per_hour: int):
        """Update rate limits"""
        self.rate_limits = {
            "requests_per_minute": requests_per_minute,
            "requests_per_hour": requests_per_hour,
        }


# Global service instance
_service_instance: Optional[LLMResponseGenerationService] = None


def get_llm_service() -> LLMResponseGenerationService:
    """Get the global LLM response generation service"""
    global _service_instance
    if _service_instance is None:
        _service_instance = LLMResponseGenerationService()
    return _service_instance
