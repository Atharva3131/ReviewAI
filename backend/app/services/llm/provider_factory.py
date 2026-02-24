"""
LLM Provider Factory

This module provides a factory for creating and managing LLM providers,
including provider switching and configuration management.
"""
from typing import Dict, Any, Optional, Type
import os
from enum import Enum

from .base_provider import BaseLLMProvider, LLMProvider
from .openai_provider import OpenAIProvider
from .mock_provider import MockLLMProvider
from .mistral_provider import MistralProvider


class ProviderConfig:
    """Configuration management for LLM providers"""
    
    def __init__(self):
        # Check if Mistral is configured (preferred over OpenAI)
        mistral_key = os.getenv("MISTRAL_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        self.providers_config = {
            LLMProvider.OPENAI: {
                "api_key": mistral_key or openai_key,  # Use Mistral key if available
                "organization": os.getenv("OPENAI_ORGANIZATION"),
                "timeout": int(os.getenv("OPENAI_TIMEOUT", "30")),
                "enabled": bool(mistral_key or openai_key),
                "use_mistral": bool(mistral_key)  # Flag to use Mistral provider
            },
            LLMProvider.GEMINI: {
                "api_key": os.getenv("GEMINI_API_KEY"),
                "timeout": int(os.getenv("GEMINI_TIMEOUT", "30")),
                "enabled": os.getenv("GEMINI_ENABLED", "false").lower() == "true"
            },
            LLMProvider.MOCK: {
                "simulate_errors": os.getenv("MOCK_SIMULATE_ERRORS", "false").lower() == "true",
                "response_delay": float(os.getenv("MOCK_RESPONSE_DELAY", "0.1")),
                "error_rate": float(os.getenv("MOCK_ERROR_RATE", "0.05")),
                "enabled": os.getenv("MOCK_ENABLED", "true").lower() == "true"
            }
        }
        
        # Default provider selection
        self.default_provider = LLMProvider(
            os.getenv("DEFAULT_LLM_PROVIDER", LLMProvider.MOCK.value)
        )
        
        # Fallback provider if default fails
        self.fallback_provider = LLMProvider(
            os.getenv("FALLBACK_LLM_PROVIDER", LLMProvider.MOCK.value)
        )
    
    def get_provider_config(self, provider: LLMProvider) -> Dict[str, Any]:
        """Get configuration for a specific provider"""
        return self.providers_config.get(provider, {})
    
    def is_provider_enabled(self, provider: LLMProvider) -> bool:
        """Check if a provider is enabled"""
        config = self.get_provider_config(provider)
        return config.get("enabled", False)
    
    def get_enabled_providers(self) -> list[LLMProvider]:
        """Get list of enabled providers"""
        return [
            provider for provider in LLMProvider
            if self.is_provider_enabled(provider)
        ]
    
    def update_provider_config(self, provider: LLMProvider, config: Dict[str, Any]):
        """Update configuration for a provider"""
        if provider in self.providers_config:
            self.providers_config[provider].update(config)
        else:
            self.providers_config[provider] = config


class LLMProviderFactory:
    """Factory for creating and managing LLM providers"""
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        self.config = config or ProviderConfig()
        self._provider_classes: Dict[LLMProvider, Type[BaseLLMProvider]] = {
            LLMProvider.OPENAI: OpenAIProvider,
            LLMProvider.MOCK: MockLLMProvider,
            # LLMProvider.GEMINI: GeminiProvider,  # Would be added when implemented
        }
        self._provider_instances: Dict[LLMProvider, BaseLLMProvider] = {}
        
        # Override OpenAI with Mistral if Mistral is configured
        openai_config = self.config.get_provider_config(LLMProvider.OPENAI)
        if openai_config.get("use_mistral"):
            self._provider_classes[LLMProvider.OPENAI] = MistralProvider
    
    def create_provider(self, provider_type: LLMProvider) -> BaseLLMProvider:
        """
        Create a new provider instance
        
        Args:
            provider_type: Type of provider to create
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider type is not supported or not enabled
        """
        if provider_type not in self._provider_classes:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        if not self.config.is_provider_enabled(provider_type):
            raise ValueError(f"Provider {provider_type} is not enabled")
        
        provider_class = self._provider_classes[provider_type]
        provider_config = self.config.get_provider_config(provider_type)
        
        return provider_class(provider_config)
    
    def get_provider(self, provider_type: Optional[LLMProvider] = None) -> BaseLLMProvider:
        """
        Get a provider instance (cached)
        
        Args:
            provider_type: Type of provider to get. If None, uses default provider
            
        Returns:
            Provider instance
        """
        if provider_type is None:
            provider_type = self.config.default_provider
        
        # Return cached instance if available
        if provider_type in self._provider_instances:
            return self._provider_instances[provider_type]
        
        # Create new instance and cache it
        provider = self.create_provider(provider_type)
        self._provider_instances[provider_type] = provider
        
        return provider
    
    def get_default_provider(self) -> BaseLLMProvider:
        """Get the default provider"""
        return self.get_provider(self.config.default_provider)
    
    def get_fallback_provider(self) -> BaseLLMProvider:
        """Get the fallback provider"""
        return self.get_provider(self.config.fallback_provider)
    
    def switch_default_provider(self, provider_type: LLMProvider):
        """
        Switch the default provider
        
        Args:
            provider_type: New default provider type
        """
        if not self.config.is_provider_enabled(provider_type):
            raise ValueError(f"Cannot switch to disabled provider: {provider_type}")
        
        self.config.default_provider = provider_type
    
    def get_available_providers(self) -> Dict[LLMProvider, Dict[str, Any]]:
        """
        Get information about all available providers
        
        Returns:
            Dictionary with provider info
        """
        providers_info = {}
        
        for provider_type in LLMProvider:
            if provider_type in self._provider_classes:
                config = self.config.get_provider_config(provider_type)
                providers_info[provider_type] = {
                    "enabled": self.config.is_provider_enabled(provider_type),
                    "is_default": provider_type == self.config.default_provider,
                    "is_fallback": provider_type == self.config.fallback_provider,
                    "config_keys": list(config.keys()) if config else []
                }
        
        return providers_info
    
    async def health_check_all_providers(self) -> Dict[LLMProvider, Dict[str, Any]]:
        """
        Perform health checks on all enabled providers
        
        Returns:
            Health status for each provider
        """
        health_results = {}
        
        for provider_type in self.config.get_enabled_providers():
            try:
                provider = self.get_provider(provider_type)
                health_results[provider_type] = await provider.health_check()
            except Exception as e:
                health_results[provider_type] = {
                    "status": "error",
                    "provider": provider_type.value,
                    "error": str(e),
                    "test_successful": False
                }
        
        return health_results
    
    def register_provider(
        self, 
        provider_type: LLMProvider, 
        provider_class: Type[BaseLLMProvider],
        config: Dict[str, Any]
    ):
        """
        Register a new provider type
        
        Args:
            provider_type: Provider type enum
            provider_class: Provider implementation class
            config: Provider configuration
        """
        self._provider_classes[provider_type] = provider_class
        self.config.update_provider_config(provider_type, config)
    
    def clear_cache(self):
        """Clear all cached provider instances"""
        self._provider_instances.clear()
    
    def get_provider_statistics(self) -> Dict[str, Any]:
        """Get factory statistics"""
        return {
            "total_provider_types": len(self._provider_classes),
            "cached_instances": len(self._provider_instances),
            "enabled_providers": len(self.config.get_enabled_providers()),
            "default_provider": self.config.default_provider.value,
            "fallback_provider": self.config.fallback_provider.value,
            "available_providers": list(self._provider_classes.keys())
        }


# Global factory instance
_factory_instance: Optional[LLMProviderFactory] = None


def get_llm_factory() -> LLMProviderFactory:
    """Get the global LLM provider factory instance"""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = LLMProviderFactory()
    return _factory_instance


def get_default_llm_provider() -> BaseLLMProvider:
    """Get the default LLM provider"""
    factory = get_llm_factory()
    return factory.get_default_provider()


def get_llm_provider(provider_type: LLMProvider) -> BaseLLMProvider:
    """Get a specific LLM provider"""
    factory = get_llm_factory()
    return factory.get_provider(provider_type)
