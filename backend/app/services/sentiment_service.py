"""
Sentiment analysis service for review content
"""
import re
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import math


@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    sentiment_score: float  # 0.0 to 1.0 (0 = very negative, 1 = very positive)
    confidence: float       # 0.0 to 1.0
    dominant_emotion: str   # primary emotion detected
    word_contributions: Dict[str, float]  # words that influenced the score


class SentimentService:
    """Service for analyzing sentiment in review content"""
    
    # Sentiment lexicon with weights
    POSITIVE_WORDS = {
        # Strong positive (0.8-1.0)
        'excellent': 0.9, 'amazing': 0.9, 'outstanding': 0.9, 'perfect': 0.9,
        'fantastic': 0.9, 'wonderful': 0.9, 'exceptional': 0.9, 'superb': 0.9,
        'brilliant': 0.9, 'magnificent': 0.9, 'incredible': 0.9, 'phenomenal': 0.9,
        
        # Moderate positive (0.6-0.8)
        'good': 0.7, 'great': 0.8, 'nice': 0.6, 'pleasant': 0.7, 'satisfied': 0.7,
        'happy': 0.8, 'pleased': 0.7, 'impressed': 0.8, 'recommend': 0.8,
        'love': 0.8, 'like': 0.6, 'enjoy': 0.7, 'appreciate': 0.7,
        
        # Mild positive (0.5-0.6)
        'okay': 0.55, 'fine': 0.55, 'decent': 0.6, 'acceptable': 0.55,
        'adequate': 0.55, 'reasonable': 0.6, 'fair': 0.55
    }
    
    NEGATIVE_WORDS = {
        # Strong negative (0.0-0.2)
        'terrible': 0.1, 'awful': 0.1, 'horrible': 0.1, 'disgusting': 0.05,
        'worst': 0.05, 'hate': 0.1, 'despise': 0.05, 'appalling': 0.05,
        'atrocious': 0.05, 'abysmal': 0.05, 'dreadful': 0.1, 'nightmare': 0.1,
        
        # Moderate negative (0.2-0.4)
        'bad': 0.3, 'poor': 0.3, 'disappointing': 0.2, 'unsatisfied': 0.2,
        'unhappy': 0.2, 'frustrated': 0.3, 'annoyed': 0.3, 'upset': 0.2,
        'dissatisfied': 0.2, 'unpleasant': 0.3, 'inadequate': 0.3,
        
        # Mild negative (0.4-0.5)
        'mediocre': 0.4, 'average': 0.45, 'meh': 0.4, 'so-so': 0.45,
        'nothing special': 0.4, 'could be better': 0.4
    }
    
    # Intensifiers and diminishers
    INTENSIFIERS = {
        'very': 1.3, 'extremely': 1.5, 'incredibly': 1.4, 'absolutely': 1.4,
        'completely': 1.3, 'totally': 1.3, 'really': 1.2, 'quite': 1.1,
        'so': 1.2, 'super': 1.3, 'highly': 1.2, 'exceptionally': 1.4
    }
    
    DIMINISHERS = {
        'somewhat': 0.8, 'rather': 0.8, 'fairly': 0.8, 'pretty': 0.9,
        'kind of': 0.7, 'sort of': 0.7, 'a bit': 0.7, 'slightly': 0.6,
        'barely': 0.5, 'hardly': 0.4, 'scarcely': 0.4
    }
    
    # Negation words
    NEGATION_WORDS = {
        'not', 'no', 'never', 'nothing', 'nobody', 'nowhere', 'neither',
        'nor', 'none', 'without', 'lack', 'lacking', 'missing', 'absent',
        'fail', 'failed', 'unable', 'cannot', 'can\'t', 'won\'t', 'wouldn\'t',
        'shouldn\'t', 'couldn\'t', 'don\'t', 'doesn\'t', 'didn\'t', 'isn\'t',
        'aren\'t', 'wasn\'t', 'weren\'t', 'haven\'t', 'hasn\'t', 'hadn\'t'
    }
    
    # Context-specific sentiment patterns
    SERVICE_PATTERNS = {
        r'staff (?:was|were) (?:rude|unhelpful|slow)': -0.3,
        r'staff (?:was|were) (?:friendly|helpful|professional)': 0.3,
        r'long wait|waited forever|took forever': -0.2,
        r'quick service|fast service|prompt': 0.2,
        r'clean|spotless|well maintained': 0.2,
        r'dirty|filthy|messy|unkempt': -0.3,
        r'overpriced|too expensive|rip off': -0.2,
        r'great value|good price|affordable': 0.2,
        r'would (?:not )?recommend': lambda m: -0.3 if 'not' in m.group() else 0.3,
        r'will (?:not )?(?:return|come back)': lambda m: -0.3 if 'not' in m.group() else 0.2
    }
    
    @staticmethod
    async def analyze_sentiment(content: str, rating: int = None) -> Dict[str, Any]:
        """
        Analyze sentiment of review content with deterministic algorithm
        """
        if not content or not content.strip():
            return SentimentService._create_result(0.5, 0.0, "neutral", {})
        
        # Preprocess content
        processed_content = SentimentService._preprocess_content(content)
        words = processed_content.split()
        
        # Calculate base sentiment score
        word_scores = {}
        total_score = 0.0
        scored_words = 0
        
        i = 0
        while i < len(words):
            word = words[i].lower()
            
            # Check for negation context (3 words before)
            negation_context = SentimentService._check_negation_context(words, i)
            
            # Check for intensifier/diminisher context
            intensity_modifier = SentimentService._check_intensity_context(words, i)
            
            # Get word sentiment score
            word_score = SentimentService._get_word_sentiment(word)
            
            if word_score is not None:
                # Apply negation
                if negation_context:
                    word_score = 1.0 - word_score  # Flip sentiment
                
                # Apply intensity modification
                word_score = SentimentService._apply_intensity(word_score, intensity_modifier)
                
                # Clamp to valid range
                word_score = max(0.0, min(1.0, word_score))
                
                word_scores[word] = word_score
                total_score += word_score
                scored_words += 1
            
            i += 1
        
        # Calculate base sentiment
        if scored_words > 0:
            base_sentiment = total_score / scored_words
        else:
            base_sentiment = 0.5  # Neutral if no sentiment words found
        
        # Apply contextual patterns
        pattern_adjustment = SentimentService._analyze_patterns(content)
        adjusted_sentiment = base_sentiment + pattern_adjustment
        adjusted_sentiment = max(0.0, min(1.0, adjusted_sentiment))
        
        # Rating correlation adjustment
        if rating is not None:
            rating_sentiment = SentimentService._rating_to_sentiment(rating)
            # Weighted average: 70% content analysis, 30% rating
            final_sentiment = 0.7 * adjusted_sentiment + 0.3 * rating_sentiment
        else:
            final_sentiment = adjusted_sentiment
        
        # Calculate confidence
        confidence = SentimentService._calculate_confidence(
            scored_words, len(words), rating, final_sentiment
        )
        
        # Determine dominant emotion
        dominant_emotion = SentimentService._determine_emotion(final_sentiment, word_scores)
        
        return SentimentService._create_result(
            final_sentiment, confidence, dominant_emotion, word_scores
        )
    
    @staticmethod
    def _preprocess_content(content: str) -> str:
        """Preprocess content for sentiment analysis"""
        # Convert to lowercase
        content = content.lower()
        
        # Handle contractions
        contractions = {
            "won't": "will not", "can't": "cannot", "n't": " not",
            "'re": " are", "'ve": " have", "'ll": " will", "'d": " would",
            "'m": " am", "'s": " is"
        }
        
        for contraction, expansion in contractions.items():
            content = content.replace(contraction, expansion)
        
        # Remove punctuation but keep sentence structure
        content = re.sub(r'[^\w\s]', ' ', content)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    @staticmethod
    def _check_negation_context(words: List[str], index: int) -> bool:
        """Check if word is in negation context"""
        # Look 3 words back for negation
        start = max(0, index - 3)
        context_words = words[start:index]
        
        return any(word.lower() in SentimentService.NEGATION_WORDS for word in context_words)
    
    @staticmethod
    def _check_intensity_context(words: List[str], index: int) -> float:
        """Check for intensity modifiers"""
        if index > 0:
            prev_word = words[index - 1].lower()
            
            if prev_word in SentimentService.INTENSIFIERS:
                return SentimentService.INTENSIFIERS[prev_word]
            elif prev_word in SentimentService.DIMINISHERS:
                return SentimentService.DIMINISHERS[prev_word]
        
        return 1.0  # No modification
    
    @staticmethod
    def _get_word_sentiment(word: str) -> float:
        """Get sentiment score for a word"""
        if word in SentimentService.POSITIVE_WORDS:
            return SentimentService.POSITIVE_WORDS[word]
        elif word in SentimentService.NEGATIVE_WORDS:
            return SentimentService.NEGATIVE_WORDS[word]
        else:
            return None
    
    @staticmethod
    def _apply_intensity(score: float, modifier: float) -> float:
        """Apply intensity modification to sentiment score"""
        if modifier == 1.0:
            return score
        
        # For intensifiers (>1.0), push towards extremes
        if modifier > 1.0:
            if score > 0.5:
                return score + (1.0 - score) * (modifier - 1.0) * 0.5
            else:
                return score - score * (modifier - 1.0) * 0.5
        
        # For diminishers (<1.0), push towards neutral
        else:
            return 0.5 + (score - 0.5) * modifier
    
    @staticmethod
    def _analyze_patterns(content: str) -> float:
        """Analyze contextual sentiment patterns"""
        adjustment = 0.0
        content_lower = content.lower()
        
        for pattern, value in SentimentService.SERVICE_PATTERNS.items():
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                if callable(value):
                    adjustment += value(match)
                else:
                    adjustment += value
        
        # Limit total pattern adjustment
        return max(-0.3, min(0.3, adjustment))
    
    @staticmethod
    def _rating_to_sentiment(rating: int) -> float:
        """Convert rating to sentiment score"""
        # 1 star = 0.1, 2 stars = 0.3, 3 stars = 0.5, 4 stars = 0.7, 5 stars = 0.9
        return (rating - 1) * 0.2 + 0.1
    
    @staticmethod
    def _calculate_confidence(
        scored_words: int, 
        total_words: int, 
        rating: int, 
        sentiment: float
    ) -> float:
        """Calculate confidence in sentiment analysis"""
        confidence = 0.0
        
        # Word coverage factor
        if total_words > 0:
            coverage = scored_words / total_words
            confidence += min(coverage * 2, 0.4)  # Max 0.4 from coverage
        
        # Content length factor
        if total_words >= 10:
            confidence += 0.2
        elif total_words >= 5:
            confidence += 0.1
        
        # Rating consistency factor
        if rating is not None:
            rating_sentiment = SentimentService._rating_to_sentiment(rating)
            consistency = 1.0 - abs(sentiment - rating_sentiment)
            confidence += consistency * 0.3
        
        # Sentiment extremity factor (more confident about extreme sentiments)
        extremity = abs(sentiment - 0.5) * 2  # 0 to 1
        confidence += extremity * 0.1
        
        return min(confidence, 1.0)
    
    @staticmethod
    def _determine_emotion(sentiment: float, word_scores: Dict[str, float]) -> str:
        """Determine dominant emotion from sentiment analysis"""
        if sentiment >= 0.8:
            return "joy"
        elif sentiment >= 0.6:
            return "satisfaction"
        elif sentiment >= 0.4:
            return "neutral"
        elif sentiment >= 0.2:
            return "disappointment"
        else:
            return "anger"
    
    @staticmethod
    def _create_result(
        sentiment: float, 
        confidence: float, 
        emotion: str, 
        word_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Create standardized sentiment analysis result"""
        return {
            "sentiment_score": round(sentiment, 3),
            "confidence": round(confidence, 3),
            "dominant_emotion": emotion,
            "word_contributions": word_scores,
            "sentiment_label": SentimentService._get_sentiment_label(sentiment)
        }
    
    @staticmethod
    def _get_sentiment_label(sentiment: float) -> str:
        """Get human-readable sentiment label"""
        if sentiment >= 0.8:
            return "Very Positive"
        elif sentiment >= 0.6:
            return "Positive"
        elif sentiment >= 0.4:
            return "Neutral"
        elif sentiment >= 0.2:
            return "Negative"
        else:
            return "Very Negative"
    
    @staticmethod
    async def validate_sentiment_score(score: float) -> bool:
        """Validate sentiment score is in valid range"""
        return isinstance(score, (int, float)) and 0.0 <= score <= 1.0
    
    @staticmethod
    async def check_rating_sentiment_correlation(
        rating: int, 
        sentiment_score: float,
        tolerance: float = 0.3
    ) -> Dict[str, Any]:
        """Check correlation between rating and sentiment"""
        expected_sentiment = SentimentService._rating_to_sentiment(rating)
        difference = abs(sentiment_score - expected_sentiment)
        
        is_consistent = difference <= tolerance
        
        return {
            "is_consistent": is_consistent,
            "expected_sentiment": expected_sentiment,
            "actual_sentiment": sentiment_score,
            "difference": round(difference, 3),
            "tolerance": tolerance,
            "correlation_strength": max(0.0, 1.0 - (difference / 0.5))  # 0 to 1
        }
