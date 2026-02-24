"""
Property-based tests for sentiment analysis consistency
**Validates: Requirements 4.2**
"""
import pytest
import asyncio
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from typing import Dict, Any, List

from app.services.sentiment_service import SentimentService


class TestSentimentAnalysisConsistency:
    """Property-based tests for sentiment analysis consistency"""
    
    @given(st.text(min_size=1, max_size=1000))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sentiment_score_bounds_property(self, text: str):
        """
        Property: Sentiment scores must always be between 0.0 and 1.0
        **Validates: Requirements 4.2.2**
        """
        assume(text.strip())  # Assume non-empty text after stripping
        
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Score must be within bounds
        assert 0.0 <= result["sentiment_score"] <= 1.0, f"Sentiment score {result['sentiment_score']} out of bounds for text: {text[:50]}..."
        assert 0.0 <= result["confidence"] <= 1.0, f"Confidence {result['confidence']} out of bounds for text: {text[:50]}..."
    
    @given(st.text(min_size=1, max_size=500))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sentiment_determinism_property(self, text: str):
        """
        Property: Same input should always produce identical output (determinism)
        **Validates: Requirements 4.2.1**
        """
        assume(text.strip())
        
        result1 = asyncio.run(SentimentService.analyze_sentiment(text))
        result2 = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Results should be identical
        assert result1["sentiment_score"] == result2["sentiment_score"], f"Non-deterministic sentiment for: {text[:50]}..."
        assert result1["confidence"] == result2["confidence"], f"Non-deterministic confidence for: {text[:50]}..."
        assert result1["dominant_emotion"] == result2["dominant_emotion"], f"Non-deterministic emotion for: {text[:50]}..."
        assert result1["sentiment_label"] == result2["sentiment_label"], f"Non-deterministic label for: {text[:50]}..."
    
    @given(
        st.text(min_size=1, max_size=200),
        st.integers(min_value=1, max_value=5)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rating_sentiment_correlation_property(self, text: str, rating: int):
        """
        Property: Rating and sentiment should be reasonably correlated
        **Validates: Requirements 4.2.3**
        """
        assume(text.strip())
        
        result_with_rating = asyncio.run(SentimentService.analyze_sentiment(text, rating))
        correlation_check = asyncio.run(
            SentimentService.check_rating_sentiment_correlation(
                rating, result_with_rating["sentiment_score"]
            )
        )
        
        # Property: Correlation should be reasonable for most cases
        # Allow some flexibility for edge cases where text strongly contradicts rating
        if rating == 5:  # 5-star rating
            assert result_with_rating["sentiment_score"] >= 0.3, f"5-star rating should not produce very negative sentiment for: {text[:50]}..."
        elif rating == 1:  # 1-star rating
            assert result_with_rating["sentiment_score"] <= 0.7, f"1-star rating should not produce very positive sentiment for: {text[:50]}..."
        
        # Property: Correlation strength should be meaningful
        assert isinstance(correlation_check["correlation_strength"], float)
        assert 0.0 <= correlation_check["correlation_strength"] <= 1.0
    
    @given(st.text(min_size=1, max_size=300))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sentiment_label_consistency_property(self, text: str):
        """
        Property: Sentiment label should be consistent with numerical score
        **Validates: Requirements 4.2**
        """
        assume(text.strip())
        
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        score = result["sentiment_score"]
        label = result["sentiment_label"]
        
        # Property: Label should match score range
        if score >= 0.8:
            assert label == "Very Positive", f"Score {score} should be 'Very Positive', got '{label}'"
        elif score >= 0.6:
            assert label == "Positive", f"Score {score} should be 'Positive', got '{label}'"
        elif score >= 0.4:
            assert label == "Neutral", f"Score {score} should be 'Neutral', got '{label}'"
        elif score >= 0.2:
            assert label == "Negative", f"Score {score} should be 'Negative', got '{label}'"
        else:
            assert label == "Very Negative", f"Score {score} should be 'Very Negative', got '{label}'"
    
    @given(st.text(alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd', 'Po', 'Zs']), min_size=1, max_size=300))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_unicode_handling_property(self, text: str):
        """
        Property: Service should handle various Unicode characters gracefully
        **Validates: Requirements 4.2**
        """
        assume(text.strip())
        
        # Should not raise an exception
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Should return valid result structure
        assert "sentiment_score" in result
        assert "confidence" in result
        assert "dominant_emotion" in result
        assert "sentiment_label" in result
        assert isinstance(result["sentiment_score"], float)
        assert isinstance(result["confidence"], float)
        assert isinstance(result["dominant_emotion"], str)
        assert isinstance(result["sentiment_label"], str)
    
    @given(st.integers(min_value=1, max_value=2000))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_text_length_handling_property(self, length: int):
        """
        Property: Service should handle texts of various lengths consistently
        **Validates: Requirements 4.2**
        """
        # Generate text of specific length
        text = "This is a test sentence with neutral sentiment. " * (length // 47 + 1)
        text = text[:length]
        assume(text.strip())
        
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Should handle any reasonable text length
        assert 0.0 <= result["sentiment_score"] <= 1.0
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["sentiment_label"] in ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
    
    @given(st.text(min_size=1, max_size=200))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_case_insensitive_consistency_property(self, text: str):
        """
        Property: Sentiment analysis should be case-insensitive
        **Validates: Requirements 4.2**
        """
        assume(text.strip())
        
        upper_result = asyncio.run(SentimentService.analyze_sentiment(text.upper()))
        lower_result = asyncio.run(SentimentService.analyze_sentiment(text.lower()))
        original_result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Case should not affect sentiment significantly
        # Allow small differences due to preprocessing variations
        tolerance = 0.05
        
        assert abs(upper_result["sentiment_score"] - lower_result["sentiment_score"]) <= tolerance, \
            f"Case sensitivity issue: upper={upper_result['sentiment_score']}, lower={lower_result['sentiment_score']}"
        
        assert abs(original_result["sentiment_score"] - lower_result["sentiment_score"]) <= tolerance, \
            f"Case sensitivity issue: original={original_result['sentiment_score']}, lower={lower_result['sentiment_score']}"
    
    @given(st.sampled_from([
        "excellent service", "terrible experience", "okay food", 
        "amazing quality", "horrible staff", "decent price",
        "outstanding performance", "awful taste", "good value"
    ]))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_known_sentiment_words_property(self, text: str):
        """
        Property: Known sentiment words should produce expected sentiment ranges
        **Validates: Requirements 4.2**
        """
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        positive_words = ["excellent", "amazing", "outstanding"]
        negative_words = ["terrible", "horrible", "awful"]
        neutral_words = ["okay", "decent", "good"]
        
        # Property: Strong positive words should produce positive sentiment
        if any(word in text.lower() for word in positive_words):
            assert result["sentiment_score"] >= 0.6, f"Positive text '{text}' should have positive sentiment, got {result['sentiment_score']}"
        
        # Property: Strong negative words should produce negative sentiment
        elif any(word in text.lower() for word in negative_words):
            assert result["sentiment_score"] <= 0.4, f"Negative text '{text}' should have negative sentiment, got {result['sentiment_score']}"
        
        # Property: Neutral words should produce moderate sentiment
        elif any(word in text.lower() for word in neutral_words):
            assert 0.3 <= result["sentiment_score"] <= 0.7, f"Neutral text '{text}' should have moderate sentiment, got {result['sentiment_score']}"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confidence_calculation_property(self, text: str):
        """
        Property: Confidence calculation should be reasonable and bounded
        **Validates: Requirements 4.2**
        """
        assume(text.strip())
        
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        confidence = result["confidence"]
        
        # Property: Confidence should be bounded
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} out of bounds"
        
        # Property: Longer texts with sentiment words should have higher confidence
        word_count = len(text.split())
        if word_count >= 20:
            # Longer texts should generally have reasonable confidence
            assert confidence >= 0.1, f"Long text should have some confidence, got {confidence}"
        
        # Property: Confidence should be a float
        assert isinstance(confidence, float), f"Confidence should be float, got {type(confidence)}"


class TestSentimentAnalysisStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for sentiment analysis
    **Validates: Requirements 4.2**
    """
    
    def __init__(self):
        super().__init__()
        self.analyzed_texts = []
        self.results_cache = {}
        self.sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}
    
    @rule(text=st.text(min_size=1, max_size=200))
    def analyze_text(self, text: str):
        """Rule: Analyze a piece of text"""
        assume(text.strip())
        
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        self.analyzed_texts.append(text)
        self.results_cache[text] = result
        
        # Track sentiment distribution
        score = result["sentiment_score"]
        if score >= 0.6:
            self.sentiment_distribution["positive"] += 1
        elif score <= 0.4:
            self.sentiment_distribution["negative"] += 1
        else:
            self.sentiment_distribution["neutral"] += 1
    
    @rule(rating=st.integers(min_value=1, max_value=5))
    def analyze_with_rating(self, rating: int):
        """Rule: Analyze previous text with a rating"""
        if not self.analyzed_texts:
            return
        
        text = self.analyzed_texts[-1]  # Use most recent text
        result = asyncio.run(SentimentService.analyze_sentiment(text, rating))
        
        # Store result with rating key
        key = f"{text}_rating_{rating}"
        self.results_cache[key] = result
    
    @rule()
    def reanalyze_previous_text(self):
        """Rule: Re-analyze a previously analyzed text"""
        if not self.analyzed_texts:
            return
        
        text = self.analyzed_texts[-1]
        if text in self.results_cache:
            new_result = asyncio.run(SentimentService.analyze_sentiment(text))
            old_result = self.results_cache[text]
            
            # Results should be identical (determinism)
            assert new_result["sentiment_score"] == old_result["sentiment_score"]
            assert new_result["confidence"] == old_result["confidence"]
    
    @invariant()
    def results_are_valid(self):
        """Invariant: All cached results should be valid"""
        for text, result in self.results_cache.items():
            if not text.endswith(")"):  # Skip rating-based keys for this check
                assert 0.0 <= result["sentiment_score"] <= 1.0
                assert 0.0 <= result["confidence"] <= 1.0
                assert result["sentiment_label"] in ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
    
    @invariant()
    def sentiment_distribution_reasonable(self):
        """Invariant: Sentiment distribution should be reasonable"""
        total = sum(self.sentiment_distribution.values())
        if total > 10:
            # Should not have all results in one category (unless by chance)
            max_category = max(self.sentiment_distribution.values())
            assert max_category < total * 0.9, "Sentiment distribution too skewed"
    
    @invariant()
    def cache_consistency(self):
        """Invariant: Cache should be consistent with analyzed texts"""
        # All analyzed texts should have results in cache
        for text in self.analyzed_texts:
            assert text in self.results_cache or any(text in key for key in self.results_cache.keys())


class TestSentimentAnalysisEdgeCases:
    """Property-based tests for edge cases in sentiment analysis"""
    
    @given(st.text(alphabet=' \\t\\n\\r', min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_only_property(self, text: str):
        """
        Property: Whitespace-only text should be handled gracefully
        **Validates: Requirements 4.2**
        """
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Should return neutral sentiment for whitespace
        assert result["sentiment_label"] == "Neutral"
        assert 0.4 <= result["sentiment_score"] <= 0.6
        assert result["confidence"] >= 0.0
    
    @given(st.text(alphabet='!@#$%^&*()_+-=[]{}|;:,.<>?', min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_special_characters_only_property(self, text: str):
        """
        Property: Special characters only should be handled gracefully
        **Validates: Requirements 4.2**
        """
        # Should not raise an exception
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Should return valid result
        assert isinstance(result["sentiment_score"], float)
        assert isinstance(result["confidence"], float)
        assert result["sentiment_label"] in ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
    
    @given(st.text(alphabet='0123456789', min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_numbers_only_property(self, text: str):
        """
        Property: Numbers-only text should be handled gracefully
        **Validates: Requirements 4.2**
        """
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Numbers should typically be neutral
        assert result["sentiment_label"] == "Neutral"
        assert 0.4 <= result["sentiment_score"] <= 0.6
    
    @given(st.lists(st.text(min_size=0, max_size=10), min_size=0, max_size=5))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_empty_strings_property(self, texts: List[str]):
        """
        Property: Empty strings should be handled gracefully
        **Validates: Requirements 4.2**
        """
        # Include empty string
        texts.append("")
        
        for text in texts:
            # Should not raise an exception
            result = asyncio.run(SentimentService.analyze_sentiment(text))
            
            # Property: Should return valid result
            assert isinstance(result["sentiment_score"], float)
            assert 0.0 <= result["sentiment_score"] <= 1.0
            assert isinstance(result["confidence"], float)
            assert 0.0 <= result["confidence"] <= 1.0


# Test runner for stateful testing
TestSentimentStateMachine = TestSentimentAnalysisStateMachine.TestCase


# Helper strategies for generating realistic test data
def generate_positive_review_text():
    """Strategy for generating positive review text"""
    positive_words = ['excellent', 'amazing', 'great', 'wonderful', 'fantastic', 'love', 'perfect']
    return st.text(
        alphabet=st.sampled_from(positive_words + [' ', '.', '!', 'service', 'food', 'staff']),
        min_size=10,
        max_size=100
    )


def generate_negative_review_text():
    """Strategy for generating negative review text"""
    negative_words = ['terrible', 'awful', 'horrible', 'hate', 'worst', 'disappointing', 'bad']
    return st.text(
        alphabet=st.sampled_from(negative_words + [' ', '.', '!', 'service', 'food', 'staff']),
        min_size=10,
        max_size=100
    )


def generate_neutral_review_text():
    """Strategy for generating neutral review text"""
    neutral_words = ['okay', 'fine', 'average', 'normal', 'standard', 'typical', 'decent']
    return st.text(
        alphabet=st.sampled_from(neutral_words + [' ', '.', 'service', 'food', 'staff']),
        min_size=10,
        max_size=100
    )


class TestSentimentAnalysisRealisticData:
    """Property-based tests using realistic review data"""
    
    @given(generate_positive_review_text())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_positive_review_consistency(self, text: str):
        """
        Property: Positive review text should produce positive sentiment
        **Validates: Requirements 4.2**
        """
        assume(text.strip())
        
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Should lean positive
        assert result["sentiment_score"] >= 0.5, f"Positive text should have positive sentiment: {text[:50]}..."
    
    @given(generate_negative_review_text())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_negative_review_consistency(self, text: str):
        """
        Property: Negative review text should produce negative sentiment
        **Validates: Requirements 4.2**
        """
        assume(text.strip())
        
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Should lean negative
        assert result["sentiment_score"] <= 0.5, f"Negative text should have negative sentiment: {text[:50]}..."
    
    @given(generate_neutral_review_text())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_neutral_review_consistency(self, text: str):
        """
        Property: Neutral review text should produce moderate sentiment
        **Validates: Requirements 4.2**
        """
        assume(text.strip())
        
        result = asyncio.run(SentimentService.analyze_sentiment(text))
        
        # Property: Should be in neutral range
        assert 0.3 <= result["sentiment_score"] <= 0.7, f"Neutral text should have moderate sentiment: {text[:50]}..."