"""
Issue categorization service for review content
"""
import re
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

from app.models.review import IssueCategory


@dataclass
class CategoryResult:
    """Category classification result"""
    categories: List[IssueCategory]
    confidences: Dict[str, float]
    primary_category: IssueCategory
    category_scores: Dict[str, float]
    keyword_evidence: Dict[str, List[str]]


class CategorizationService:
    """Service for categorizing issues in review content"""
    
    # Category-specific keywords and patterns
    CATEGORY_KEYWORDS = {
        IssueCategory.SUPPORT: {
            # Staff and service keywords
            'staff': 0.7, 'employee': 0.7, 'worker': 0.6, 'service': 0.8,
            'customer service': 0.9, 'help': 0.6, 'assistance': 0.7,
            'support': 0.9, 'representative': 0.7, 'agent': 0.6,
            
            # Service quality
            'rude': 0.8, 'unhelpful': 0.8, 'friendly': 0.7, 'helpful': 0.7,
            'professional': 0.6, 'unprofessional': 0.8, 'courteous': 0.6,
            'attitude': 0.7, 'behavior': 0.6, 'manner': 0.6,
            
            # Communication issues
            'communication': 0.8, 'response': 0.6, 'reply': 0.6,
            'contact': 0.5, 'phone': 0.4, 'email': 0.4, 'chat': 0.5,
            'ignored': 0.7, 'unresponsive': 0.8, 'no response': 0.8
        },
        
        IssueCategory.PRICING: {
            # Price-related terms
            'price': 0.9, 'cost': 0.8, 'expensive': 0.9, 'cheap': 0.7,
            'overpriced': 0.9, 'overcharged': 0.9, 'fee': 0.7, 'charge': 0.8,
            'bill': 0.7, 'billing': 0.8, 'invoice': 0.7, 'payment': 0.6,
            
            # Value perception
            'value': 0.8, 'worth': 0.7, 'money': 0.6, 'budget': 0.6,
            'affordable': 0.7, 'reasonable': 0.6, 'fair price': 0.8,
            'good deal': 0.7, 'rip off': 0.9, 'waste of money': 0.9,
            
            # Financial issues
            'refund': 0.8, 'discount': 0.6, 'promotion': 0.5, 'coupon': 0.5,
            'hidden fee': 0.9, 'extra charge': 0.8, 'unexpected cost': 0.8
        },
        
        IssueCategory.DELIVERY: {
            # Delivery and shipping
            'delivery': 0.9, 'shipping': 0.9, 'delivered': 0.8, 'shipped': 0.7,
            'package': 0.7, 'order': 0.6, 'arrived': 0.6, 'receive': 0.6,
            
            # Timing issues
            'late': 0.8, 'delayed': 0.9, 'slow': 0.7, 'quick': 0.6,
            'fast': 0.6, 'on time': 0.7, 'prompt': 0.6, 'timely': 0.6,
            'schedule': 0.6, 'expected': 0.5, 'promised': 0.6,
            
            # Delivery problems
            'lost': 0.8, 'missing': 0.8, 'damaged in transit': 0.9,
            'wrong address': 0.8, 'delivery failed': 0.9, 'not delivered': 0.9,
            'tracking': 0.6, 'courier': 0.7, 'driver': 0.6
        },
        
        IssueCategory.QUALITY: {
            # Product/service quality
            'quality': 0.9, 'defective': 0.9, 'broken': 0.8, 'damaged': 0.8,
            'faulty': 0.9, 'poor quality': 0.9, 'high quality': 0.7,
            'excellent quality': 0.7, 'good quality': 0.7,
            
            # Condition and functionality
            'condition': 0.7, 'working': 0.6, 'not working': 0.8,
            'malfunctioning': 0.9, 'defect': 0.9, 'flaw': 0.8,
            'issue': 0.5, 'problem': 0.5, 'fault': 0.8,
            
            # Standards and expectations
            'standard': 0.6, 'expectation': 0.6, 'disappointing': 0.7,
            'subpar': 0.8, 'inferior': 0.8, 'superior': 0.6,
            'craftsmanship': 0.7, 'workmanship': 0.7
        },
        
        IssueCategory.BILLING: {
            # Billing and payment
            'billing': 0.9, 'bill': 0.8, 'invoice': 0.8, 'payment': 0.7,
            'charge': 0.7, 'charged': 0.7, 'account': 0.6, 'statement': 0.7,
            
            # Billing issues
            'billing error': 0.9, 'wrong charge': 0.9, 'incorrect bill': 0.9,
            'overcharged': 0.9, 'double charged': 0.9, 'unauthorized': 0.8,
            'fraud': 0.8, 'dispute': 0.8, 'chargeback': 0.8,
            
            # Payment methods
            'credit card': 0.6, 'debit card': 0.6, 'paypal': 0.5,
            'bank': 0.5, 'transaction': 0.6, 'auto pay': 0.6
        },
        
        IssueCategory.TECHNICAL: {
            # Technical issues
            'technical': 0.9, 'technology': 0.7, 'system': 0.7, 'software': 0.8,
            'hardware': 0.8, 'app': 0.7, 'application': 0.7, 'website': 0.8,
            
            # Technical problems
            'bug': 0.9, 'error': 0.8, 'crash': 0.9, 'freeze': 0.8,
            'slow': 0.6, 'loading': 0.7, 'connection': 0.7, 'network': 0.7,
            'server': 0.7, 'database': 0.7, 'login': 0.6, 'password': 0.6,
            
            # Technical functionality
            'feature': 0.6, 'function': 0.6, 'interface': 0.7, 'usability': 0.7,
            'user experience': 0.7, 'navigation': 0.6, 'design': 0.5
        }
    }
    
    # Category-specific patterns
    CATEGORY_PATTERNS = {
        IssueCategory.SUPPORT: [
            r'(?:staff|employee|worker) (?:was|were) (?:rude|unhelpful|unprofessional)',
            r'(?:customer service|support) (?:is|was) (?:terrible|awful|poor)',
            r'(?:no|poor|bad) (?:customer service|support|help)',
            r'(?:waited|wait) (?:forever|hours|long time) for (?:help|service|response)',
            r'(?:ignored|dismissed|brushed off) (?:by|from) (?:staff|employee)'
        ],
        
        IssueCategory.PRICING: [
            r'(?:too|very|extremely) (?:expensive|costly|pricey)',
            r'(?:overpriced|overcharged) (?:for|by)',
            r'(?:not worth|waste of) (?:the )?money',
            r'(?:hidden|extra|additional|unexpected) (?:fees?|charges?|costs?)',
            r'(?:price|cost) (?:is|was) (?:ridiculous|outrageous|unreasonable)'
        ],
        
        IssueCategory.DELIVERY: [
            r'(?:delivery|shipping) (?:was|is) (?:late|delayed|slow)',
            r'(?:never|didn\'t|not) (?:received|delivered|arrived)',
            r'(?:package|order) (?:was|is) (?:lost|missing|damaged)',
            r'(?:delivery|shipping) (?:took|takes) (?:forever|too long|weeks)',
            r'(?:wrong|incorrect) (?:delivery|shipping) (?:address|location)'
        ],
        
        IssueCategory.QUALITY: [
            r'(?:poor|bad|terrible|awful) (?:quality|condition)',
            r'(?:broken|damaged|defective|faulty) (?:when|upon) (?:arrival|delivery)',
            r'(?:not|doesn\'t|didn\'t) (?:work|function) (?:properly|correctly)',
            r'(?:quality|condition) (?:is|was) (?:disappointing|subpar|inferior)',
            r'(?:cheaply|poorly) (?:made|built|constructed)'
        ],
        
        IssueCategory.BILLING: [
            r'(?:billing|payment) (?:error|mistake|issue|problem)',
            r'(?:charged|billed) (?:twice|double|incorrectly|wrong amount)',
            r'(?:unauthorized|fraudulent|suspicious) (?:charge|transaction)',
            r'(?:can\'t|unable to|difficulty) (?:pay|make payment)',
            r'(?:billing|payment) (?:dispute|disagreement|discrepancy)'
        ],
        
        IssueCategory.TECHNICAL: [
            r'(?:website|app|system) (?:is|was) (?:down|not working|broken)',
            r'(?:technical|system) (?:error|issue|problem|glitch)',
            r'(?:can\'t|unable to|couldn\'t) (?:log in|access|connect)',
            r'(?:slow|sluggish|unresponsive) (?:website|app|system|loading)',
            r'(?:bug|error|crash|freeze) (?:in|with|on) (?:the )?(?:app|website|system)'
        ]
    }
    
    # Category relationships and conflicts
    CATEGORY_RELATIONSHIPS = {
        # Categories that often appear together
        'complementary': {
            (IssueCategory.SUPPORT, IssueCategory.BILLING): 0.7,
            (IssueCategory.DELIVERY, IssueCategory.QUALITY): 0.6,
            (IssueCategory.TECHNICAL, IssueCategory.SUPPORT): 0.8,
            (IssueCategory.PRICING, IssueCategory.BILLING): 0.9
        },
        
        # Categories that rarely appear together
        'conflicting': {
            (IssueCategory.PRICING, IssueCategory.QUALITY): 0.3,  # Can conflict but not always
        }
    }
    
    @staticmethod
    async def categorize_issues(
        content: str,
        title: str = None,
        rating: int = None,
        min_confidence: float = 0.3
    ) -> Dict[str, Any]:
        """
        Categorize issues in review content with multi-category support
        """
        if not content or not content.strip():
            return CategorizationService._create_result([], {}, None, {}, {})
        
        # Combine content and title for analysis
        full_text = content
        if title:
            full_text = f"{title} {content}"
        
        # Calculate scores for each category
        category_scores = {}
        keyword_evidence = {}
        
        for category in IssueCategory:
            score, keywords = CategorizationService._calculate_category_score(
                full_text, category, rating
            )
            category_scores[category.value] = score
            keyword_evidence[category.value] = keywords
        
        # Apply pattern matching
        pattern_scores = CategorizationService._analyze_patterns(full_text)
        
        # Combine keyword and pattern scores
        for category, pattern_score in pattern_scores.items():
            if category in category_scores:
                category_scores[category] = min(
                    category_scores[category] + pattern_score * 0.3, 1.0
                )
        
        # Apply category relationships
        adjusted_scores = CategorizationService._apply_category_relationships(category_scores)
        
        # Filter categories by minimum confidence
        confident_categories = {
            cat: score for cat, score in adjusted_scores.items() 
            if score >= min_confidence
        }
        
        # Sort categories by score
        sorted_categories = sorted(
            confident_categories.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Extract results
        categories = [IssueCategory(cat) for cat, _ in sorted_categories]
        confidences = {cat: round(score, 3) for cat, score in sorted_categories}
        primary_category = categories[0] if categories else None
        
        return CategorizationService._create_result(
            categories, confidences, primary_category, 
            adjusted_scores, keyword_evidence
        )
    
    @staticmethod
    def _calculate_category_score(
        content: str, 
        category: IssueCategory, 
        rating: int = None
    ) -> Tuple[float, List[str]]:
        """Calculate score for a specific category"""
        content_lower = content.lower()
        keywords = CategorizationService.CATEGORY_KEYWORDS.get(category, {})
        
        total_score = 0.0
        matched_keywords = []
        
        # Analyze keywords
        for keyword, weight in keywords.items():
            if keyword in content_lower:
                total_score += weight
                matched_keywords.append(keyword)
        
        # Normalize by content length
        word_count = len(content.split())
        if word_count > 0:
            normalized_score = min(total_score / (word_count / 30), 1.0)  # Per 30 words
        else:
            normalized_score = 0.0
        
        # Apply rating-based adjustment
        if rating is not None:
            rating_adjustment = CategorizationService._get_rating_adjustment(category, rating)
            normalized_score *= rating_adjustment
        
        return min(normalized_score, 1.0), matched_keywords
    
    @staticmethod
    def _analyze_patterns(content: str) -> Dict[str, float]:
        """Analyze category-specific patterns"""
        content_lower = content.lower()
        pattern_scores = defaultdict(float)
        
        for category, patterns in CategorizationService.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content_lower)
                match_count = len(list(matches))
                
                if match_count > 0:
                    # Each pattern match adds to the category score
                    pattern_scores[category.value] += min(match_count * 0.2, 0.4)
        
        return dict(pattern_scores)
    
    @staticmethod
    def _apply_category_relationships(scores: Dict[str, float]) -> Dict[str, float]:
        """Apply category relationship rules"""
        adjusted_scores = scores.copy()
        
        # Boost complementary categories
        complementary = CategorizationService.CATEGORY_RELATIONSHIPS['complementary']
        for (cat1, cat2), boost_factor in complementary.items():
            cat1_val, cat2_val = cat1.value, cat2.value
            
            if cat1_val in scores and cat2_val in scores:
                if scores[cat1_val] > 0.3 and scores[cat2_val] > 0.3:
                    # Both categories have some evidence, boost both
                    adjusted_scores[cat1_val] = min(scores[cat1_val] * boost_factor, 1.0)
                    adjusted_scores[cat2_val] = min(scores[cat2_val] * boost_factor, 1.0)
        
        return adjusted_scores
    
    @staticmethod
    def _get_rating_adjustment(category: IssueCategory, rating: int) -> float:
        """Get rating-based adjustment factor for category"""
        
        # Low ratings often indicate service/quality issues
        if rating <= 2:
            if category in [IssueCategory.SUPPORT, IssueCategory.QUALITY]:
                return 1.2  # Boost service/quality categories for low ratings
            elif category == IssueCategory.DELIVERY:
                return 1.1  # Slight boost for delivery issues
        
        # High ratings less likely to have major issues
        elif rating >= 4:
            if category in [IssueCategory.SUPPORT, IssueCategory.QUALITY]:
                return 0.8  # Reduce service/quality issues for high ratings
        
        return 1.0  # No adjustment
    
    @staticmethod
    def _create_result(
        categories: List[IssueCategory],
        confidences: Dict[str, float],
        primary_category: IssueCategory,
        all_scores: Dict[str, float],
        keyword_evidence: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Create standardized categorization result"""
        return {
            "categories": [cat.value for cat in categories],
            "confidences": confidences,
            "primary_category": primary_category.value if primary_category else None,
            "category_scores": {k: round(v, 3) for k, v in all_scores.items()},
            "keyword_evidence": keyword_evidence,
            "multi_category": len(categories) > 1,
            "category_count": len(categories)
        }
    
    @staticmethod
    async def validate_categorization(
        content: str,
        predicted_categories: List[IssueCategory],
        rating: int = None
    ) -> Dict[str, Any]:
        """Validate categorization results"""
        
        # Re-analyze to get detailed breakdown
        analysis = await CategorizationService.categorize_issues(content, rating=rating)
        
        validation_issues = []
        
        # Check for missing obvious categories
        high_score_categories = [
            cat for cat, score in analysis["category_scores"].items() 
            if score > 0.6
        ]
        
        predicted_category_values = [cat.value for cat in predicted_categories]
        
        for high_score_cat in high_score_categories:
            if high_score_cat not in predicted_category_values:
                validation_issues.append(f"High-confidence category '{high_score_cat}' not predicted")
        
        # Check for low-confidence predictions
        for cat in predicted_categories:
            if analysis["category_scores"].get(cat.value, 0) < 0.3:
                validation_issues.append(f"Low confidence for predicted category '{cat.value}'")
        
        # Check category count reasonableness
        if len(predicted_categories) > 4:
            validation_issues.append("Too many categories predicted (>4)")
        
        return {
            "is_valid": len(validation_issues) == 0,
            "validation_issues": validation_issues,
            "analysis_breakdown": analysis,
            "confidence_summary": {
                "avg_confidence": sum(analysis["confidences"].values()) / len(analysis["confidences"]) if analysis["confidences"] else 0,
                "min_confidence": min(analysis["confidences"].values()) if analysis["confidences"] else 0,
                "max_confidence": max(analysis["confidences"].values()) if analysis["confidences"] else 0
            }
        }
    
    @staticmethod
    async def get_category_suggestions(
        content: str,
        current_categories: List[IssueCategory] = None
    ) -> Dict[str, Any]:
        """Get suggestions for additional categories"""
        
        analysis = await CategorizationService.categorize_issues(content, min_confidence=0.2)
        
        current_category_values = [cat.value for cat in (current_categories or [])]
        
        # Find categories with decent scores that aren't currently assigned
        suggestions = []
        for cat, score in analysis["category_scores"].items():
            if cat not in current_category_values and score >= 0.2:
                suggestions.append({
                    "category": cat,
                    "confidence": round(score, 3),
                    "evidence": analysis["keyword_evidence"].get(cat, [])[:3]  # Top 3 keywords
                })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "suggestions": suggestions[:3],  # Top 3 suggestions
            "total_analyzed": len(analysis["category_scores"]),
            "current_categories": current_category_values
        }
