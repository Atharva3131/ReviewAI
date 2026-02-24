"""
Urgency classification service for review content
"""
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.review import UrgencyLevel


@dataclass
class UrgencyResult:
    """Urgency classification result"""
    urgency_level: UrgencyLevel
    urgency_score: float  # 0.0 to 1.0
    confidence: float     # 0.0 to 1.0
    contributing_factors: List[str]
    keyword_matches: List[str]


class UrgencyService:
    """Service for classifying urgency level of reviews"""
    
    # High urgency keywords and phrases
    HIGH_URGENCY_KEYWORDS = {
        # Immediate action required
        'emergency': 1.0, 'urgent': 0.9, 'immediately': 0.9, 'asap': 0.9,
        'right now': 0.9, 'critical': 0.9, 'crisis': 1.0, 'disaster': 0.9,
        
        # Safety and health concerns
        'dangerous': 0.9, 'unsafe': 0.8, 'hazard': 0.8, 'risk': 0.7,
        'injury': 0.8, 'hurt': 0.7, 'sick': 0.7, 'poisoned': 0.9,
        'allergic reaction': 0.9, 'food poisoning': 0.9,
        
        # Severe service failures
        'nightmare': 0.8, 'disaster': 0.9, 'catastrophe': 0.8, 'chaos': 0.7,
        'completely failed': 0.8, 'total failure': 0.8, 'broke down': 0.7,
        
        # Financial urgency
        'overcharged': 0.7, 'fraud': 0.9, 'scam': 0.8, 'stolen': 0.9,
        'unauthorized charge': 0.8, 'billing error': 0.6,
        
        # Time-sensitive issues
        'deadline': 0.7, 'time sensitive': 0.8, 'expires': 0.6,
        'running out of time': 0.7, 'last minute': 0.6
    }
    
    # Medium urgency keywords
    MEDIUM_URGENCY_KEYWORDS = {
        # Service issues
        'problem': 0.5, 'issue': 0.5, 'trouble': 0.6, 'difficulty': 0.5,
        'concern': 0.5, 'complaint': 0.6, 'dissatisfied': 0.6,
        
        # Quality issues
        'defective': 0.6, 'broken': 0.6, 'damaged': 0.6, 'faulty': 0.6,
        'not working': 0.6, 'malfunctioning': 0.6, 'poor quality': 0.5,
        
        # Service delays
        'delayed': 0.5, 'late': 0.5, 'slow': 0.5, 'waiting': 0.4,
        'behind schedule': 0.5, 'overdue': 0.6,
        
        # Communication issues
        'no response': 0.6, 'ignored': 0.6, 'unresponsive': 0.6,
        'poor communication': 0.5, 'lack of information': 0.5
    }
    
    # Low urgency indicators
    LOW_URGENCY_INDICATORS = {
        'suggestion', 'recommend', 'could improve', 'minor', 'small',
        'feedback', 'opinion', 'thought', 'consider', 'maybe',
        'perhaps', 'possibly', 'eventually', 'when convenient'
    }
    
    # Urgency patterns (regex patterns with scores)
    URGENCY_PATTERNS = {
        # Immediate action patterns
        r'need(?:s)? (?:immediate|urgent|quick) (?:help|assistance|response)': 0.9,
        r'this (?:is|was) (?:an )?emergency': 0.9,
        r'please (?:help|fix|resolve) (?:immediately|urgently|asap)': 0.8,
        r'can\'?t wait (?:any )?longer': 0.8,
        r'time is running out': 0.8,
        
        # Escalation patterns
        r'(?:will|going to) (?:sue|report|complain to|contact)': 0.7,
        r'(?:lawyer|attorney|legal action)': 0.8,
        r'(?:better business bureau|bbb|consumer protection)': 0.7,
        r'(?:social media|facebook|twitter|instagram|review sites)': 0.6,
        
        # Repetition patterns (indicating frustration)
        r'(?:called|contacted|tried) (?:multiple times|several times|many times)': 0.6,
        r'(?:this is the|it\'s been) (?:\d+)(?:st|nd|rd|th) time': 0.6,
        r'(?:still|yet) (?:no|not) (?:response|reply|solution)': 0.7,
        
        # Deadline patterns
        r'(?:by|before) (?:tomorrow|today|end of (?:day|week))': 0.7,
        r'(?:deadline|due date) (?:is|was) (?:today|tomorrow|yesterday)': 0.8,
        
        # Impact patterns
        r'(?:business|company|operation) (?:is|was) (?:affected|impacted|down)': 0.8,
        r'(?:losing|lost) (?:money|revenue|customers|business)': 0.7,
        r'(?:reputation|image) (?:is|being) (?:damaged|hurt|affected)': 0.6
    }
    
    # Temporal urgency indicators
    TEMPORAL_INDICATORS = {
        'now': 0.8, 'today': 0.7, 'immediately': 0.9, 'asap': 0.9,
        'urgent': 0.8, 'quickly': 0.6, 'soon': 0.4, 'fast': 0.5,
        'right away': 0.8, 'at once': 0.8, 'without delay': 0.8
    }
    
    @staticmethod
    async def classify_urgency(
        content: str,
        rating: int = None,
        sentiment_score: float = None,
        title: str = None
    ) -> Dict[str, Any]:
        """
        Classify urgency level of review content
        """
        if not content or not content.strip():
            return UrgencyService._create_result(
                UrgencyLevel.LOW, 0.1, 0.0, [], []
            )
        
        # CRITICAL: 1-2 star reviews are ALWAYS high urgency
        if rating is not None and rating <= 2:
            return UrgencyService._create_result(
                UrgencyLevel.HIGH, 
                0.9, 
                1.0, 
                ["Low rating (1-2 stars) - automatic high urgency"],
                ["rating_based"]
            )
        
        # Combine content and title for analysis
        full_text = content
        if title:
            full_text = f"{title} {content}"
        
        # Calculate base urgency score
        keyword_score, keyword_matches = UrgencyService._analyze_keywords(full_text)
        pattern_score, contributing_factors = UrgencyService._analyze_patterns(full_text)
        temporal_score = UrgencyService._analyze_temporal_indicators(full_text)
        
        # Rating-based urgency (low ratings often indicate urgent issues)
        rating_score = UrgencyService._calculate_rating_urgency(rating)
        
        # Sentiment-based urgency (very negative sentiment can indicate urgency)
        sentiment_urgency = UrgencyService._calculate_sentiment_urgency(sentiment_score)
        
        # Combine scores with weights
        urgency_score = (
            keyword_score * 0.25 +
            pattern_score * 0.20 +
            temporal_score * 0.15 +
            rating_score * 0.30 +      # Increased weight for rating
            sentiment_urgency * 0.10
        )
        
        # Apply content length factor
        length_factor = UrgencyService._calculate_length_factor(content)
        urgency_score *= length_factor
        
        # Clamp to valid range
        urgency_score = max(0.0, min(1.0, urgency_score))
        
        # Determine urgency level
        urgency_level = UrgencyService._score_to_level(urgency_score)
        
        # Calculate confidence
        confidence = UrgencyService._calculate_confidence(
            urgency_score, keyword_matches, contributing_factors, rating, sentiment_score
        )
        
        return UrgencyService._create_result(
            urgency_level, urgency_score, confidence, contributing_factors, keyword_matches
        )
    
    @staticmethod
    def _analyze_keywords(content: str) -> Tuple[float, List[str]]:
        """Analyze urgency keywords in content"""
        content_lower = content.lower()
        total_score = 0.0
        matches = []
        
        # Check high urgency keywords
        for keyword, score in UrgencyService.HIGH_URGENCY_KEYWORDS.items():
            if keyword in content_lower:
                total_score += score
                matches.append(f"HIGH: {keyword}")
        
        # Check medium urgency keywords
        for keyword, score in UrgencyService.MEDIUM_URGENCY_KEYWORDS.items():
            if keyword in content_lower:
                total_score += score * 0.6  # Weight medium keywords less
                matches.append(f"MEDIUM: {keyword}")
        
        # Check for low urgency indicators (reduce score)
        low_urgency_count = sum(1 for indicator in UrgencyService.LOW_URGENCY_INDICATORS 
                               if indicator in content_lower)
        if low_urgency_count > 0:
            total_score *= (1.0 - min(low_urgency_count * 0.1, 0.3))
            matches.append(f"LOW_INDICATORS: {low_urgency_count}")
        
        # Normalize by content length (longer content can have more keywords)
        word_count = len(content.split())
        if word_count > 0:
            normalized_score = min(total_score / (word_count / 50), 1.0)  # Normalize per 50 words
        else:
            normalized_score = 0.0
        
        return normalized_score, matches
    
    @staticmethod
    def _analyze_patterns(content: str) -> Tuple[float, List[str]]:
        """Analyze urgency patterns in content"""
        content_lower = content.lower()
        total_score = 0.0
        factors = []
        
        for pattern, score in UrgencyService.URGENCY_PATTERNS.items():
            matches = re.finditer(pattern, content_lower)
            match_count = len(list(matches))
            
            if match_count > 0:
                # Multiple matches of same pattern increase urgency
                pattern_score = score * min(match_count, 2)  # Cap at 2x
                total_score += pattern_score
                factors.append(f"PATTERN: {pattern[:30]}... (x{match_count})")
        
        # Cap total pattern score
        return min(total_score, 1.0), factors
    
    @staticmethod
    def _analyze_temporal_indicators(content: str) -> float:
        """Analyze temporal urgency indicators"""
        content_lower = content.lower()
        total_score = 0.0
        
        for indicator, score in UrgencyService.TEMPORAL_INDICATORS.items():
            if indicator in content_lower:
                total_score += score
        
        # Check for specific time references
        time_patterns = [
            r'(?:by|before|within) (?:\d+) (?:hour|day|week)s?',
            r'(?:today|tomorrow|this week|next week)',
            r'(?:end of|close of) (?:business|day|week)',
            r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, content_lower):
                total_score += 0.3
        
        return min(total_score, 1.0)
    
    @staticmethod
    def _calculate_rating_urgency(rating: int) -> float:
        """Calculate urgency based on rating"""
        if rating is None:
            return 0.0
        
        # Lower ratings often indicate more urgent issues
        if rating == 1:
            return 0.9
        elif rating == 2:
            return 0.8
        elif rating == 3:
            return 0.4
        elif rating == 4:
            return 0.1
        else:  # rating == 5
            return 0.0
    
    @staticmethod
    def _calculate_sentiment_urgency(sentiment_score: float) -> float:
        """Calculate urgency based on sentiment"""
        if sentiment_score is None:
            return 0.0
        
        # Very negative sentiment can indicate urgency
        if sentiment_score <= 0.2:
            return 0.7
        elif sentiment_score <= 0.4:
            return 0.4
        else:
            return 0.0
    
    @staticmethod
    def _calculate_length_factor(content: str) -> float:
        """Calculate urgency factor based on content length"""
        word_count = len(content.split())
        
        if word_count < 10:
            return 0.7  # Very short content might miss context
        elif word_count < 50:
            return 1.0  # Optimal length
        elif word_count < 200:
            return 0.9  # Longer content might dilute urgency signals
        else:
            return 0.8  # Very long content
    
    @staticmethod
    def _score_to_level(score: float) -> UrgencyLevel:
        """Convert urgency score to level"""
        if score >= 0.7:
            return UrgencyLevel.HIGH
        elif score >= 0.4:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW
    
    @staticmethod
    def _calculate_confidence(
        urgency_score: float,
        keyword_matches: List[str],
        contributing_factors: List[str],
        rating: int,
        sentiment_score: float
    ) -> float:
        """Calculate confidence in urgency classification"""
        confidence = 0.0
        
        # Keyword evidence factor
        high_urgency_matches = len([m for m in keyword_matches if m.startswith("HIGH:")])
        medium_urgency_matches = len([m for m in keyword_matches if m.startswith("MEDIUM:")])
        
        if high_urgency_matches > 0:
            confidence += min(high_urgency_matches * 0.2, 0.4)
        if medium_urgency_matches > 0:
            confidence += min(medium_urgency_matches * 0.1, 0.2)
        
        # Pattern evidence factor
        if contributing_factors:
            confidence += min(len(contributing_factors) * 0.1, 0.3)
        
        # Rating consistency factor
        if rating is not None:
            expected_urgency = UrgencyService._calculate_rating_urgency(rating)
            consistency = 1.0 - abs(urgency_score - expected_urgency)
            confidence += consistency * 0.2
        
        # Sentiment consistency factor
        if sentiment_score is not None:
            expected_urgency = UrgencyService._calculate_sentiment_urgency(sentiment_score)
            consistency = 1.0 - abs(urgency_score - expected_urgency)
            confidence += consistency * 0.1
        
        # Score extremity factor (more confident about extreme scores)
        if urgency_score >= 0.8 or urgency_score <= 0.2:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    @staticmethod
    def _create_result(
        level: UrgencyLevel,
        score: float,
        confidence: float,
        factors: List[str],
        keywords: List[str]
    ) -> Dict[str, Any]:
        """Create standardized urgency classification result"""
        return {
            "urgency_level": level.value,
            "urgency_score": round(score, 3),
            "confidence": round(confidence, 3),
            "contributing_factors": factors,
            "keyword_matches": keywords,
            "level_description": UrgencyService._get_level_description(level)
        }
    
    @staticmethod
    def _get_level_description(level: UrgencyLevel) -> str:
        """Get human-readable description of urgency level"""
        descriptions = {
            UrgencyLevel.HIGH: "Requires immediate attention - critical issue that needs urgent response",
            UrgencyLevel.MEDIUM: "Needs prompt attention - important issue that should be addressed soon",
            UrgencyLevel.LOW: "Standard priority - can be handled in normal workflow"
        }
        return descriptions.get(level, "Unknown urgency level")
    
    @staticmethod
    async def validate_urgency_classification(
        content: str,
        predicted_level: UrgencyLevel,
        rating: int = None
    ) -> Dict[str, Any]:
        """Validate urgency classification against expected patterns"""
        
        # Re-analyze to get detailed breakdown
        analysis = await UrgencyService.classify_urgency(content, rating)
        
        # Check for obvious misclassifications
        validation_issues = []
        
        # High rating with high urgency might be inconsistent
        if rating and rating >= 4 and predicted_level == UrgencyLevel.HIGH:
            validation_issues.append("High urgency with positive rating may be inconsistent")
        
        # Very short content with high urgency
        if len(content.split()) < 5 and predicted_level == UrgencyLevel.HIGH:
            validation_issues.append("High urgency classification with very short content")
        
        # No urgency keywords but high classification
        if (predicted_level == UrgencyLevel.HIGH and 
            not any("HIGH:" in match for match in analysis["keyword_matches"])):
            validation_issues.append("High urgency without strong keyword evidence")
        
        return {
            "is_valid": len(validation_issues) == 0,
            "confidence": analysis["confidence"],
            "validation_issues": validation_issues,
            "supporting_evidence": {
                "keyword_matches": len(analysis["keyword_matches"]),
                "contributing_factors": len(analysis["contributing_factors"]),
                "urgency_score": analysis["urgency_score"]
            }
        }
