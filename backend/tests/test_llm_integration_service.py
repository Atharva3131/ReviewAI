"""
Unit tests for LLM integration service
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from app.services.llm.response_generation_service import (
    LLMResponseGenerationService,
    GenerationRequest,
    GenerationResponse,
    ContentSanitizer,
    ResponseCache
)
from app.services.llm.base_provider import LLMRequest, LLMResponse, LLMMessage, LLMModel, LLMError, LLMProvider
from app.services.llm.prompt_templates import TemplateType


class TestContentSanitizer:
    """Test cases for ContentSanitizer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.sanitizer = ContentSanitizer()
    
    def test_sanitize_content_clean(self):
        """Test sanitization of clean content"""
        content = "This is a clean and professional message."
        
        result = self.sanitizer.sanitize_content(content)
        
        assert result['original_content'] == content
        assert result['sanitized_content'] == content
        assert result['was_sanitized'] == False
        assert result['issues_found'] == []
        assert result['sanitization_score'] == 1.0
    
    def test_sanitize_content_with_profanity(self):
        """Test sanitization of content with profanity"""
        content = "This service is damn stupid and the staff are idiots!"
        
        result = self.sanitizer.sanitize_content(content)
        
        assert result['was_sanitized'] == True
        assert 'profanity' in result['issues_found']
        assert '****' in result['sanitized_content']  # Profanity should be masked
        assert result['sanitization_score'] < 1.0
    
    def test_sanitize_content_with_sensitive_data(self):
        """Test sanitization of content with sensitive data"""
        content = "My credit card number is 1234-5678-9012-3456 and password is secret123"
        
        result = self.sanitizer.sanitize_content(content)
        
        assert result['was_sanitized'] == True
        assert len(result['issues_found']) >= 1
        assert '[REDACTED]' in result['sanitized_content']
        assert '1234-5678-9012-3456' not in result['sanitized_content']
    
    def test_sanitize_content_with_script_tags(self):
        """Test sanitization of content with script tags"""
        content = "Hello <script>alert('xss')</script> world"
        
        result = self.sanitizer.sanitize_content(content)
        
        assert result['was_sanitized'] == True
        assert '<script>' not in result['sanitized_content']
        assert '[REDACTED]' in result['sanitized_content']
    
    def test_sanitize_content_excessive_whitespace(self):
        """Test sanitization removes excessive whitespace"""
        content = "This   has    too     much      whitespace"
        
        result = self.sanitizer.sanitize_content(content)
        
        assert result['sanitized_content'] == "This has too much whitespace"
        # Whitespace cleanup doesn't count as sanitization issue
        assert result['was_sanitized'] == False
    
    def test_validate_content_valid(self):
        """Test validation of valid content"""
        content = "Thank you for your feedback. We appreciate your business and will address your concerns promptly."
        
        result = self.sanitizer.validate_content(content, 'review_response')
        
        assert result['is_valid'] == True
        assert result['quality_score'] > 0.5
        assert len(result['issues']) == 0
    
    def test_validate_content_too_short(self):
        """Test validation of content that's too short"""
        content = "OK"
        
        result = self.sanitizer.validate_content(content)
        
        assert result['is_valid'] == False
        assert 'content_too_short' in result['issues']
    
    def test_validate_content_too_long(self):
        """Test validation of content that's too long"""
        content = "A" * 2500  # Exceeds 2000 character limit
        
        result = self.sanitizer.validate_content(content)
        
        assert 'content_too_long' in result['issues']
        assert 'shortening' in str(result['recommendations']).lower()
    
    def test_validate_content_email_specific(self):
        """Test email-specific validation"""
        content = "This is an email without a subject line."
        
        result = self.sanitizer.validate_content(content, 'email')
        
        assert any('subject' in rec.lower() for rec in result['recommendations'])
    
    def test_validate_content_review_response_specific(self):
        """Test review response specific validation"""
        content = "We will fix this issue immediately."
        
        result = self.sanitizer.validate_content(content, 'review_response')
        
        assert any('thank' in rec.lower() for rec in result['recommendations'])
    
    def test_validate_content_quality_scoring(self):
        """Test content quality scoring"""
        # High quality content
        high_quality = "Thank you for your feedback. We sincerely apologize for the inconvenience. Please contact us so we can resolve this matter."
        result_high = self.sanitizer.validate_content(high_quality)
        
        # Low quality content
        low_quality = "ok we will fix it maybe"
        result_low = self.sanitizer.validate_content(low_quality)
        
        assert result_high['quality_score'] > result_low['quality_score']


class TestResponseCache:
    """Test cases for ResponseCache"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.cache = ResponseCache(max_size=10, ttl_hours=1)
    
    def create_mock_request(self, **kwargs):
        """Create a mock generation request"""
        defaults = {
            'template_type': TemplateType.REVIEW_RESPONSE,
            'variables': {'rating': 5, 'content': 'Great service!'},
            'model': LLMModel.MOCK_MODEL,
            'temperature': 0.7,
            'use_cache': True
        }
        defaults.update(kwargs)
        return GenerationRequest(**defaults)
    
    def create_mock_response(self, **kwargs):
        """Create a mock generation response"""
        defaults = {
            'content': 'Thank you for your positive feedback!',
            'template_id': 'template-123',
            'provider': LLMProvider.MOCK,
            'model': 'mock-model',
            'usage': {'prompt_tokens': 50, 'completion_tokens': 25, 'total_tokens': 75},
            'response_time': 1.5
        }
        defaults.update(kwargs)
        return GenerationResponse(**defaults)
    
    def test_cache_miss(self):
        """Test cache miss scenario"""
        request = self.create_mock_request()
        
        result = self.cache.get(request)
        
        assert result is None
    
    def test_cache_hit(self):
        """Test cache hit scenario"""
        request = self.create_mock_request()
        response = self.create_mock_response()
        
        # Cache the response
        self.cache.set(request, response)
        
        # Retrieve from cache
        cached_response = self.cache.get(request)
        
        assert cached_response is not None
        assert cached_response.content == response.content
        assert cached_response.cached == True
    
    def test_cache_expiry(self):
        """Test cache expiry"""
        # Create cache with very short TTL
        short_cache = ResponseCache(max_size=10, ttl_hours=0)  # Immediate expiry
        
        request = self.create_mock_request()
        response = self.create_mock_response()
        
        # Cache the response
        short_cache.set(request, response)
        
        # Should be expired immediately
        cached_response = short_cache.get(request)
        
        assert cached_response is None
    
    def test_cache_disabled(self):
        """Test caching when disabled"""
        request = self.create_mock_request(use_cache=False)
        response = self.create_mock_response()
        
        # Try to cache
        self.cache.set(request, response)
        
        # Should not be cached
        cached_response = self.cache.get(request)
        
        assert cached_response is None
    
    def test_cache_size_limit(self):
        """Test cache size limit enforcement"""
        # Fill cache beyond limit
        for i in range(15):  # More than max_size of 10
            request = self.create_mock_request(variables={'rating': i})
            response = self.create_mock_response(content=f'Response {i}')
            self.cache.set(request, response)
        
        # Cache should not exceed max size
        assert len(self.cache.cache) <= self.cache.max_size
    
    def test_cache_key_generation(self):
        """Test cache key generation for different requests"""
        request1 = self.create_mock_request(variables={'rating': 5})
        request2 = self.create_mock_request(variables={'rating': 4})
        request3 = self.create_mock_request(variables={'rating': 5})  # Same as request1
        
        key1 = self.cache._generate_cache_key(request1)
        key2 = self.cache._generate_cache_key(request2)
        key3 = self.cache._generate_cache_key(request3)
        
        assert key1 != key2  # Different variables should generate different keys
        assert key1 == key3  # Same variables should generate same key
    
    def test_cache_clear(self):
        """Test cache clearing"""
        request = self.create_mock_request()
        response = self.create_mock_response()
        
        self.cache.set(request, response)
        assert len(self.cache.cache) > 0
        
        self.cache.clear()
        assert len(self.cache.cache) == 0
    
    def test_cache_stats(self):
        """Test cache statistics"""
        stats = self.cache.get_stats()
        
        assert 'total_entries' in stats
        assert 'expired_entries' in stats
        assert 'active_entries' in stats
        assert 'max_size' in stats
        assert 'ttl_hours' in stats
        
        assert stats['max_size'] == 10
        assert stats['ttl_hours'] == 1


class TestLLMResponseGenerationService:
    """Test cases for LLMResponseGenerationService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = LLMResponseGenerationService()
        
        # Mock the template manager
        self.mock_template = MagicMock()
        self.mock_template.id = 'template-123'
        self.mock_template.name = 'Review Response Template'
        self.mock_template.version = '1.0'
        self.mock_template.status.value = 'active'
        
        # Mock LLM provider
        self.mock_provider = AsyncMock()
        self.mock_llm_response = LLMResponse(
            content="Thank you for your feedback!",
            provider=LLMProvider.MOCK,
            model="mock-model",
            usage={'prompt_tokens': 50, 'completion_tokens': 25, 'total_tokens': 75}
        )
        self.mock_provider.generate_response.return_value = self.mock_llm_response
    
    @pytest.mark.asyncio
    async def test_generate_review_response_success(self):
        """Test successful review response generation"""
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a response'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=self.mock_provider):
            
            result = await self.service.generate_review_response(
                rating=5,
                review_content="Great service!",
                customer_name="John Doe"
            )
            
            assert isinstance(result, GenerationResponse)
            assert result.content == "Thank you for your feedback!"
            assert result.template_id == 'template-123'
            assert result.provider == LLMProvider.MOCK
            assert result.validation_passed == True
            assert result.response_time > 0
    
    @pytest.mark.asyncio
    async def test_generate_recovery_email_success(self):
        """Test successful recovery email generation"""
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a recovery email'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=self.mock_provider):
            
            result = await self.service.generate_recovery_email(
                customer_name="Jane Smith",
                issue_type="billing",
                concerns="Incorrect charge",
                solution="Refund processed",
                contact_info="support@company.com"
            )
            
            assert isinstance(result, GenerationResponse)
            assert result.content == "Thank you for your feedback!"
            assert result.template_id == 'template-123'
    
    @pytest.mark.asyncio
    async def test_generate_apology_message_success(self):
        """Test successful apology message generation"""
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate an apology'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=self.mock_provider):
            
            result = await self.service.generate_apology_message(
                customer_name="Bob Johnson",
                issue_description="Service outage",
                impact="Unable to access account",
                our_fault="Server maintenance",
                corrective_actions="Restored service"
            )
            
            assert isinstance(result, GenerationResponse)
            assert result.content == "Thank you for your feedback!"
    
    @pytest.mark.asyncio
    async def test_generate_discount_offer_success(self):
        """Test successful discount offer generation"""
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a discount offer'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=self.mock_provider):
            
            result = await self.service.generate_discount_offer(
                customer_name="Alice Brown",
                discount_percentage=20,
                discount_code="SAVE20",
                expiry_date="2024-12-31"
            )
            
            assert isinstance(result, GenerationResponse)
            assert result.content == "Thank you for your feedback!"
    
    @pytest.mark.asyncio
    async def test_generate_response_with_caching(self):
        """Test response generation with caching"""
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a response'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=self.mock_provider):
            
            # First call should generate and cache
            result1 = await self.service.generate_review_response(
                rating=5,
                review_content="Great service!",
                use_cache=True
            )
            
            # Second call should return cached result
            result2 = await self.service.generate_review_response(
                rating=5,
                review_content="Great service!",
                use_cache=True
            )
            
            assert result1.content == result2.content
            assert result2.cached == True
            # Provider should only be called once
            assert self.mock_provider.generate_response.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_response_no_template(self):
        """Test response generation when no template is found"""
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[]):
            
            with pytest.raises(ValueError, match="No active templates found"):
                await self.service.generate_review_response(
                    rating=5,
                    review_content="Great service!"
                )
    
    @pytest.mark.asyncio
    async def test_generate_response_llm_error(self):
        """Test response generation when LLM provider fails"""
        error_provider = AsyncMock()
        error_provider.generate_response.side_effect = LLMError("API Error", LLMProvider.MOCK)
        
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a response'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=error_provider):
            
            with pytest.raises(LLMError):
                await self.service.generate_review_response(
                    rating=5,
                    review_content="Great service!"
                )
    
    @pytest.mark.asyncio
    async def test_generate_response_with_sanitization(self):
        """Test response generation with content sanitization"""
        # Mock LLM response with content that needs sanitization
        sanitized_response = LLMResponse(
            content="Thank you for your damn feedback, you idiot!",
            provider=LLMProvider.MOCK,
            model="mock-model",
            usage={'prompt_tokens': 50, 'completion_tokens': 25, 'total_tokens': 75}
        )
        self.mock_provider.generate_response.return_value = sanitized_response
        
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a response'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=self.mock_provider):
            
            result = await self.service.generate_review_response(
                rating=5,
                review_content="Great service!"
            )
            
            assert result.sanitized == True
            assert "****" in result.content  # Profanity should be masked
            assert "idiot" not in result.content
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Set very low rate limits
        self.service.update_rate_limits(requests_per_minute=2, requests_per_hour=5)
        
        # Should not raise error for first few requests
        self.service._check_rate_limits()
        self.service._check_rate_limits()
        
        # Should raise error when limit exceeded
        with pytest.raises(LLMError, match="Rate limit exceeded"):
            self.service._check_rate_limits()
    
    def test_get_service_stats(self):
        """Test service statistics"""
        stats = self.service.get_service_stats()
        
        assert 'cache_stats' in stats
        assert 'rate_limits' in stats
        assert 'recent_requests' in stats
        assert 'template_count' in stats
        assert 'active_templates' in stats
        
        assert isinstance(stats['cache_stats'], dict)
        assert isinstance(stats['rate_limits'], dict)
        assert isinstance(stats['recent_requests'], int)
    
    def test_clear_cache(self):
        """Test cache clearing"""
        # Add something to cache first
        request = GenerationRequest(
            template_type=TemplateType.REVIEW_RESPONSE,
            variables={'rating': 5}
        )
        response = GenerationResponse(
            content="Test",
            template_id="test",
            provider=LLMProvider.MOCK,
            model="test",
            usage={},
            response_time=1.0
        )
        self.service.cache.set(request, response)
        
        assert len(self.service.cache.cache) > 0
        
        self.service.clear_cache()
        
        assert len(self.service.cache.cache) == 0
    
    def test_update_rate_limits(self):
        """Test rate limit updates"""
        self.service.update_rate_limits(100, 2000)
        
        assert self.service.rate_limits['requests_per_minute'] == 100
        assert self.service.rate_limits['requests_per_hour'] == 2000
    
    def test_select_template(self):
        """Test template selection logic"""
        # Test with active template
        active_template = MagicMock()
        active_template.status.value = 'active'
        
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[active_template]):
            result = self.service._select_template(TemplateType.REVIEW_RESPONSE)
            assert result == active_template
        
        # Test with no active templates
        inactive_template = MagicMock()
        inactive_template.status.value = 'inactive'
        
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[inactive_template]):
            with pytest.raises(ValueError, match="No active templates found"):
                self.service._select_template(TemplateType.REVIEW_RESPONSE)
    
    def test_get_content_type(self):
        """Test content type mapping"""
        assert self.service._get_content_type(TemplateType.REVIEW_RESPONSE) == 'review_response'
        assert self.service._get_content_type(TemplateType.RECOVERY_EMAIL) == 'email'
        assert self.service._get_content_type(TemplateType.APOLOGY_MESSAGE) == 'apology'
        assert self.service._get_content_type(TemplateType.DISCOUNT_OFFER) == 'offer'
        assert self.service._get_content_type(TemplateType.GENERIC_RESPONSE) == 'general'
    
    @pytest.mark.asyncio
    async def test_generate_response_with_custom_provider(self):
        """Test response generation with custom provider"""
        custom_provider = AsyncMock()
        custom_provider.generate_response.return_value = self.mock_llm_response
        
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a response'
             }), \
             patch('app.services.llm.response_generation_service.get_llm_provider', return_value=custom_provider):
            
            result = await self.service.generate_review_response(
                rating=5,
                review_content="Great service!",
                provider=LLMProvider.OPENAI
            )
            
            assert isinstance(result, GenerationResponse)
            # Should use the custom provider
            custom_provider.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_with_metadata(self):
        """Test response generation with custom metadata"""
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a response'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=self.mock_provider):
            
            custom_metadata = {'user_id': '123', 'session_id': 'abc'}
            
            result = await self.service.generate_review_response(
                rating=5,
                review_content="Great service!",
                metadata=custom_metadata
            )
            
            assert 'user_id' in result.metadata
            assert 'session_id' in result.metadata
            assert result.metadata['user_id'] == '123'
            assert result.metadata['session_id'] == 'abc'
    
    @pytest.mark.asyncio
    async def test_generate_response_validation_failure(self):
        """Test response generation with validation failure"""
        # Mock LLM response with invalid content (too short)
        invalid_response = LLMResponse(
            content="OK",  # Too short
            provider=LLMProvider.MOCK,
            model="mock-model",
            usage={'prompt_tokens': 50, 'completion_tokens': 25, 'total_tokens': 75}
        )
        self.mock_provider.generate_response.return_value = invalid_response
        
        with patch.object(self.service.template_manager, 'get_templates_by_type', return_value=[self.mock_template]), \
             patch.object(self.service.template_manager, 'render_template', return_value={
                 'system_prompt': 'You are a helpful assistant',
                 'user_prompt': 'Generate a response'
             }), \
             patch('app.services.llm.response_generation_service.get_default_llm_provider', return_value=self.mock_provider):
            
            result = await self.service.generate_review_response(
                rating=5,
                review_content="Great service!"
            )
            
            assert result.validation_passed == False
            assert 'content_too_short' in result.metadata['validation_issues']


class TestGenerationRequestResponse:
    """Test cases for GenerationRequest and GenerationResponse dataclasses"""
    
    def test_generation_request_creation(self):
        """Test GenerationRequest creation"""
        request = GenerationRequest(
            template_type=TemplateType.REVIEW_RESPONSE,
            variables={'rating': 5, 'content': 'Great!'},
            model=LLMModel.MOCK_MODEL,
            temperature=0.8,
            max_tokens=100,
            use_cache=False,
            metadata={'test': 'value'}
        )
        
        assert request.template_type == TemplateType.REVIEW_RESPONSE
        assert request.variables['rating'] == 5
        assert request.model == LLMModel.MOCK_MODEL
        assert request.temperature == 0.8
        assert request.max_tokens == 100
        assert request.use_cache == False
        assert request.metadata['test'] == 'value'
    
    def test_generation_request_defaults(self):
        """Test GenerationRequest default values"""
        request = GenerationRequest(
            template_type=TemplateType.REVIEW_RESPONSE,
            variables={'rating': 5}
        )
        
        assert request.model is None
        assert request.temperature == 0.7
        assert request.max_tokens is None
        assert request.provider is None
        assert request.use_cache == True
        assert request.metadata is None
    
    def test_generation_response_creation(self):
        """Test GenerationResponse creation"""
        response = GenerationResponse(
            content="Test response",
            template_id="template-123",
            provider=LLMProvider.MOCK,
            model="mock-model",
            usage={'total_tokens': 100},
            response_time=1.5,
            cached=True,
            sanitized=True,
            validation_passed=False,
            metadata={'test': 'value'}
        )
        
        assert response.content == "Test response"
        assert response.template_id == "template-123"
        assert response.provider == LLMProvider.MOCK
        assert response.model == "mock-model"
        assert response.usage['total_tokens'] == 100
        assert response.response_time == 1.5
        assert response.cached == True
        assert response.sanitized == True
        assert response.validation_passed == False
        assert response.metadata['test'] == 'value'
        assert isinstance(response.created_at, datetime)
    
    def test_generation_response_defaults(self):
        """Test GenerationResponse default values"""
        response = GenerationResponse(
            content="Test response",
            template_id="template-123",
            provider=LLMProvider.MOCK,
            model="mock-model",
            usage={'total_tokens': 100},
            response_time=1.5
        )
        
        assert response.cached == False
        assert response.sanitized == False
        assert response.validation_passed == True
        assert response.metadata is None
        assert isinstance(response.created_at, datetime)


# Integration test for the global service instance
def test_get_llm_service():
    """Test getting the global LLM service instance"""
    from app.services.llm.response_generation_service import get_llm_service
    
    service1 = get_llm_service()
    service2 = get_llm_service()
    
    # Should return the same instance (singleton pattern)
    assert service1 is service2
    assert isinstance(service1, LLMResponseGenerationService)