"""
LLM Integration Service

This package provides a comprehensive LLM integration system with support for
multiple providers, prompt template management, response caching, and content
sanitization.
"""

from .base_provider import (
    BaseLLMProvider,
    LLMProvider,
    LLMModel,
    LLMRequest,
    LLMResponse,
    LLMMessage,
    LLMError,
    RateLimitError,
    InvalidRequestError,
    AuthenticationError
)

from .provider_factory import (
    LLMProviderFactory,
    ProviderConfig,
    get_llm_factory,
    get_default_llm_provider,
    get_llm_provider
)

from .prompt_templates import (
    TemplateType,
    TemplateStatus,
    PromptTemplate,
    TemplateVariable,
    TemplateManager,
    TemplateRenderer,
    get_template_manager
)

from .response_generation_service import (
    GenerationRequest,
    GenerationResponse,
    LLMResponseGenerationService,
    get_llm_service
)

from .openai_provider import OpenAIProvider
from .mock_provider import MockLLMProvider
from .mistral_provider import MistralProvider

__all__ = [
    # Base classes and types
    'BaseLLMProvider',
    'LLMProvider',
    'LLMModel',
    'LLMRequest',
    'LLMResponse',
    'LLMMessage',
    'LLMError',
    'RateLimitError',
    'InvalidRequestError',
    'AuthenticationError',
    
    # Provider factory
    'LLMProviderFactory',
    'ProviderConfig',
    'get_llm_factory',
    'get_default_llm_provider',
    'get_llm_provider',
    
    # Template management
    'TemplateType',
    'TemplateStatus',
    'PromptTemplate',
    'TemplateVariable',
    'TemplateManager',
    'TemplateRenderer',
    'get_template_manager',
    
    # Response generation
    'GenerationRequest',
    'GenerationResponse',
    'LLMResponseGenerationService',
    'get_llm_service',
    
    # Specific providers
    'OpenAIProvider',
    'MockLLMProvider',
    'MistralProvider',
]

# Version info
__version__ = '1.0.0'
__author__ = 'Revive AI Team'
__description__ = 'LLM Integration Service for customer communication automation'
