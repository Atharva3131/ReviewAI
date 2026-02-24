"""
Decision Rules Engine for Agent Orchestration
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.agent_decision import DecisionType

logger = logging.getLogger(__name__)


@dataclass
class DecisionRule:
    """Individual decision rule"""
    name: str
    condition: callable
    action: DecisionType
    confidence: float
    reasoning: str
    priority: int = 0  # Higher priority rules are evaluated first


class DecisionRulesEngine:
    """
    Rule-based decision engine for determining agent actions
    
    Implements deterministic business logic for deciding how to handle
    reviews, support tickets, and other customer interactions.
    """
    
    def __init__(self):
        self.review_rules = self._initialize_review_rules()
        self.ticket_rules = self._initialize_ticket_rules()
        self.safety_rules = self._initialize_safety_rules()
    
    async def decide_review_action(
        self,
        sentiment_score: float,
        urgency_level: str,
        rating: int,
        categories: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decide action for a review based on analysis results and business rules
        
        Args:
            sentiment_score: Sentiment analysis score (0.0-1.0)
            urgency_level: Urgency classification (low/medium/high)
            rating: Review rating (1-5)
            categories: List of issue categories
            context: Additional context for decision making
            
        Returns:
            Dict with decision details
        """
        decision_context = {
            "sentiment_score": sentiment_score,
            "urgency_level": urgency_level,
            "rating": rating,
            "categories": categories,
            **context
        }
        
        # Apply safety rules first
        safety_decision = self._apply_safety_rules(decision_context)
        if safety_decision:
            return safety_decision
        
        # Apply review-specific rules
        for rule in sorted(self.review_rules, key=lambda r: r.priority, reverse=True):
            if rule.condition(decision_context):
                logger.info(f"Applied review rule: {rule.name}")
                return {
                    "decision_type": rule.action,
                    "confidence_score": rule.confidence,
                    "reasoning": rule.reasoning,
                    "rule_name": rule.name,
                    "requires_approval": self._requires_approval(rule.action, rule.confidence)
                }
        
        # Default fallback
        return self._get_default_review_decision(decision_context)
    
    async def decide_ticket_action(
        self,
        sentiment_score: float,
        urgency_level: str,
        priority: str,
        categories: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decide action for a support ticket
        """
        decision_context = {
            "sentiment_score": sentiment_score,
            "urgency_level": urgency_level,
            "priority": priority,
            "categories": categories,
            **context
        }
        
        # Apply safety rules first
        safety_decision = self._apply_safety_rules(decision_context)
        if safety_decision:
            return safety_decision
        
        # Apply ticket-specific rules
        for rule in sorted(self.ticket_rules, key=lambda r: r.priority, reverse=True):
            if rule.condition(decision_context):
                logger.info(f"Applied ticket rule: {rule.name}")
                return {
                    "decision_type": rule.action,
                    "confidence_score": rule.confidence,
                    "reasoning": rule.reasoning,
                    "rule_name": rule.name,
                    "requires_approval": self._requires_approval(rule.action, rule.confidence)
                }
        
        # Default fallback
        return self._get_default_ticket_decision(decision_context)
    
    def _initialize_review_rules(self) -> List[DecisionRule]:
        """Initialize review-specific decision rules"""
        return [
            # Rule 1: Critical negative reviews (highest priority)
            DecisionRule(
                name="critical_negative_review",
                condition=lambda ctx: ctx["rating"] <= 2 and ctx["urgency_level"] == "high",
                action=DecisionType.RECOVER_PRIVATE,
                confidence=0.95,
                reasoning="Critical negative review requiring immediate private recovery",
                priority=100
            ),
            
            # Rule 2: Emergency or safety issues
            DecisionRule(
                name="emergency_safety_issue",
                condition=lambda ctx: (
                    ctx["urgency_level"] == "high" and 
                    any(keyword in str(ctx.get("content", "")).lower() 
                        for keyword in ["emergency", "danger", "unsafe", "injury", "sick"])
                ),
                action=DecisionType.ESCALATE,
                confidence=0.98,
                reasoning="Emergency or safety issue requires immediate human attention",
                priority=95
            ),
            
            # Rule 3: Legal threats or escalation language
            DecisionRule(
                name="legal_threat_escalation",
                condition=lambda ctx: any(
                    keyword in str(ctx.get("content", "")).lower() 
                    for keyword in ["lawyer", "sue", "legal action", "attorney", "court", "bbb"]
                ),
                action=DecisionType.ESCALATE,
                confidence=0.92,
                reasoning="Legal threats or escalation language requires human review",
                priority=90
            ),
            
            # Rule 4: Multiple negative categories with low sentiment
            DecisionRule(
                name="complex_negative_issues",
                condition=lambda ctx: (
                    ctx["sentiment_score"] < 0.3 and 
                    len(ctx["categories"]) >= 2 and
                    ctx["rating"] <= 3
                ),
                action=DecisionType.RECOVER_PRIVATE,
                confidence=0.85,
                reasoning="Multiple issues with negative sentiment require private recovery",
                priority=80
            ),
            
            # Rule 5: Service/quality issues with moderate negative sentiment
            DecisionRule(
                name="service_quality_issues",
                condition=lambda ctx: (
                    ctx["rating"] <= 3 and 
                    any(cat in ["support", "quality", "delivery"] for cat in ctx["categories"]) and
                    ctx["sentiment_score"] < 0.4
                ),
                action=DecisionType.RECOVER_PRIVATE,
                confidence=0.8,
                reasoning="Service or quality issues with negative sentiment need private attention",
                priority=70
            ),
            
            # Rule 6: Positive reviews (4-5 stars)
            DecisionRule(
                name="positive_review_response",
                condition=lambda ctx: ctx["rating"] >= 4,
                action=DecisionType.RESPOND_PUBLIC,
                confidence=0.9,
                reasoning="Positive review - thank customer publicly",
                priority=60
            ),
            
            # Rule 7: Neutral reviews with constructive feedback
            DecisionRule(
                name="neutral_constructive_feedback",
                condition=lambda ctx: (
                    ctx["rating"] == 3 and 
                    ctx["sentiment_score"] >= 0.4 and
                    ctx["urgency_level"] == "low"
                ),
                action=DecisionType.RESPOND_PUBLIC,
                confidence=0.75,
                reasoning="Neutral review with constructive feedback suitable for public response",
                priority=50
            ),
            
            # Rule 8: Complex cases requiring human review
            DecisionRule(
                name="complex_case_escalation",
                condition=lambda ctx: (
                    ctx["urgency_level"] == "high" and 
                    len(ctx["categories"]) > 2
                ),
                action=DecisionType.ESCALATE,
                confidence=0.6,
                reasoning="Complex multi-issue case requiring human review",
                priority=40
            ),
            
            # Rule 9: Low confidence in analysis
            DecisionRule(
                name="low_confidence_escalation",
                condition=lambda ctx: (
                    ctx.get("sentiment_confidence", 1.0) < 0.5 or
                    ctx.get("urgency_confidence", 1.0) < 0.5
                ),
                action=DecisionType.ESCALATE,
                confidence=0.4,
                reasoning="Low confidence in analysis requires human review",
                priority=30
            ),
            
            # Rule 10: Moderate negative reviews
            DecisionRule(
                name="moderate_negative_response",
                condition=lambda ctx: (
                    ctx["rating"] <= 3 and 
                    ctx["sentiment_score"] >= 0.3 and
                    ctx["urgency_level"] in ["low", "medium"]
                ),
                action=DecisionType.RESPOND_PUBLIC,
                confidence=0.7,
                reasoning="Moderate negative review suitable for public response",
                priority=20
            )
        ]
    
    def _initialize_ticket_rules(self) -> List[DecisionRule]:
        """Initialize support ticket decision rules"""
        return [
            # Rule 1: High priority tickets with negative sentiment
            DecisionRule(
                name="high_priority_negative_ticket",
                condition=lambda ctx: (
                    ctx["priority"] == "high" and 
                    ctx["sentiment_score"] < 0.4
                ),
                action=DecisionType.ESCALATE,
                confidence=0.9,
                reasoning="High priority ticket with negative sentiment requires escalation",
                priority=100
            ),
            
            # Rule 2: Billing or payment issues
            DecisionRule(
                name="billing_payment_issues",
                condition=lambda ctx: any(
                    cat in ["billing", "pricing"] for cat in ctx["categories"]
                ),
                action=DecisionType.ESCALATE,
                confidence=0.85,
                reasoning="Billing and payment issues require human attention",
                priority=90
            ),
            
            # Rule 3: Technical issues with high urgency
            DecisionRule(
                name="urgent_technical_issues",
                condition=lambda ctx: (
                    "technical" in ctx["categories"] and 
                    ctx["urgency_level"] == "high"
                ),
                action=DecisionType.ESCALATE,
                confidence=0.8,
                reasoning="Urgent technical issues need immediate attention",
                priority=80
            ),
            
            # Rule 4: Multiple categories indicating complex issue
            DecisionRule(
                name="complex_ticket_escalation",
                condition=lambda ctx: len(ctx["categories"]) >= 3,
                action=DecisionType.ESCALATE,
                confidence=0.75,
                reasoning="Complex multi-category ticket requires human review",
                priority=70
            ),
            
            # Rule 5: Standard support requests
            DecisionRule(
                name="standard_support_request",
                condition=lambda ctx: (
                    ctx["priority"] in ["low", "medium"] and 
                    ctx["sentiment_score"] >= 0.4 and
                    len(ctx["categories"]) <= 2
                ),
                action=DecisionType.SCHEDULE_FOLLOWUP,
                confidence=0.7,
                reasoning="Standard support request can be scheduled for follow-up",
                priority=60
            )
        ]
    
    def _initialize_safety_rules(self) -> List[DecisionRule]:
        """Initialize safety and compliance rules"""
        return [
            # Rule 1: Abusive or inappropriate content
            DecisionRule(
                name="abusive_content_escalation",
                condition=lambda ctx: self._contains_abusive_content(ctx),
                action=DecisionType.ESCALATE,
                confidence=0.95,
                reasoning="Abusive or inappropriate content requires human review",
                priority=1000
            ),
            
            # Rule 2: Potential fraud or security issues
            DecisionRule(
                name="fraud_security_escalation",
                condition=lambda ctx: any(
                    keyword in str(ctx.get("content", "")).lower() 
                    for keyword in ["fraud", "hack", "stolen", "unauthorized", "identity theft"]
                ),
                action=DecisionType.ESCALATE,
                confidence=0.98,
                reasoning="Potential fraud or security issue requires immediate escalation",
                priority=999
            )
        ]
    
    def _apply_safety_rules(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply safety rules first - these override all other rules"""
        for rule in sorted(self.safety_rules, key=lambda r: r.priority, reverse=True):
            if rule.condition(context):
                logger.warning(f"Safety rule triggered: {rule.name}")
                return {
                    "decision_type": rule.action,
                    "confidence_score": rule.confidence,
                    "reasoning": rule.reasoning,
                    "rule_name": rule.name,
                    "requires_approval": True,  # Safety rules always require approval
                    "safety_flag": True
                }
        return None
    
    def _contains_abusive_content(self, context: Dict[str, Any]) -> bool:
        """Check for abusive or inappropriate content"""
        content = str(context.get("content", "")).lower()
        
        # Simple keyword-based detection (in production, use more sophisticated methods)
        abusive_keywords = [
            "idiot", "stupid", "moron", "hate you", "kill", "die",
            "racist", "discrimination", "harassment"
        ]
        
        return any(keyword in content for keyword in abusive_keywords)
    
    def _requires_approval(self, action: DecisionType, confidence: float) -> bool:
        """Determine if decision requires human approval"""
        # Low confidence decisions always require approval
        if confidence < 0.6:
            return True
        
        # Certain action types require approval
        approval_required_actions = [
            DecisionType.ESCALATE,
            DecisionType.RECOVER_PRIVATE
        ]
        
        if action in approval_required_actions and confidence < 0.8:
            return True
        
        return False
    
    def _get_default_review_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get default decision when no rules match"""
        # Conservative default: public response for positive, escalate for negative
        if context["rating"] >= 4:
            return {
                "decision_type": DecisionType.RESPOND_PUBLIC,
                "confidence_score": 0.5,
                "reasoning": "Default: Public response for positive review",
                "rule_name": "default_positive",
                "requires_approval": False
            }
        else:
            return {
                "decision_type": DecisionType.ESCALATE,
                "confidence_score": 0.3,
                "reasoning": "Default: Escalate uncertain cases for human review",
                "rule_name": "default_escalate",
                "requires_approval": True
            }
    
    def _get_default_ticket_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get default decision for tickets when no rules match"""
        return {
            "decision_type": DecisionType.ESCALATE,
            "confidence_score": 0.4,
            "reasoning": "Default: Escalate support tickets for human review",
            "rule_name": "default_ticket_escalate",
            "requires_approval": True
        }
    
    def get_rule_summary(self) -> Dict[str, Any]:
        """Get summary of all configured rules"""
        return {
            "review_rules": [
                {
                    "name": rule.name,
                    "action": rule.action.value,
                    "confidence": rule.confidence,
                    "priority": rule.priority,
                    "reasoning": rule.reasoning
                }
                for rule in self.review_rules
            ],
            "ticket_rules": [
                {
                    "name": rule.name,
                    "action": rule.action.value,
                    "confidence": rule.confidence,
                    "priority": rule.priority,
                    "reasoning": rule.reasoning
                }
                for rule in self.ticket_rules
            ],
            "safety_rules": [
                {
                    "name": rule.name,
                    "action": rule.action.value,
                    "confidence": rule.confidence,
                    "priority": rule.priority,
                    "reasoning": rule.reasoning
                }
                for rule in self.safety_rules
            ]
        }
    
    def add_custom_rule(
        self,
        rule_type: str,
        name: str,
        condition: callable,
        action: DecisionType,
        confidence: float,
        reasoning: str,
        priority: int = 0
    ):
        """Add a custom rule to the engine"""
        rule = DecisionRule(
            name=name,
            condition=condition,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            priority=priority
        )
        
        if rule_type == "review":
            self.review_rules.append(rule)
        elif rule_type == "ticket":
            self.ticket_rules.append(rule)
        elif rule_type == "safety":
            self.safety_rules.append(rule)
        else:
            raise ValueError(f"Invalid rule type: {rule_type}")
        
        logger.info(f"Added custom {rule_type} rule: {name}")
