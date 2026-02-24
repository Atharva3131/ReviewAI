"""
Mock LLM Provider Implementation

This module implements a mock provider for testing and development purposes.
"""
import asyncio
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import random

from .base_provider import (
    BaseLLMProvider, LLMProvider, LLMModel, LLMRequest, LLMResponse, 
    LLMError, RateLimitError
)


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing and development"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Mock provider
        
        Args:
            config: Configuration dictionary containing:
                - simulate_errors: Whether to simulate random errors
                - response_delay: Delay in seconds for responses
                - error_rate: Probability of errors (0.0 to 1.0)
        """
        super().__init__(config)
        self.simulate_errors = config.get("simulate_errors", False)
        self.response_delay = config.get("response_delay", 0.1)
        self.error_rate = config.get("error_rate", 0.05)
        
        # Mock response templates
        self.response_templates = {
            "review_response": [
                "Thank you for your feedback! We appreciate you taking the time to share your experience with us.",
                "We're grateful for your review and will use your feedback to continue improving our service.",
                "Your opinion matters to us. Thank you for choosing our service and for your valuable feedback.",
                "We appreciate your honest review and are committed to providing excellent service to all our customers."
            ],
            "recovery_email": [
                "We sincerely apologize for any inconvenience. We'd like to make this right and ensure your satisfaction.",
                "Your experience is important to us. Please allow us to address your concerns and improve your experience.",
                "We value your business and want to resolve any issues you may have experienced with our service.",
                "Thank you for bringing this to our attention. We're committed to making improvements based on your feedback."
            ],
            "apology": [
                "We sincerely apologize for the inconvenience and take full responsibility for this situation.",
                "We're sorry this happened and are taking steps to prevent similar issues in the future.",
                "Please accept our apologies. We're committed to making this right and earning back your trust.",
                "We apologize for falling short of your expectations and appreciate your patience as we work to improve."
            ],
            "generic": [
                "Thank you for contacting us. We're here to help and appreciate your business.",
                "We value your inquiry and are committed to providing you with excellent service.",
                "Thank you for reaching out. Our team is dedicated to ensuring your satisfaction.",
                "We appreciate your message and look forward to assisting you with your needs."
            ]
        }
    
    def _get_provider_name(self) -> LLMProvider:
        """Return the provider name"""
        return LLMProvider.MOCK
    
    def _validate_config(self) -> None:
        """Validate the provider configuration"""
        # Mock provider doesn't require special validation
        pass
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a mock response"""
        self.validate_request(request)
        
        # Simulate processing delay
        await asyncio.sleep(self.response_delay)
        
        # Simulate random errors if enabled
        if self.simulate_errors and random.random() < self.error_rate:
            if random.random() < 0.3:
                raise RateLimitError(LLMProvider.MOCK, retry_after=30)
            else:
                raise LLMError("Mock error for testing", LLMProvider.MOCK)
        
        start_time = time.time()
        
        # Generate mock response based on content
        content = self._generate_mock_content(request)
        
        # Calculate mock usage
        input_tokens = sum(self.estimate_tokens(msg.content, request.model) for msg in request.messages)
        output_tokens = self.estimate_tokens(content, request.model)
        
        response_time = time.time() - start_time
        
        return self.create_response(
            content=content,
            model=request.model.value,
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            finish_reason="stop",
            response_time=response_time,
            metadata={
                "mock_provider": True,
                "template_used": self._get_template_type(request)
            }
        )
    
    async def generate_streaming_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming mock response"""
        self.validate_request(request)
        
        # Generate content first
        content = self._generate_mock_content(request)
        
        # Stream the response word by word
        words = content.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.02)  # Fast streaming for mock
            if i == 0:
                yield word
            else:
                yield f" {word}"
    
    def get_supported_models(self) -> List[LLMModel]:
        """Return list of supported mock models"""
        return [LLMModel.MOCK_MODEL]
    
    def estimate_tokens(self, text: str, model: LLMModel) -> int:
        """Estimate token count (simple approximation)"""
        return len(text.split()) + len(text) // 10  # Words + some for punctuation
    
    def get_max_tokens(self, model: LLMModel) -> int:
        """Get maximum token limit for mock model"""
        return 4096  # Standard limit for mock
    
    def _generate_mock_content(self, request: LLMRequest) -> str:
        """Generate mock content based on request"""
        template_type = self._get_template_type(request)
        templates = self.response_templates.get(template_type, self.response_templates["generic"])
        
        # Select a random template
        base_response = random.choice(templates)
        
        # Add some variation based on request parameters
        if request.temperature > 0.8:
            # High temperature - add more creative elements
            variations = [
                " We're excited to continue serving you!",
                " Your satisfaction is our top priority.",
                " We look forward to exceeding your expectations.",
                " Thank you for being a valued customer."
            ]
            base_response += random.choice(variations)
        
        return base_response
    
    def _get_template_type(self, request: LLMRequest) -> str:
        """Determine the appropriate template type based on request content"""
        if not request.messages:
            return "generic"
        
        last_message = request.messages[-1].content.lower()
        
        if "review" in last_message and "respond" in last_message:
            return "review_response"
        elif "recovery" in last_message or ("email" in last_message and "customer" in last_message):
            return "recovery_email"
        elif "apolog" in last_message or "sorry" in last_message:
            return "apology"
        else:
            return "generic"
    
    def set_error_simulation(self, enabled: bool, error_rate: float = 0.05):
        """
        Configure error simulation for testing
        
        Args:
            enabled: Whether to enable error simulation
            error_rate: Probability of errors (0.0 to 1.0)
        """
        self.simulate_errors = enabled
        self.error_rate = max(0.0, min(1.0, error_rate))
    
    def set_response_delay(self, delay: float):
        """
        Set the response delay for simulation
        
        Args:
            delay: Delay in seconds
        """
        self.response_delay = max(0.0, delay)
    
    async def simulate_rate_limit(self):
        """Simulate a rate limit error"""
        raise RateLimitError(LLMProvider.MOCK, retry_after=60)
    
    def get_mock_statistics(self) -> Dict[str, Any]:
        """Get mock provider statistics"""
        return {
            "provider": "mock",
            "simulate_errors": self.simulate_errors,
            "error_rate": self.error_rate,
            "response_delay": self.response_delay,
            "supported_models": [model.value for model in self.get_supported_models()],
            "template_types": list(self.response_templates.keys())
        }
