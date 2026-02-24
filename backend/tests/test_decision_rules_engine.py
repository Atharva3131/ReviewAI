"""
Unit tests for decision rules engine
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.services.decision_rules_engine import DecisionRulesEngine, DecisionRule
from app.models.agent_decision import DecisionType


class TestDecisionRulesEngine:
    """Test cases for DecisionRulesEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DecisionRulesEngine()
    
    @pytest.mark.asyncio
    async def test_decide_review_action_critical_negative(self):
        """Test decision for critical negative review"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.1,
            urgency_level="high",
            rating=1,
            categories=["support", "quality"],
            context={"content": "This was terrible service!"}
        )
        
        assert result["decision_type"] == DecisionType.RECOVER_PRIVATE
        assert result["confidence_score"] >= 0.9
        assert result["rule_name"] == "critical_negative_review"
        assert "critical negative review" in result["reasoning"].lower()
        assert result["requires_approval"] == False  # High confidence
    
    @pytest.mark.asyncio
    async def test_decide_review_action_emergency_safety(self):
        """Test decision for emergency/safety issues"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.2,
            urgency_level="high",
            rating=2,
            categories=["safety"],
            context={"content": "This is an emergency! Someone could get injured!"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.95
        assert result["rule_name"] == "emergency_safety_issue"
        assert "emergency" in result["reasoning"].lower()
        assert result["requires_approval"] == False  # High confidence
    
    @pytest.mark.asyncio
    async def test_decide_review_action_legal_threat(self):
        """Test decision for legal threats"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.3,
            urgency_level="medium",
            rating=2,
            categories=["support"],
            context={"content": "I'm going to sue you and contact my lawyer!"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.9
        assert result["rule_name"] == "legal_threat_escalation"
        assert "legal" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_review_action_positive_review(self):
        """Test decision for positive reviews"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.8,
            urgency_level="low",
            rating=5,
            categories=["quality"],
            context={"content": "Excellent service and great food!"}
        )
        
        assert result["decision_type"] == DecisionType.RESPOND_PUBLIC
        assert result["confidence_score"] >= 0.8
        assert result["rule_name"] == "positive_review_response"
        assert "positive review" in result["reasoning"].lower()
        assert result["requires_approval"] == False
    
    @pytest.mark.asyncio
    async def test_decide_review_action_complex_negative(self):
        """Test decision for complex negative issues"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.2,
            urgency_level="medium",
            rating=2,
            categories=["support", "quality", "delivery"],
            context={"content": "Multiple problems with my order"}
        )
        
        assert result["decision_type"] == DecisionType.RECOVER_PRIVATE
        assert result["confidence_score"] >= 0.8
        assert result["rule_name"] == "complex_negative_issues"
        assert "multiple issues" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_review_action_service_quality_issues(self):
        """Test decision for service/quality issues"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.3,
            urgency_level="medium",
            rating=3,
            categories=["support"],
            context={"content": "The service was poor and disappointing"}
        )
        
        assert result["decision_type"] == DecisionType.RECOVER_PRIVATE
        assert result["confidence_score"] >= 0.7
        assert result["rule_name"] == "service_quality_issues"
        assert "service" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_review_action_neutral_constructive(self):
        """Test decision for neutral constructive feedback"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.5,
            urgency_level="low",
            rating=3,
            categories=["feedback"],
            context={"content": "The food was okay, could be improved"}
        )
        
        assert result["decision_type"] == DecisionType.RESPOND_PUBLIC
        assert result["confidence_score"] >= 0.7
        assert result["rule_name"] == "neutral_constructive_feedback"
        assert "constructive feedback" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_review_action_complex_case_escalation(self):
        """Test decision for complex cases requiring escalation"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.4,
            urgency_level="high",
            rating=3,
            categories=["support", "quality", "delivery", "billing"],
            context={"content": "Multiple complex issues"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.5
        assert result["rule_name"] == "complex_case_escalation"
        assert "complex" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_review_action_low_confidence(self):
        """Test decision with low confidence analysis"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.5,
            urgency_level="medium",
            rating=3,
            categories=["support"],
            context={
                "content": "Some feedback",
                "sentiment_confidence": 0.3,
                "urgency_confidence": 0.4
            }
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["rule_name"] == "low_confidence_escalation"
        assert "low confidence" in result["reasoning"].lower()
        assert result["requires_approval"] == True
    
    @pytest.mark.asyncio
    async def test_decide_review_action_moderate_negative(self):
        """Test decision for moderate negative reviews"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.4,
            urgency_level="medium",
            rating=3,
            categories=["quality"],
            context={"content": "The food was not great"}
        )
        
        assert result["decision_type"] == DecisionType.RESPOND_PUBLIC
        assert result["confidence_score"] >= 0.6
        assert result["rule_name"] == "moderate_negative_response"
        assert "moderate negative" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_review_action_default_positive(self):
        """Test default decision for unmatched positive cases"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.7,
            urgency_level="low",
            rating=4,
            categories=[],
            context={"content": "Good experience"}
        )
        
        # Should match positive review rule or default to positive
        assert result["decision_type"] == DecisionType.RESPOND_PUBLIC
        assert result["requires_approval"] == False
    
    @pytest.mark.asyncio
    async def test_decide_review_action_default_negative(self):
        """Test default decision for unmatched negative cases"""
        # Create a case that doesn't match specific rules
        result = await self.engine.decide_review_action(
            sentiment_score=0.6,  # Not very negative
            urgency_level="low",   # Not urgent
            rating=2,             # Negative but not critical
            categories=[],        # No specific categories
            context={"content": "Meh, it was okay I guess"}
        )
        
        # Should default to escalation for safety
        assert result["decision_type"] == DecisionType.ESCALATE
        assert "default" in result["rule_name"].lower()
        assert result["requires_approval"] == True
    
    @pytest.mark.asyncio
    async def test_decide_ticket_action_high_priority_negative(self):
        """Test ticket decision for high priority negative sentiment"""
        result = await self.engine.decide_ticket_action(
            sentiment_score=0.2,
            urgency_level="high",
            priority="high",
            categories=["technical"],
            context={"content": "System is completely broken!"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.8
        assert result["rule_name"] == "high_priority_negative_ticket"
        assert "high priority" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_ticket_action_billing_issues(self):
        """Test ticket decision for billing/payment issues"""
        result = await self.engine.decide_ticket_action(
            sentiment_score=0.5,
            urgency_level="medium",
            priority="medium",
            categories=["billing"],
            context={"content": "I was charged incorrectly"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.8
        assert result["rule_name"] == "billing_payment_issues"
        assert "billing" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_ticket_action_urgent_technical(self):
        """Test ticket decision for urgent technical issues"""
        result = await self.engine.decide_ticket_action(
            sentiment_score=0.4,
            urgency_level="high",
            priority="medium",
            categories=["technical"],
            context={"content": "The system won't work"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.7
        assert result["rule_name"] == "urgent_technical_issues"
        assert "technical" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_ticket_action_complex_ticket(self):
        """Test ticket decision for complex multi-category tickets"""
        result = await self.engine.decide_ticket_action(
            sentiment_score=0.5,
            urgency_level="medium",
            priority="medium",
            categories=["technical", "billing", "support"],
            context={"content": "Multiple issues with my account"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.7
        assert result["rule_name"] == "complex_ticket_escalation"
        assert "complex" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_decide_ticket_action_standard_support(self):
        """Test ticket decision for standard support requests"""
        result = await self.engine.decide_ticket_action(
            sentiment_score=0.6,
            urgency_level="low",
            priority="low",
            categories=["support"],
            context={"content": "I have a question about my account"}
        )
        
        assert result["decision_type"] == DecisionType.SCHEDULE_FOLLOWUP
        assert result["confidence_score"] >= 0.6
        assert result["rule_name"] == "standard_support_request"
        assert "standard support" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_safety_rule_abusive_content(self):
        """Test safety rule for abusive content"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.1,
            urgency_level="high",
            rating=1,
            categories=["complaint"],
            context={"content": "You idiots are stupid and I hate you all!"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.9
        assert result["rule_name"] == "abusive_content_escalation"
        assert "abusive" in result["reasoning"].lower()
        assert result["requires_approval"] == True
        assert result["safety_flag"] == True
    
    @pytest.mark.asyncio
    async def test_safety_rule_fraud_security(self):
        """Test safety rule for fraud/security issues"""
        result = await self.engine.decide_review_action(
            sentiment_score=0.3,
            urgency_level="high",
            rating=2,
            categories=["security"],
            context={"content": "My account was hacked and there's fraud on my card!"}
        )
        
        assert result["decision_type"] == DecisionType.ESCALATE
        assert result["confidence_score"] >= 0.95
        assert result["rule_name"] == "fraud_security_escalation"
        assert "fraud" in result["reasoning"].lower()
        assert result["requires_approval"] == True
        assert result["safety_flag"] == True
    
    def test_contains_abusive_content(self):
        """Test abusive content detection"""
        # Test abusive content
        abusive_context = {"content": "You idiots are stupid morons!"}
        assert self.engine._contains_abusive_content(abusive_context) == True
        
        # Test clean content
        clean_context = {"content": "I'm disappointed with the service"}
        assert self.engine._contains_abusive_content(clean_context) == False
        
        # Test edge cases
        empty_context = {"content": ""}
        assert self.engine._contains_abusive_content(empty_context) == False
        
        no_content_context = {}
        assert self.engine._contains_abusive_content(no_content_context) == False
    
    def test_requires_approval(self):
        """Test approval requirement logic"""
        # Low confidence always requires approval
        assert self.engine._requires_approval(DecisionType.RESPOND_PUBLIC, 0.5) == True
        
        # High confidence public response doesn't require approval
        assert self.engine._requires_approval(DecisionType.RESPOND_PUBLIC, 0.9) == False
        
        # Escalation with medium confidence requires approval
        assert self.engine._requires_approval(DecisionType.ESCALATE, 0.7) == True
        
        # Escalation with high confidence doesn't require approval
        assert self.engine._requires_approval(DecisionType.ESCALATE, 0.9) == False
        
        # Recovery with medium confidence requires approval
        assert self.engine._requires_approval(DecisionType.RECOVER_PRIVATE, 0.7) == True
        
        # Recovery with high confidence doesn't require approval
        assert self.engine._requires_approval(DecisionType.RECOVER_PRIVATE, 0.9) == False
    
    def test_get_rule_summary(self):
        """Test rule summary generation"""
        summary = self.engine.get_rule_summary()
        
        assert "review_rules" in summary
        assert "ticket_rules" in summary
        assert "safety_rules" in summary
        
        # Check review rules
        assert len(summary["review_rules"]) > 0
        for rule in summary["review_rules"]:
            assert "name" in rule
            assert "action" in rule
            assert "confidence" in rule
            assert "priority" in rule
            assert "reasoning" in rule
        
        # Check ticket rules
        assert len(summary["ticket_rules"]) > 0
        for rule in summary["ticket_rules"]:
            assert "name" in rule
            assert "action" in rule
            assert "confidence" in rule
            assert "priority" in rule
            assert "reasoning" in rule
        
        # Check safety rules
        assert len(summary["safety_rules"]) > 0
        for rule in summary["safety_rules"]:
            assert "name" in rule
            assert "action" in rule
            assert "confidence" in rule
            assert "priority" in rule
            assert "reasoning" in rule
    
    def test_add_custom_rule(self):
        """Test adding custom rules"""
        # Add custom review rule
        custom_condition = lambda ctx: ctx["rating"] == 3 and "test" in ctx.get("content", "")
        
        self.engine.add_custom_rule(
            rule_type="review",
            name="test_custom_rule",
            condition=custom_condition,
            action=DecisionType.RESPOND_PUBLIC,
            confidence=0.8,
            reasoning="Custom test rule",
            priority=50
        )
        
        # Check rule was added
        rule_names = [rule.name for rule in self.engine.review_rules]
        assert "test_custom_rule" in rule_names
        
        # Test invalid rule type
        with pytest.raises(ValueError):
            self.engine.add_custom_rule(
                rule_type="invalid",
                name="invalid_rule",
                condition=lambda ctx: True,
                action=DecisionType.RESPOND_PUBLIC,
                confidence=0.8,
                reasoning="Invalid rule"
            )
    
    @pytest.mark.asyncio
    async def test_rule_priority_ordering(self):
        """Test that rules are applied in priority order"""
        # Add a high-priority custom rule that should override others
        high_priority_condition = lambda ctx: ctx["rating"] == 1
        
        self.engine.add_custom_rule(
            rule_type="review",
            name="high_priority_test",
            condition=high_priority_condition,
            action=DecisionType.SCHEDULE_FOLLOWUP,  # Different from normal action
            confidence=0.9,
            reasoning="High priority test rule",
            priority=200  # Higher than existing rules
        )
        
        result = await self.engine.decide_review_action(
            sentiment_score=0.1,
            urgency_level="high",
            rating=1,
            categories=["support"],
            context={"content": "Test content"}
        )
        
        # Should use the high-priority custom rule
        assert result["rule_name"] == "high_priority_test"
        assert result["decision_type"] == DecisionType.SCHEDULE_FOLLOWUP
    
    @pytest.mark.asyncio
    async def test_decision_consistency(self):
        """Test that decisions are consistent for same input"""
        context = {
            "sentiment_score": 0.3,
            "urgency_level": "medium",
            "rating": 2,
            "categories": ["support"],
            "content": "I'm not happy with the service"
        }
        
        result1 = await self.engine.decide_review_action(**context)
        result2 = await self.engine.decide_review_action(**context)
        
        # Results should be identical (deterministic)
        assert result1["decision_type"] == result2["decision_type"]
        assert result1["confidence_score"] == result2["confidence_score"]
        assert result1["rule_name"] == result2["rule_name"]
        assert result1["reasoning"] == result2["reasoning"]
        assert result1["requires_approval"] == result2["requires_approval"]
    
    @pytest.mark.asyncio
    async def test_edge_case_handling(self):
        """Test handling of edge cases and invalid inputs"""
        # Test with missing context
        result = await self.engine.decide_review_action(
            sentiment_score=0.5,
            urgency_level="medium",
            rating=3,
            categories=[],
            context={}
        )
        
        assert "decision_type" in result
        assert "confidence_score" in result
        assert "rule_name" in result
        assert "reasoning" in result
        assert "requires_approval" in result
        
        # Test with extreme values
        result = await self.engine.decide_review_action(
            sentiment_score=1.5,  # Invalid but should be handled
            urgency_level="extreme",  # Invalid but should be handled
            rating=10,  # Invalid but should be handled
            categories=["unknown"],
            context={"content": "Test"}
        )
        
        assert "decision_type" in result
        assert isinstance(result["confidence_score"], (int, float))
        assert 0.0 <= result["confidence_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_comprehensive_rule_coverage(self):
        """Test that all major scenarios have appropriate rule coverage"""
        test_scenarios = [
            # Critical cases
            {"sentiment_score": 0.1, "urgency_level": "high", "rating": 1, "categories": ["safety"]},
            {"sentiment_score": 0.2, "urgency_level": "high", "rating": 2, "categories": ["support"]},
            
            # Positive cases
            {"sentiment_score": 0.8, "urgency_level": "low", "rating": 5, "categories": ["quality"]},
            {"sentiment_score": 0.7, "urgency_level": "low", "rating": 4, "categories": ["service"]},
            
            # Neutral cases
            {"sentiment_score": 0.5, "urgency_level": "medium", "rating": 3, "categories": ["feedback"]},
            
            # Complex cases
            {"sentiment_score": 0.2, "urgency_level": "high", "rating": 2, "categories": ["support", "quality", "delivery"]},
        ]
        
        for scenario in test_scenarios:
            result = await self.engine.decide_review_action(
                **scenario,
                context={"content": "Test scenario"}
            )
            
            # All scenarios should produce valid decisions
            assert result["decision_type"] in [dt.value for dt in DecisionType]
            assert 0.0 <= result["confidence_score"] <= 1.0
            assert len(result["reasoning"]) > 0
            assert isinstance(result["requires_approval"], bool)