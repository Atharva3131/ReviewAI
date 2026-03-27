"""
Abstract LLM Provider Interface

This module defines the base interface for LLM providers, allowing for
easy switching between different LLM services (OpenAI, Gemini, etc.)
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    GEMINI = "gemini"
    MOCK = "mock"  # For testing


class LLMModel(str, Enum):
    """Supported LLM models"""

    # OpenAI models
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

    # Gemini models
    GEMINI_PRO = "gemini-pro"
    GEMINI_PRO_VISION = "gemini-pro-vision"

    # Mock model
    MOCK_MODEL = "mock-model"


class LLMMessage(BaseModel):
    """Standard message format for LLM interactions"""

    role: str  # "system", "user", "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None


class LLMRequest(BaseModel):
    """Standard request format for LLM providers"""

    messages: List[LLMMessage]
    model: LLMModel
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMResponse(BaseModel):
    """Standard response format from LLM providers"""

    content: str
    model: str
    provider: LLMProvider
    usage: Dict[str, int]  # tokens used
    finish_reason: str
    response_time: float  # seconds
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class LLMError(Exception):
    """Base exception for LLM-related errors"""

    def __init__(
        self, message: str, provider: LLMProvider, error_code: Optional[str] = None
    ):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(message)


class RateLimitError(LLMError):
    """Exception for rate limit errors"""

    def __init__(self, provider: LLMProvider, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {provider}", provider, "rate_limit")


class InvalidRequestError(LLMError):
    """Exception for invalid request errors"""

    pass


class AuthenticationError(LLMError):
    """Exception for authentication errors"""

    pass


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM provider with configuration

        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.provider_name = self._get_provider_name()
        self._validate_config()

    @abstractmethod
    def _get_provider_name(self) -> LLMProvider:
        """Return the provider name"""
        pass

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate the provider configuration"""
        pass

    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response using the LLM

        Args:
            request: The LLM request containing messages and parameters

        Returns:
            LLMResponse containing the generated content and metadata

        Raises:
            LLMError: For various LLM-related errors
        """
        pass

    @abstractmethod
    async def generate_streaming_response(self, request: LLMRequest):
        """
        Generate a streaming response using the LLM

        Args:
            request: The LLM request containing messages and parameters

        Yields:
            Partial response chunks

        Raises:
            LLMError: For various LLM-related errors
        """
        pass

    @abstractmethod
    def get_supported_models(self) -> List[LLMModel]:
        """Return list of supported models for this provider"""
        pass

    @abstractmethod
    def estimate_tokens(self, text: str, model: LLMModel) -> int:
        """
        Estimate token count for given text and model

        Args:
            text: Text to estimate tokens for
            model: Model to use for estimation

        Returns:
            Estimated token count
        """
        pass

    @abstractmethod
    def get_max_tokens(self, model: LLMModel) -> int:
        """
        Get maximum token limit for a model

        Args:
            model: Model to get limit for

        Returns:
            Maximum token count
        """
        pass

    def validate_request(self, request: LLMRequest) -> None:
        """
        Validate an LLM request

        Args:
            request: Request to validate

        Raises:
            InvalidRequestError: If request is invalid
        """
        # Check if model is supported
        if request.model not in self.get_supported_models():
            raise InvalidRequestError(
                f"Model {request.model} not supported by {self.provider_name}",
                self.provider_name,
            )

        # Check if messages are valid
        if not request.messages:
            raise InvalidRequestError(
                "Request must contain at least one message", self.provider_name
            )

        # Validate message roles
        valid_roles = {"system", "user", "assistant"}
        for message in request.messages:
            if message.role not in valid_roles:
                raise InvalidRequestError(
                    f"Invalid message role: {message.role}", self.provider_name
                )

        # Check token limits
        total_tokens = sum(
            self.estimate_tokens(msg.content, request.model) for msg in request.messages
        )

        max_tokens = self.get_max_tokens(request.model)
        if total_tokens > max_tokens * 0.8:  # Leave room for response
            raise InvalidRequestError(
                f"Request too long: {total_tokens} tokens (max: {max_tokens})",
                self.provider_name,
            )

    def format_messages(self, messages: List[LLMMessage]) -> Any:
        """
        Format messages for the specific provider
        Override in subclasses if needed

        Args:
            messages: List of LLMMessage objects

        Returns:
            Provider-specific message format
        """
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def create_response(
        self,
        content: str,
        model: str,
        usage: Dict[str, int],
        finish_reason: str,
        response_time: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Create a standardized LLMResponse

        Args:
            content: Generated content
            model: Model used
            usage: Token usage information
            finish_reason: Why generation stopped
            response_time: Time taken for response
            metadata: Additional metadata

        Returns:
            LLMResponse object
        """
        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            usage=usage,
            finish_reason=finish_reason,
            response_time=response_time,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the provider

        Returns:
            Health status information
        """
        try:
            # Simple test request
            test_request = LLMRequest(
                messages=[LLMMessage(role="user", content="Hello")],
                model=self.get_supported_models()[0],
                max_tokens=10,
            )

            start_time = datetime.utcnow()
            response = await self.generate_response(test_request)
            end_time = datetime.utcnow()

            return {
                "status": "healthy",
                "provider": self.provider_name.value,
                "response_time": (end_time - start_time).total_seconds(),
                "test_successful": True,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider_name.value,
                "error": str(e),
                "test_successful": False,
            }
