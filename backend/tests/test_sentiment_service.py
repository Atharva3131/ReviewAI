"""
Unit tests for sentiment analysis service
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.services.sentiment_service import SentimentService


class TestSentimentService:
    """Test cases for SentimentService"""
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_positive_review(self):
        """Test sentiment analysis for positive review"""
        content = "The food was excellent and the staff was very friendly. I highly recommend this place!"
        rating = 5
        
        result = await SentimentService.analyze_sentiment(content, rating)
        
        assert isinstance(result, dict)
        assert "sentiment_score" in result
        assert "confidence" in result
        assert "dominant_emotion" in result
        assert "word_contributions" in result
        assert "sentiment_label" in result
        
        # Should be positive sentiment
        assert result["sentiment_score"] > 0.7
        assert result["confidence"] > 0.5
        assert result["dominant_emotion"] in ["joy", "satisfaction"]
        assert result["sentiment_label"] in ["Positive", "Very Positive"]
        
        # Should have positive word contributions
        assert "excellent" in result["word_contributions"]
        assert "friendly" in result["word_contributions"]
        assert "recommend" in result["word_contributions"]
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_negative_review(self):
        """Test sentiment analysis for negative review"""
        content = "The service was terrible and the food was awful. I will never come back!"
        rating = 1
        
        result = await SentimentService.analyze_sentiment(content, rating)
        
        # Should be negative sentiment
        assert result["sentiment_score"] < 0.3
        assert result["confidence"] > 0.5
        assert result["dominant_emotion"] in ["anger", "disappointment"]
        assert result["sentiment_label"] in ["Negative", "Very Negative"]
        
        # Should have negative word contributions
        assert "terrible" in result["word_contributions"]
        assert "awful" in result["word_contributions"]
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_neutral_review(self):
        """Test sentiment analysis for neutral review"""
        content = "The food was okay and the service was adequate. Nothing special but acceptable."
        rating = 3
        
        result = await SentimentService.analyze_sentiment(content, rating)
        
        # Should be neutral sentiment
        assert 0.3 <= result["sentiment_score"] <= 0.7
        assert result["dominant_emotion"] == "neutral"
        assert result["sentiment_label"] == "Neutral"
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_empty_content(self):
        """Test sentiment analysis with empty content"""
        result = await SentimentService.analyze_sentiment("")
        
        assert result["sentiment_score"] == 0.5
        assert result["confidence"] == 0.0
        assert result["dominant_emotion"] == "neutral"
        assert result["word_contributions"] == {}
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_with_negation(self):
        """Test sentiment analysis with negation"""
        content = "The food was not good and the service was not excellent."
        
        result = await SentimentService.analyze_sentiment(content)
        
        # Negation should flip sentiment
        assert result["sentiment_score"] < 0.5
        assert "good" in result["word_contributions"]
        assert "excellent" in result["word_contributions"]
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_with_intensifiers(self):
        """Test sentiment analysis with intensifiers"""
        content = "The food was very good and extremely delicious."
        
        result = await SentimentService.analyze_sentiment(content)
        
        # Intensifiers should boost positive sentiment
        assert result["sentiment_score"] > 0.7
        assert "good" in result["word_contributions"]
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_with_diminishers(self):
        """Test sentiment analysis with diminishers"""
        content = "The food was somewhat good but only slightly better than average."
        
        result = await SentimentService.analyze_sentiment(content)
        
        # Diminishers should reduce sentiment intensity
        assert 0.4 <= result["sentiment_score"] <= 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_rating_correlation(self):
        """Test sentiment analysis with rating correlation"""
        content = "Good food"
        
        # Test with different ratings
        result_5_star = await SentimentService.analyze_sentiment(content, 5)
        result_1_star = await SentimentService.analyze_sentiment(content, 1)
        
        # Higher rating should result in higher sentiment
        assert result_5_star["sentiment_score"] > result_1_star["sentiment_score"]
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_contextual_patterns(self):
        """Test sentiment analysis with contextual patterns"""
        content = "The staff was rude and we had a long wait."
        
        result = await SentimentService.analyze_sentiment(content)
        
        # Contextual patterns should affect sentiment
        assert result["sentiment_score"] < 0.5
    
    def test_preprocess_content(self):
        """Test content preprocessing"""
        content = "I can't believe it's so AMAZING!!! Really, it's the best."
        
        processed = SentimentService._preprocess_content(content)
        
        assert processed.lower() == processed  # Should be lowercase
        assert "cannot" in processed  # Contractions expanded
        assert "!!!" not in processed  # Punctuation removed
        assert "  " not in processed  # Extra whitespace removed
    
    def test_check_negation_context(self):
        """Test negation context detection"""
        words = ["the", "food", "was", "not", "good"]
        
        # "good" should be in negation context
        assert SentimentService._check_negation_context(words, 4) == True
        
        # "food" should not be in negation context
        assert SentimentService._check_negation_context(words, 1) == False
    
    def test_check_intensity_context(self):
        """Test intensity context detection"""
        words = ["the", "food", "was", "very", "good"]
        
        # "good" should have intensifier context
        modifier = SentimentService._check_intensity_context(words, 4)
        assert modifier > 1.0
        
        # "food" should have no intensity context
        modifier = SentimentService._check_intensity_context(words, 1)
        assert modifier == 1.0
    
    def test_get_word_sentiment(self):
        """Test word sentiment scoring"""
        # Test positive word
        score = SentimentService._get_word_sentiment("excellent")
        assert score is not None
        assert score > 0.5
        
        # Test negative word
        score = SentimentService._get_word_sentiment("terrible")
        assert score is not None
        assert score < 0.5
        
        # Test unknown word
        score = SentimentService._get_word_sentiment("unknown")
        assert score is None
    
    def test_apply_intensity(self):
        """Test intensity application"""
        # Test intensifier on positive sentiment
        result = SentimentService._apply_intensity(0.7, 1.3)
        assert result > 0.7
        
        # Test diminisher on positive sentiment
        result = SentimentService._apply_intensity(0.7, 0.8)
        assert result < 0.7
        
        # Test no modification
        result = SentimentService._apply_intensity(0.7, 1.0)
        assert result == 0.7
    
    def test_rating_to_sentiment(self):
        """Test rating to sentiment conversion"""
        # Test all ratings
        assert SentimentService._rating_to_sentiment(1) == 0.1
        assert SentimentService._rating_to_sentiment(2) == 0.3
        assert SentimentService._rating_to_sentiment(3) == 0.5
        assert SentimentService._rating_to_sentiment(4) == 0.7
        assert SentimentService._rating_to_sentiment(5) == 0.9
    
    def test_calculate_confidence(self):
        """Test confidence calculation"""
        # High word coverage, long content, consistent rating
        confidence = SentimentService._calculate_confidence(
            scored_words=5, total_words=10, rating=5, sentiment=0.8
        )
        assert confidence > 0.7
        
        # Low word coverage, short content, no rating
        confidence = SentimentService._calculate_confidence(
            scored_words=1, total_words=3, rating=None, sentiment=0.5
        )
        assert confidence < 0.5
    
    def test_determine_emotion(self):
        """Test emotion determination"""
        assert SentimentService._determine_emotion(0.9, {}) == "joy"
        assert SentimentService._determine_emotion(0.7, {}) == "satisfaction"
        assert SentimentService._determine_emotion(0.5, {}) == "neutral"
        assert SentimentService._determine_emotion(0.3, {}) == "disappointment"
        assert SentimentService._determine_emotion(0.1, {}) == "anger"
    
    def test_get_sentiment_label(self):
        """Test sentiment label generation"""
        assert SentimentService._get_sentiment_label(0.9) == "Very Positive"
        assert SentimentService._get_sentiment_label(0.7) == "Positive"
        assert SentimentService._get_sentiment_label(0.5) == "Neutral"
        assert SentimentService._get_sentiment_label(0.3) == "Negative"
        assert SentimentService._get_sentiment_label(0.1) == "Very Negative"
    
    @pytest.mark.asyncio
    async def test_validate_sentiment_score(self):
        """Test sentiment score validation"""
        # Valid scores
        assert await SentimentService.validate_sentiment_score(0.0) == True
        assert await SentimentService.validate_sentiment_score(0.5) == True
        assert await SentimentService.validate_sentiment_score(1.0) == True
        
        # Invalid scores
        assert await SentimentService.validate_sentiment_score(-0.1) == False
        assert await SentimentService.validate_sentiment_score(1.1) == False
        assert await SentimentService.validate_sentiment_score("0.5") == False
    
    @pytest.mark.asyncio
    async def test_check_rating_sentiment_correlation(self):
        """Test rating-sentiment correlation checking"""
        # Consistent correlation
        result = await SentimentService.check_rating_sentiment_correlation(5, 0.8)
        assert result["is_consistent"] == True
        assert result["correlation_strength"] > 0.7
        
        # Inconsistent correlation
        result = await SentimentService.check_rating_sentiment_correlation(1, 0.8)
        assert result["is_consistent"] == False
        assert result["correlation_strength"] < 0.5
        
        # Check result structure
        assert "expected_sentiment" in result
        assert "actual_sentiment" in result
        assert "difference" in result
        assert "tolerance" in result
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_edge_cases(self):
        """Test sentiment analysis edge cases"""
        # Only punctuation
        result = await SentimentService.analyze_sentiment("!@#$%^&*()")
        assert result["sentiment_score"] == 0.5
        
        # Only numbers
        result = await SentimentService.analyze_sentiment("123 456 789")
        assert result["sentiment_score"] == 0.5
        
        # Mixed case with special characters
        result = await SentimentService.analyze_sentiment("EXCELLENT!!! food... TERRIBLE service???")
        assert isinstance(result["sentiment_score"], float)
        assert 0.0 <= result["sentiment_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_long_content(self):
        """Test sentiment analysis with long content"""
        content = " ".join(["good"] * 100)  # 100 positive words
        
        result = await SentimentService.analyze_sentiment(content)
        
        assert result["sentiment_score"] > 0.6
        assert result["confidence"] > 0.5
        assert len(result["word_contributions"]) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_mixed_sentiment(self):
        """Test sentiment analysis with mixed positive and negative words"""
        content = "The food was excellent but the service was terrible. Good atmosphere though."
        
        result = await SentimentService.analyze_sentiment(content)
        
        # Should be somewhere in the middle
        assert 0.3 <= result["sentiment_score"] <= 0.7
        assert "excellent" in result["word_contributions"]
        assert "terrible" in result["word_contributions"]
        assert "good" in result["word_contributions"]
    
    def test_analyze_patterns(self):
        """Test contextual pattern analysis"""
        # Test service patterns
        content = "staff was rude and we had a long wait"
        adjustment = SentimentService._analyze_patterns(content)
        assert adjustment < 0
        
        content = "staff was friendly and quick service"
        adjustment = SentimentService._analyze_patterns(content)
        assert adjustment > 0
        
        # Test recommendation patterns
        content = "would not recommend this place"
        adjustment = SentimentService._analyze_patterns(content)
        assert adjustment < 0
        
        content = "would recommend this place"
        adjustment = SentimentService._analyze_patterns(content)
        assert adjustment > 0
    
    @pytest.mark.asyncio
    async def test_sentiment_consistency(self):
        """Test that sentiment analysis is consistent for same input"""
        content = "The food was good and the service was excellent."
        
        result1 = await SentimentService.analyze_sentiment(content)
        result2 = await SentimentService.analyze_sentiment(content)
        
        # Results should be identical (deterministic)
        assert result1["sentiment_score"] == result2["sentiment_score"]
        assert result1["confidence"] == result2["confidence"]
        assert result1["dominant_emotion"] == result2["dominant_emotion"]
        assert result1["word_contributions"] == result2["word_contributions"]
    
    @pytest.mark.asyncio
    async def test_sentiment_score_bounds(self):
        """Test that sentiment scores are always within valid bounds"""
        test_cases = [
            "absolutely terrible horrible awful disgusting worst",
            "extremely excellent amazing outstanding perfect wonderful",
            "very very very good",
            "not not not bad",
            "",
            "neutral okay fine"
        ]
        
        for content in test_cases:
            result = await SentimentService.analyze_sentiment(content)
            assert 0.0 <= result["sentiment_score"] <= 1.0
            assert 0.0 <= result["confidence"] <= 1.0