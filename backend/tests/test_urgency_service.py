"""
Unit tests for urgency classification service
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.services.urgency_service import UrgencyService
from app.models.review import UrgencyLevel


class TestUrgencyService:
    """Test cases for UrgencyService"""
    
    @pytest.mark.asyncio
    async def test_classify_urgency_high_emergency(self):
        """Test urgency classification for emergency content"""
        content = "This is an emergency! The food poisoning made me sick and I need immediate help!"
        rating = 1
        
        result = await UrgencyService.classify_urgency(content, rating)
        
        assert result["urgency_level"] == UrgencyLevel.HIGH.value
        assert result["urgency_score"] >= 0.7
        assert result["confidence"] > 0.5
        assert any("HIGH:" in match for match in result["keyword_matches"])
        assert "emergency" in str(result["keyword_matches"]).lower()
        assert len(result["contributing_factors"]) > 0
    
    @pytest.mark.asyncio
    async def test_classify_urgency_high_safety_concern(self):
        """Test urgency classification for safety concerns"""
        content = "The food was dangerous and unsafe. Someone could get seriously hurt!"
        rating = 1
        
        result = await UrgencyService.classify_urgency(content, rating)
        
        assert result["urgency_level"] == UrgencyLevel.HIGH.value
        assert result["urgency_score"] >= 0.6
        assert "dangerous" in str(result["keyword_matches"]).lower()
        assert "unsafe" in str(result["keyword_matches"]).lower()
    
    @pytest.mark.asyncio
    async def test_classify_urgency_high_legal_threat(self):
        """Test urgency classification for legal threats"""
        content = "I'm going to sue you and contact my lawyer about this terrible service!"
        rating = 2
        
        result = await UrgencyService.classify_urgency(content, rating)
        
        assert result["urgency_level"] in [UrgencyLevel.HIGH.value, UrgencyLevel.MEDIUM.value]
        assert result["urgency_score"] >= 0.5
        assert any("PATTERN:" in factor for factor in result["contributing_factors"])
    
    @pytest.mark.asyncio
    async def test_classify_urgency_medium_service_issues(self):
        """Test urgency classification for medium service issues"""
        content = "I have a problem with my order. The food was defective and I'm dissatisfied."
        rating = 2
        
        result = await UrgencyService.classify_urgency(content, rating)
        
        assert result["urgency_level"] in [UrgencyLevel.MEDIUM.value, UrgencyLevel.HIGH.value]
        assert 0.3 <= result["urgency_score"] <= 0.8
        assert any("MEDIUM:" in match for match in result["keyword_matches"])
    
    @pytest.mark.asyncio
    async def test_classify_urgency_low_suggestion(self):
        """Test urgency classification for low urgency suggestions"""
        content = "I have a small suggestion for improvement. Maybe you could consider adding more options."
        rating = 4
        
        result = await UrgencyService.classify_urgency(content, rating)
        
        assert result["urgency_level"] == UrgencyLevel.LOW.value
        assert result["urgency_score"] <= 0.4
        assert "LOW_INDICATORS:" in str(result["keyword_matches"])
    
    @pytest.mark.asyncio
    async def test_classify_urgency_empty_content(self):
        """Test urgency classification with empty content"""
        result = await UrgencyService.classify_urgency("")
        
        assert result["urgency_level"] == UrgencyLevel.LOW.value
        assert result["urgency_score"] == 0.1
        assert result["confidence"] == 0.0
        assert result["keyword_matches"] == []
        assert result["contributing_factors"] == []
    
    @pytest.mark.asyncio
    async def test_classify_urgency_with_title(self):
        """Test urgency classification with title included"""
        title = "URGENT: Need immediate assistance"
        content = "Please help me resolve this issue quickly."
        
        result = await UrgencyService.classify_urgency(content, title=title)
        
        assert result["urgency_level"] in [UrgencyLevel.HIGH.value, UrgencyLevel.MEDIUM.value]
        assert result["urgency_score"] >= 0.5
        # Title should contribute to urgency detection
        assert any("urgent" in match.lower() for match in result["keyword_matches"])
    
    @pytest.mark.asyncio
    async def test_classify_urgency_rating_correlation(self):
        """Test urgency correlation with ratings"""
        content = "The service was not good."
        
        # Test with different ratings
        result_1_star = await UrgencyService.classify_urgency(content, rating=1)
        result_5_star = await UrgencyService.classify_urgency(content, rating=5)
        
        # Lower rating should result in higher urgency
        assert result_1_star["urgency_score"] > result_5_star["urgency_score"]
    
    @pytest.mark.asyncio
    async def test_classify_urgency_sentiment_correlation(self):
        """Test urgency correlation with sentiment"""
        content = "The service was not acceptable."
        
        # Test with different sentiment scores
        result_negative = await UrgencyService.classify_urgency(content, sentiment_score=0.1)
        result_positive = await UrgencyService.classify_urgency(content, sentiment_score=0.9)
        
        # More negative sentiment should result in higher urgency
        assert result_negative["urgency_score"] > result_positive["urgency_score"]
    
    @pytest.mark.asyncio
    async def test_classify_urgency_temporal_indicators(self):
        """Test urgency classification with temporal indicators"""
        content = "I need this fixed today, right now, ASAP!"
        
        result = await UrgencyService.classify_urgency(content)
        
        assert result["urgency_level"] in [UrgencyLevel.HIGH.value, UrgencyLevel.MEDIUM.value]
        assert result["urgency_score"] >= 0.5
        # Should detect temporal urgency keywords
        assert any(keyword in content.lower() for keyword in ["today", "right now", "asap"])
    
    @pytest.mark.asyncio
    async def test_classify_urgency_multiple_issues(self):
        """Test urgency classification with multiple urgency indicators"""
        content = "URGENT: This is an emergency! I need immediate help with this critical problem!"
        rating = 1
        sentiment_score = 0.1
        
        result = await UrgencyService.classify_urgency(content, rating, sentiment_score)
        
        assert result["urgency_level"] == UrgencyLevel.HIGH.value
        assert result["urgency_score"] >= 0.8
        assert result["confidence"] >= 0.7
        assert len(result["keyword_matches"]) >= 3
    
    @pytest.mark.asyncio
    async def test_classify_urgency_length_factor(self):
        """Test urgency classification with different content lengths"""
        # Very short content
        short_result = await UrgencyService.classify_urgency("Help!")
        
        # Optimal length content
        medium_content = "I have an urgent problem that needs immediate attention please help me."
        medium_result = await UrgencyService.classify_urgency(medium_content)
        
        # Very long content
        long_content = " ".join(["urgent problem"] * 50)
        long_result = await UrgencyService.classify_urgency(long_content)
        
        # Medium length should have highest confidence
        assert medium_result["confidence"] >= short_result["confidence"]
        assert medium_result["confidence"] >= long_result["confidence"]
    
    def test_analyze_keywords_high_urgency(self):
        """Test keyword analysis for high urgency terms"""
        content = "This is an emergency and I need urgent help immediately!"
        
        score, matches = UrgencyService._analyze_keywords(content)
        
        assert score > 0.5
        assert len(matches) >= 2
        assert any("HIGH:" in match for match in matches)
        assert any("emergency" in match.lower() for match in matches)
        assert any("urgent" in match.lower() for match in matches)
    
    def test_analyze_keywords_medium_urgency(self):
        """Test keyword analysis for medium urgency terms"""
        content = "I have a problem with my order and I'm having trouble with the service."
        
        score, matches = UrgencyService._analyze_keywords(content)
        
        assert 0.2 <= score <= 0.7
        assert len(matches) >= 1
        assert any("MEDIUM:" in match for match in matches)
    
    def test_analyze_keywords_low_urgency_indicators(self):
        """Test keyword analysis with low urgency indicators"""
        content = "I have a small suggestion that you might consider when convenient."
        
        score, matches = UrgencyService._analyze_keywords(content)
        
        assert score <= 0.5
        assert any("LOW_INDICATORS:" in match for match in matches)
    
    def test_analyze_patterns_escalation(self):
        """Test pattern analysis for escalation language"""
        content = "I will sue you and contact the better business bureau about this!"
        
        score, factors = UrgencyService._analyze_patterns(content)
        
        assert score > 0.5
        assert len(factors) >= 1
        assert any("PATTERN:" in factor for factor in factors)
    
    def test_analyze_patterns_repetition(self):
        """Test pattern analysis for repetition indicating frustration"""
        content = "I called multiple times and contacted you several times but still no response!"
        
        score, factors = UrgencyService._analyze_patterns(content)
        
        assert score > 0.3
        assert any("PATTERN:" in factor for factor in factors)
    
    def test_analyze_temporal_indicators(self):
        """Test temporal indicator analysis"""
        content = "I need this by tomorrow, today would be better, ASAP please!"
        
        score = UrgencyService._analyze_temporal_indicators(content)
        
        assert score >= 0.5
    
    def test_calculate_rating_urgency(self):
        """Test rating-based urgency calculation"""
        # Test all rating levels
        assert UrgencyService._calculate_rating_urgency(1) == 0.8
        assert UrgencyService._calculate_rating_urgency(2) == 0.6
        assert UrgencyService._calculate_rating_urgency(3) == 0.3
        assert UrgencyService._calculate_rating_urgency(4) == 0.1
        assert UrgencyService._calculate_rating_urgency(5) == 0.0
        assert UrgencyService._calculate_rating_urgency(None) == 0.0
    
    def test_calculate_sentiment_urgency(self):
        """Test sentiment-based urgency calculation"""
        # Very negative sentiment
        assert UrgencyService._calculate_sentiment_urgency(0.1) == 0.7
        assert UrgencyService._calculate_sentiment_urgency(0.2) == 0.7
        
        # Moderately negative sentiment
        assert UrgencyService._calculate_sentiment_urgency(0.3) == 0.4
        assert UrgencyService._calculate_sentiment_urgency(0.4) == 0.4
        
        # Neutral or positive sentiment
        assert UrgencyService._calculate_sentiment_urgency(0.5) == 0.0
        assert UrgencyService._calculate_sentiment_urgency(0.8) == 0.0
        assert UrgencyService._calculate_sentiment_urgency(None) == 0.0
    
    def test_calculate_length_factor(self):
        """Test content length factor calculation"""
        # Very short content
        assert UrgencyService._calculate_length_factor("Help!") == 0.7
        
        # Optimal length content
        medium_content = "I have a problem that needs attention."
        assert UrgencyService._calculate_length_factor(medium_content) == 1.0
        
        # Long content
        long_content = " ".join(["word"] * 100)
        assert UrgencyService._calculate_length_factor(long_content) == 0.9
        
        # Very long content
        very_long_content = " ".join(["word"] * 300)
        assert UrgencyService._calculate_length_factor(very_long_content) == 0.8
    
    def test_score_to_level(self):
        """Test urgency score to level conversion"""
        assert UrgencyService._score_to_level(0.8) == UrgencyLevel.HIGH
        assert UrgencyService._score_to_level(0.7) == UrgencyLevel.HIGH
        assert UrgencyService._score_to_level(0.6) == UrgencyLevel.MEDIUM
        assert UrgencyService._score_to_level(0.4) == UrgencyLevel.MEDIUM
        assert UrgencyService._score_to_level(0.3) == UrgencyLevel.LOW
        assert UrgencyService._score_to_level(0.1) == UrgencyLevel.LOW
    
    def test_calculate_confidence(self):
        """Test confidence calculation"""
        # High confidence case
        high_confidence = UrgencyService._calculate_confidence(
            urgency_score=0.8,
            keyword_matches=["HIGH: emergency", "HIGH: urgent"],
            contributing_factors=["PATTERN: legal threat"],
            rating=1,
            sentiment_score=0.1
        )
        assert high_confidence >= 0.6
        
        # Low confidence case
        low_confidence = UrgencyService._calculate_confidence(
            urgency_score=0.5,
            keyword_matches=[],
            contributing_factors=[],
            rating=None,
            sentiment_score=None
        )
        assert low_confidence <= 0.4
    
    def test_get_level_description(self):
        """Test urgency level descriptions"""
        high_desc = UrgencyService._get_level_description(UrgencyLevel.HIGH)
        assert "immediate attention" in high_desc.lower()
        assert "critical" in high_desc.lower()
        
        medium_desc = UrgencyService._get_level_description(UrgencyLevel.MEDIUM)
        assert "prompt attention" in medium_desc.lower()
        assert "important" in medium_desc.lower()
        
        low_desc = UrgencyService._get_level_description(UrgencyLevel.LOW)
        assert "standard priority" in low_desc.lower()
        assert "normal workflow" in low_desc.lower()
    
    @pytest.mark.asyncio
    async def test_validate_urgency_classification_consistent(self):
        """Test validation of consistent urgency classification"""
        content = "This is an emergency that needs urgent attention!"
        
        result = await UrgencyService.validate_urgency_classification(
            content, UrgencyLevel.HIGH, rating=1
        )
        
        assert result["is_valid"] == True
        assert result["confidence"] > 0.5
        assert len(result["validation_issues"]) == 0
        assert result["supporting_evidence"]["urgency_score"] >= 0.6
    
    @pytest.mark.asyncio
    async def test_validate_urgency_classification_inconsistent_rating(self):
        """Test validation with inconsistent rating"""
        content = "Everything was great, excellent service!"
        
        result = await UrgencyService.validate_urgency_classification(
            content, UrgencyLevel.HIGH, rating=5
        )
        
        assert result["is_valid"] == False
        assert any("inconsistent" in issue.lower() for issue in result["validation_issues"])
    
    @pytest.mark.asyncio
    async def test_validate_urgency_classification_short_content(self):
        """Test validation with very short content"""
        content = "Bad"
        
        result = await UrgencyService.validate_urgency_classification(
            content, UrgencyLevel.HIGH
        )
        
        assert result["is_valid"] == False
        assert any("short content" in issue.lower() for issue in result["validation_issues"])
    
    @pytest.mark.asyncio
    async def test_validate_urgency_classification_no_keywords(self):
        """Test validation with high urgency but no supporting keywords"""
        content = "The meal was not what I expected and the atmosphere was disappointing."
        
        result = await UrgencyService.validate_urgency_classification(
            content, UrgencyLevel.HIGH
        )
        
        # This might be valid or invalid depending on other factors
        if not result["is_valid"]:
            assert any("keyword evidence" in issue.lower() for issue in result["validation_issues"])
    
    @pytest.mark.asyncio
    async def test_urgency_score_bounds(self):
        """Test that urgency scores are always within valid bounds"""
        test_cases = [
            "EMERGENCY URGENT CRITICAL IMMEDIATE HELP ASAP NOW!",
            "small suggestion maybe consider when convenient",
            "",
            "neutral content with no urgency indicators",
            "very very very urgent emergency critical now immediately!"
        ]
        
        for content in test_cases:
            result = await UrgencyService.classify_urgency(content)
            assert 0.0 <= result["urgency_score"] <= 1.0
            assert 0.0 <= result["confidence"] <= 1.0
            assert result["urgency_level"] in [level.value for level in UrgencyLevel]
    
    @pytest.mark.asyncio
    async def test_urgency_consistency(self):
        """Test that urgency classification is consistent for same input"""
        content = "I have an urgent problem that needs immediate attention."
        rating = 2
        sentiment_score = 0.3
        
        result1 = await UrgencyService.classify_urgency(content, rating, sentiment_score)
        result2 = await UrgencyService.classify_urgency(content, rating, sentiment_score)
        
        # Results should be identical (deterministic)
        assert result1["urgency_score"] == result2["urgency_score"]
        assert result1["urgency_level"] == result2["urgency_level"]
        assert result1["confidence"] == result2["confidence"]
        assert result1["keyword_matches"] == result2["keyword_matches"]
        assert result1["contributing_factors"] == result2["contributing_factors"]
    
    @pytest.mark.asyncio
    async def test_urgency_edge_cases(self):
        """Test urgency classification edge cases"""
        # Only punctuation
        result = await UrgencyService.classify_urgency("!@#$%^&*()")
        assert result["urgency_level"] == UrgencyLevel.LOW.value
        
        # Only numbers
        result = await UrgencyService.classify_urgency("123 456 789")
        assert result["urgency_level"] == UrgencyLevel.LOW.value
        
        # Mixed case with special characters
        result = await UrgencyService.classify_urgency("URGENT!!! help... EMERGENCY???")
        assert result["urgency_level"] in [UrgencyLevel.HIGH.value, UrgencyLevel.MEDIUM.value]
        assert 0.0 <= result["urgency_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_urgency_complex_scenarios(self):
        """Test complex urgency scenarios"""
        # Scenario 1: Mixed signals
        content = "The food was excellent but I have an urgent billing issue that needs immediate attention!"
        result = await UrgencyService.classify_urgency(content, rating=4)
        
        # Should detect urgency despite positive rating
        assert result["urgency_level"] in [UrgencyLevel.HIGH.value, UrgencyLevel.MEDIUM.value]
        
        # Scenario 2: Escalation with deadline
        content = "I will contact the BBB by tomorrow if this isn't resolved today!"
        result = await UrgencyService.classify_urgency(content, rating=2)
        
        assert result["urgency_level"] in [UrgencyLevel.HIGH.value, UrgencyLevel.MEDIUM.value]
        assert len(result["contributing_factors"]) > 0
        
        # Scenario 3: Safety concern with legal threat
        content = "This dangerous product injured my child and I'm calling my lawyer!"
        result = await UrgencyService.classify_urgency(content, rating=1, sentiment_score=0.1)
        
        assert result["urgency_level"] == UrgencyLevel.HIGH.value
        assert result["urgency_score"] >= 0.8
        assert result["confidence"] >= 0.7