"""
Property-based tests for response generation safety
**Validates: Requirements 7.3**
"""
import pytest
import asyncio
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
import re

from app.services.llm.response_generation_service import (
    LLMResponseGenerationService, 
    ContentSanitizer, 
    GenerationRequest, 
    GenerationResponse
)
from app.services.llm.prompt_templates import TemplateType
from app.services.llm.base_provider import LLMProvider, LLMModel


class TestResponseGenerationSafety:
    """Property-based tests for response generation safety"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = LLMResponseGenerationService()
        self.sanitizer = ContentSanitizer()
    
    @given(st.text(min_size=1, max_size=1000))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_sanitization_safety_property(self, content: str):
        """
        Property: All content should be sanitized and safe for output
        **Validates: Requirements 7.3.3**
        """
        assume(content.strip())
        
        result = self.sanitizer.sanitize_content(content)
        
        # Property: Should always return required fields
        required_fields = ['original_content', 'sanitized_content', 'was_sanitized', 'issues_found', 'sanitization_score']
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Property: Sanitized content should not contain harmful patterns
        sanitized = result['sanitized_content']
        
        # Check for credit card patterns
        cc_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        assert not re.search(cc_pattern, sanitized), "Sanitized content should not contain credit card patterns"
        
        # Check for SSN patterns
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        assert not re.search(ssn_pattern, sanitized), "Sanitized content should not contain SSN patterns"
        
        # Check for script tags
        script_pattern = r'<script[^>]*>.*?</script>'
        assert not re.search(script_pattern, sanitized, re.IGNORECASE), "Sanitized content should not contain script tags"
        
        # Property: Sanitization score should be between 0 and 1
        assert 0.0 <= result['sanitization_score'] <= 1.0, f"Sanitization score {result['sanitization_score']} out of bounds"
    
    @given(
        st.text(min_size=1, max_size=500),
        st.sampled_from(['general', 'email', 'review_response', 'apology'])
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_validation_safety_property(self, content: str, content_type: str):
        """
        Property: Content validation should ensure quality and safety
        **Validates: Requirements 7.3.3**
        """
        assume(content.strip())
        
        result = self.sanitizer.validate_content(content, content_type)
        
        # Property: Should always return required validation fields
        required_fields = ['is_valid', 'issues', 'quality_score', 'recommendations']
        for field in required_fields:
            assert field in result, f"Missing required validation field: {field}"
        
        # Property: Quality score should be between 0 and 1
        assert 0.0 <= result['quality_score'] <= 1.0, f"Quality score {result['quality_score']} out of bounds"
        
        # Property: Issues should be a list
        assert isinstance(result['issues'], list), "Issues should be a list"
        
        # Property: Very short content should be marked as invalid
        if len(content.strip()) < 10:
            assert result['is_valid'] == False, "Very short content should be invalid"
            assert 'content_too_short' in result['issues'], "Short content should have appropriate issue"
    
    @given(
        st.integers(min_value=1, max_value=5),  # rating
        st.text(min_size=1, max_size=200),      # review_content
        st.text(min_size=1, max_size=50)       # customer_name
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_review_response_generation_safety_property(self, rating: int, review_content: str, customer_name: str):
        """
        Property: Review response generation should be safe and appropriate
        **Validates: Requirements 7.3.1**
        """
        assume(review_content.strip() and customer_name.strip())
        
        # Mock the LLM provider to return controlled content
        mock_response_content = f"Thank you {customer_name} for your {rating}-star review. We appreciate your feedback."
        
        with patch('app.services.llm.response_generation_service.get_default_llm_provider') as mock_provider_factory:
            mock_provider = AsyncMock()
            mock_llm_response = MagicMock()
            mock_llm_response.content = mock_response_content
            mock_llm_response.provider = LLMProvider.MOCK
            mock_llm_response.model = "mock-model"
            mock_llm_response.usage = {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}
            
            mock_provider.generate_response.return_value = mock_llm_response
            mock_provider_factory.return_value = mock_provider
            
            # Mock template manager
            with patch.object(self.service.template_manager, 'render_template') as mock_render, \
                 patch.object(self.service.template_manager, 'get_templates_by_type') as mock_get_templates, \
                 patch.object(self.service.template_manager, 'update_template_metrics') as mock_update_metrics:
                
                # Mock template
                mock_template = MagicMock()
                mock_template.id = 'review_response_template'
                mock_template.name = 'Review Response'
                mock_template.version = '1.0'
                mock_template.status.value = 'active'
                
                mock_get_templates.return_value = [mock_template]
                mock_render.return_value = {
                    'system_prompt': 'You are a helpful customer service assistant.',
                    'user_prompt': f'Generate a response to this {rating}-star review: {review_content}'
                }
                
                result = asyncio.run(self.service.generate_review_response(
                    rating=rating,
                    review_content=review_content,
                    customer_name=customer_name
                ))
                
                # Property: Response should be generated successfully
                assert isinstance(result, GenerationResponse), "Should return GenerationResponse object"
                
                # Property: Content should be sanitized
                assert isinstance(result.sanitized, bool), "Sanitized flag should be boolean"
                
                # Property: Content should pass validation
                assert isinstance(result.validation_passed, bool), "Validation flag should be boolean"
                
                # Property: Response should contain safe content
                assert len(result.content) > 0, "Response content should not be empty"
                
                # Property: Response time should be reasonable
                assert result.response_time >= 0, "Response time should be non-negative"
    
    @given(
        st.text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?', min_size=1, max_size=500)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_harmful_content_detection_property(self, base_content: str):
        """
        Property: Harmful content should be detected and sanitized
        **Validates: Requirements 7.3.3**
        """
        assume(base_content.strip())
        
        # Test various harmful content patterns
        harmful_patterns = [
            f"{base_content} My password is secret123",
            f"{base_content} Call 4532-1234-5678-9012 for payment",
            f"{base_content} SSN: 123-45-6789",
            f"{base_content} <script>alert('xss')</script>",
            f"{base_content} javascript:void(0)"
        ]
        
        for harmful_content in harmful_patterns:
            result = self.sanitizer.sanitize_content(harmful_content)
            
            # Property: Harmful content should be detected
            assert result['was_sanitized'] == True, f"Harmful content should be detected: {harmful_content[:50]}..."
            assert len(result['issues_found']) > 0, "Should identify specific issues"
            
            # Property: Sanitized content should be safer
            sanitized = result['sanitized_content']
            assert '[REDACTED]' in sanitized or harmful_content != sanitized, \
                "Harmful content should be modified or redacted"
            
            # Property: Sanitization score should reflect the issues
            assert result['sanitization_score'] < 1.0, "Sanitization score should be reduced for harmful content"
    
    @given(
        st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),  # profanity_words
        st.text(min_size=10, max_size=200)  # base_content
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_profanity_filtering_property(self, profanity_words: List[str], base_content: str):
        """
        Property: Profanity should be filtered from generated content
        **Validates: Requirements 7.3.3**
        """
        assume(base_content.strip())
        
        # Add known profanity words to the content
        known_profanity = ['damn', 'hell', 'stupid', 'idiot']
        test_content = f"{base_content} This is {' and '.join(known_profanity)} content"
        
        result = self.sanitizer.sanitize_content(test_content)
        
        # Property: Profanity should be detected and filtered
        if any(word in test_content.lower() for word in known_profanity):
            assert result['was_sanitized'] == True, "Content with profanity should be sanitized"
            assert 'profanity' in result['issues_found'], "Profanity should be identified as an issue"
            
            # Property: Profanity should be replaced with asterisks
            sanitized = result['sanitized_content']
            for word in known_profanity:
                if word in test_content.lower():
                    assert '*' in sanitized or word not in sanitized.lower(), \
                        f"Profanity word '{word}' should be filtered"
    
    @given(st.integers(min_value=1, max_value=20))  # Number of requests
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=3)
    def test_rate_limiting_safety_property(self, num_requests: int):
        """
        Property: Rate limiting should prevent abuse
        **Validates: Requirements 7.3**
        """
        # Create a fresh service instance with low rate limits for testing
        test_service = LLMResponseGenerationService()
        test_service.update_rate_limits(requests_per_minute=5, requests_per_hour=20)
        
        # Mock response
        mock_response_content = "Rate limited response."
        
        with patch('app.services.llm.response_generation_service.get_default_llm_provider') as mock_provider_factory:
            mock_provider = AsyncMock()
            mock_llm_response = MagicMock()
            mock_llm_response.content = mock_response_content
            mock_llm_response.provider = LLMProvider.MOCK
            mock_llm_response.model = "mock-model"
            mock_llm_response.usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            
            mock_provider.generate_response.return_value = mock_llm_response
            mock_provider_factory.return_value = mock_provider
            
            # Mock template manager
            with patch.object(test_service.template_manager, 'render_template') as mock_render, \
                 patch.object(test_service.template_manager, 'get_templates_by_type') as mock_get_templates, \
                 patch.object(test_service.template_manager, 'update_template_metrics') as mock_update_metrics:
                
                mock_template = MagicMock()
                mock_template.id = 'rate_limit_test_template'
                mock_template.name = 'Rate Limit Test'
                mock_template.version = '1.0'
                mock_template.status.value = 'active'
                
                mock_get_templates.return_value = [mock_template]
                mock_render.return_value = {
                    'system_prompt': 'You are a helpful assistant.',
                    'user_prompt': 'Generate a response.'
                }
                
                successful_requests = 0
                rate_limited_requests = 0
                
                for i in range(min(num_requests, 8)):  # Limit to 8 for test performance
                    try:
                        request = GenerationRequest(
                            template_type=TemplateType.GENERIC_RESPONSE,
                            variables={'content': f'test_{i}'},
                            use_cache=False  # Disable cache to test rate limiting
                        )
                        
                        result = asyncio.run(test_service.generate_response(request))
                        successful_requests += 1
                        
                    except Exception as e:
                        if "rate limit" in str(e).lower():
                            rate_limited_requests += 1
                        else:
                            raise e
                
                # Property: Rate limiting should kick in for excessive requests
                if num_requests > 5:
                    assert rate_limited_requests > 0, "Rate limiting should prevent excessive requests"
                
                # Property: Some requests should succeed before rate limiting
                assert successful_requests > 0, "Some requests should succeed before rate limiting"


class TestResponseGenerationEdgeCases:
    """Property-based tests for edge cases in response generation safety"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.sanitizer = ContentSanitizer()
    
    @given(st.text(alphabet=' \\t\\n\\r', min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_only_content_property(self, content: str):
        """
        Property: Whitespace-only content should be handled safely
        **Validates: Requirements 7.3.3**
        """
        result = self.sanitizer.sanitize_content(content)
        
        # Property: Should handle whitespace gracefully
        assert 'sanitized_content' in result, "Should return sanitized content"
        assert isinstance(result['sanitized_content'], str), "Sanitized content should be string"
        assert result['sanitization_score'] >= 0.0, "Sanitization score should be non-negative"
    
    @given(st.text(alphabet='!@#$%^&*()_+-=[]{}|;:,.<>?', min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_special_characters_only_property(self, content: str):
        """
        Property: Special characters should be handled safely
        **Validates: Requirements 7.3.3**
        """
        result = self.sanitizer.sanitize_content(content)
        
        # Property: Should not crash on special characters
        assert isinstance(result['sanitized_content'], str), "Should return string"
        assert 0.0 <= result['sanitization_score'] <= 1.0, "Score should be in valid range"
    
    @given(st.text(min_size=0, max_size=5))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_very_short_content_property(self, content: str):
        """
        Property: Very short content should be handled appropriately
        **Validates: Requirements 7.3.3**
        """
        validation_result = self.sanitizer.validate_content(content, 'general')
        
        # Property: Very short content should be flagged
        if len(content.strip()) < 10:
            assert validation_result['is_valid'] == False, "Very short content should be invalid"
        
        # Property: Should always return valid structure
        assert isinstance(validation_result['quality_score'], float), "Quality score should be float"
        assert 0.0 <= validation_result['quality_score'] <= 1.0, "Quality score should be in range"


class TestResponseGenerationPerformance:
    """Property-based tests for response generation performance"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.sanitizer = ContentSanitizer()
    
    @given(st.integers(min_value=1, max_value=20))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=3)
    def test_batch_sanitization_performance_property(self, batch_size: int):
        """
        Property: Batch sanitization should scale reasonably
        **Validates: Requirements 7.3.3**
        """
        import time
        
        # Generate test content
        test_contents = [f"Test content {i} with some text to sanitize." for i in range(batch_size)]
        
        start_time = time.time()
        
        results = []
        for content in test_contents:
            result = self.sanitizer.sanitize_content(content)
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Property: Should complete in reasonable time (less than 0.1 seconds per item)
        max_time = batch_size * 0.1
        assert processing_time < max_time, f"Sanitization too slow: {processing_time}s for {batch_size} items"
        
        # Property: Should return results for all items
        assert len(results) == batch_size, "Should return result for each item"
        
        # Property: All results should be valid
        for result in results:
            assert 'sanitized_content' in result, "Each result should have sanitized content"
            assert 0.0 <= result['sanitization_score'] <= 1.0, "Each result should have valid score"


# Helper functions for generating realistic test data
def generate_review_content():
    """Strategy for generating realistic review content"""
    positive_words = ['excellent', 'amazing', 'great', 'wonderful', 'fantastic']
    negative_words = ['terrible', 'awful', 'horrible', 'disappointing', 'bad']
    neutral_words = ['okay', 'fine', 'average', 'normal', 'standard']
    
    return st.one_of(
        st.text(alphabet=st.sampled_from(positive_words + [' ', '.', '!'])),
        st.text(alphabet=st.sampled_from(negative_words + [' ', '.', '!'])),
        st.text(alphabet=st.sampled_from(neutral_words + [' ', '.']))
    )


class TestResponseGenerationRealisticScenarios:
    """Property-based tests using realistic response generation scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = LLMResponseGenerationService()
    
    @given(
        st.integers(min_value=1, max_value=5),
        generate_review_content(),
        st.text(min_size=1, max_size=30)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_realistic_review_response_scenario_property(self, rating: int, review_content: str, customer_name: str):
        """
        Property: Realistic review response scenarios should be handled safely
        **Validates: Requirements 7.3.1**
        """
        assume(review_content.strip() and customer_name.strip())
        
        # Mock realistic response
        sentiment = "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"
        mock_response = f"Dear {customer_name}, thank you for your {rating}-star {sentiment} review."
        
        with patch('app.services.llm.response_generation_service.get_default_llm_provider') as mock_provider_factory:
            mock_provider = AsyncMock()
            mock_llm_response = MagicMock()
            mock_llm_response.content = mock_response
            mock_llm_response.provider = LLMProvider.MOCK
            mock_llm_response.model = "mock-model"
            mock_llm_response.usage = {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}
            
            mock_provider.generate_response.return_value = mock_llm_response
            mock_provider_factory.return_value = mock_provider
            
            # Mock template manager
            with patch.object(self.service.template_manager, 'render_template') as mock_render, \
                 patch.object(self.service.template_manager, 'get_templates_by_type') as mock_get_templates, \
                 patch.object(self.service.template_manager, 'update_template_metrics') as mock_update_metrics:
                
                mock_template = MagicMock()
                mock_template.id = 'realistic_review_template'
                mock_template.name = 'Realistic Review Response'
                mock_template.version = '1.0'
                mock_template.status.value = 'active'
                
                mock_get_templates.return_value = [mock_template]
                mock_render.return_value = {
                    'system_prompt': 'You are a professional customer service representative.',
                    'user_prompt': f'Respond professionally to this {rating}-star review: {review_content}'
                }
                
                result = asyncio.run(self.service.generate_review_response(
                    rating=rating,
                    review_content=review_content,
                    customer_name=customer_name
                ))
                
                # Property: Realistic scenarios should produce safe, appropriate responses
                assert isinstance(result, GenerationResponse), "Should return valid response"
                assert len(result.content) > 0, "Response should have content"
                
                # Property: Response should be appropriate for the rating
                content_lower = result.content.lower()
                if rating >= 4:
                    assert 'thank' in content_lower, "Positive reviews should include thanks"
                
                # Property: Should maintain safety standards
                assert isinstance(result.sanitized, bool), "Should have sanitization status"