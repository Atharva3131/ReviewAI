"""
Property-based tests for decision rule determinism
**Validates: Requirements 5.2**
"""
import pytest
import asyncio
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from typing import Dict, Any, List

from app.services.decision_rules_engine import DecisionRulesEngine
from app.models.agent_decision import DecisionType


class TestDecisionRuleDeterminism:
    """Property-based tests for decision rule determinism"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DecisionRulesEngine()
    
    @given(
        st.floats(min_value=0.0, max_value=1.0),  # sentiment_score
        st.sampled_from(['low', 'medium', 'high']),  # urgency_level
        st.integers(min_value=1, max_value=5),  # rating
        st.lists(st.sampled_from(['support', 'quality', 'delivery', 'pricing', 'technical']), min_size=0, max_size=3)  # categories
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_review_decision_determinism_property(self, sentiment_score: float, urgency_level: str, rating: int, categories: List[str]):
        """
        Property: Same inputs should always produce identical decisions (determinism)
        **Validates: Requirements 5.2.1**
        """
        context = {"content": "Test review content"}
        
        result1 = asyncio.run(self.engine.decide_review_action(
            sentiment_score, urgency_level, rating, categories, context
        ))
        result2 = asyncio.run(self.engine.decide_review_action(
            sentiment_score, urgency_level, rating, categories, context
        ))
        
        # Property: Results should be identical
        assert result1["decision_type"] == result2["decision_type"], f"Non-deterministic decision type for inputs: {sentiment_score}, {urgency_level}, {rating}, {categories}"
        assert result1["confidence_score"] == result2["confidence_score"], f"Non-deterministic confidence for inputs: {sentiment_score}, {urgency_level}, {rating}, {categories}"
        assert result1["reasoning"] == result2["reasoning"], f"Non-deterministic reasoning for inputs: {sentiment_score}, {urgency_level}, {rating}, {categories}"
        assert result1["rule_name"] == result2["rule_name"], f"Non-deterministic rule name for inputs: {sentiment_score}, {urgency_level}, {rating}, {categories}"
        assert result1["requires_approval"] == result2["requires_approval"], f"Non-deterministic approval requirement for inputs: {sentiment_score}, {urgency_level}, {rating}, {categories}"
    
    @given(
        st.floats(min_value=0.0, max_value=1.0),  # sentiment_score
        st.sampled_from(['low', 'medium', 'high']),  # urgency_level
        st.sampled_from(['low', 'medium', 'high']),  # priority
        st.lists(st.sampled_from(['support', 'quality', 'delivery', 'pricing', 'technical', 'billing']), min_size=0, max_size=3)  # categories
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_ticket_decision_determinism_property(self, sentiment_score: float, urgency_level: str, priority: str, categories: List[str]):
        """
        Property: Ticket decisions should be deterministic
        **Validates: Requirements 5.2.1**
        """
        context = {"content": "Test ticket content"}
        
        result1 = asyncio.run(self.engine.decide_ticket_action(
            sentiment_score, urgency_level, priority, categories, context
        ))
        result2 = asyncio.run(self.engine.decide_ticket_action(
            sentiment_score, urgency_level, priority, categories, context
        ))
        
        # Property: Results should be identical
        assert result1["decision_type"] == result2["decision_type"], f"Non-deterministic ticket decision for inputs: {sentiment_score}, {urgency_level}, {priority}, {categories}"
        assert result1["confidence_score"] == result2["confidence_score"], f"Non-deterministic ticket confidence for inputs: {sentiment_score}, {urgency_level}, {priority}, {categories}"
        assert result1["reasoning"] == result2["reasoning"], f"Non-deterministic ticket reasoning for inputs: {sentiment_score}, {urgency_level}, {priority}, {categories}"
    
    @given(st.integers(min_value=1, max_value=2))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_critical_negative_review_rule_property(self, rating: int):
        """
        Property: Critical negative reviews should trigger recovery actions
        **Validates: Requirements 5.2.1**
        """
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.1,  # Very negative
            urgency_level='high',
            rating=rating,
            categories=['support'],
            context={"content": "Terrible service"}
        ))
        
        # Property: Should trigger recovery action
        assert result["decision_type"] == DecisionType.RECOVER_PRIVATE, f"Critical negative review should trigger private recovery, got {result['decision_type']}"
        assert result["confidence_score"] >= 0.8, f"Critical negative review should have high confidence, got {result['confidence_score']}"
        assert result["requires_approval"] == True, "Critical negative review should require approval"
    
    @given(st.integers(min_value=4, max_value=5))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_positive_review_rule_property(self, rating: int):
        """
        Property: Positive reviews should trigger public responses
        **Validates: Requirements 5.2.3**
        """
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.8,  # Very positive
            urgency_level='low',
            rating=rating,
            categories=[],
            context={"content": "Great service"}
        ))
        
        # Property: Should trigger public response
        assert result["decision_type"] == DecisionType.RESPOND_PUBLIC, f"Positive review should trigger public response, got {result['decision_type']}"
        assert result["confidence_score"] >= 0.7, f"Positive review should have good confidence, got {result['confidence_score']}"
    
    @given(st.text(min_size=1, max_size=200))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_safety_rule_consistency_property(self, content: str):
        """
        Property: Safety rules should be consistently applied
        **Validates: Requirements 5.2.4**
        """
        assume(content.strip())
        
        # Test with potentially abusive content
        abusive_keywords = ["idiot", "stupid", "hate you"]
        
        for keyword in abusive_keywords:
            test_content = f"{content} {keyword}"
            
            result = asyncio.run(self.engine.decide_review_action(
                sentiment_score=0.5,
                urgency_level='medium',
                rating=3,
                categories=['support'],
                context={"content": test_content}
            ))
            
            # Property: Abusive content should be escalated
            if keyword in test_content.lower():
                assert result["decision_type"] == DecisionType.ESCALATE, f"Abusive content should be escalated, got {result['decision_type']}"
                assert result.get("safety_flag") == True, "Safety rule should set safety flag"
                assert result["requires_approval"] == True, "Safety issues should require approval"
    
    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.sampled_from(['low', 'medium', 'high']),
        st.integers(min_value=1, max_value=5)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_decision_confidence_bounds_property(self, sentiment_score: float, urgency_level: str, rating: int):
        """
        Property: Decision confidence should always be within bounds
        **Validates: Requirements 5.2**
        """
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=sentiment_score,
            urgency_level=urgency_level,
            rating=rating,
            categories=['support'],
            context={"content": "Test content"}
        ))
        
        # Property: Confidence should be bounded
        assert 0.0 <= result["confidence_score"] <= 1.0, f"Confidence {result['confidence_score']} out of bounds"
        assert isinstance(result["confidence_score"], float), f"Confidence should be float, got {type(result['confidence_score'])}"
    
    @given(
        st.lists(st.sampled_from(['support', 'quality', 'delivery', 'pricing', 'technical']), min_size=3, max_size=5)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_complex_case_escalation_property(self, categories: List[str]):
        """
        Property: Complex cases with multiple categories should be escalated
        **Validates: Requirements 5.2.4**
        """
        # Remove duplicates while preserving order
        unique_categories = list(dict.fromkeys(categories))
        
        if len(unique_categories) >= 3:
            result = asyncio.run(self.engine.decide_review_action(
                sentiment_score=0.4,
                urgency_level='high',
                rating=2,
                categories=unique_categories,
                context={"content": "Complex multi-issue case"}
            ))
            
            # Property: Complex cases should be escalated
            assert result["decision_type"] == DecisionType.ESCALATE, f"Complex case should be escalated, got {result['decision_type']}"
    
    @given(
        st.floats(min_value=0.0, max_value=0.5),  # Low confidence values
        st.floats(min_value=0.0, max_value=0.5)   # Low confidence values
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_low_confidence_escalation_property(self, sentiment_confidence: float, urgency_confidence: float):
        """
        Property: Low confidence in analysis should trigger escalation
        **Validates: Requirements 5.2.4**
        """
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.5,
            urgency_level='medium',
            rating=3,
            categories=['support'],
            context={
                "content": "Uncertain case",
                "sentiment_confidence": sentiment_confidence,
                "urgency_confidence": urgency_confidence
            }
        ))
        
        # Property: Low confidence should trigger escalation
        assert result["decision_type"] == DecisionType.ESCALATE, f"Low confidence should trigger escalation, got {result['decision_type']}"
        assert result["requires_approval"] == True, "Low confidence cases should require approval"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_legal_threat_escalation_property(self, base_content: str):
        """
        Property: Legal threats should always be escalated
        **Validates: Requirements 5.2.4**
        """
        assume(base_content.strip())
        
        legal_keywords = ["lawyer", "sue", "legal action", "attorney", "court"]
        
        for keyword in legal_keywords:
            content = f"{base_content} I will contact my {keyword}"
            
            result = asyncio.run(self.engine.decide_review_action(
                sentiment_score=0.3,
                urgency_level='medium',
                rating=2,
                categories=['support'],
                context={"content": content}
            ))
            
            # Property: Legal threats should be escalated
            assert result["decision_type"] == DecisionType.ESCALATE, f"Legal threat should be escalated, got {result['decision_type']}"
            assert result["confidence_score"] >= 0.8, f"Legal threat should have high confidence, got {result['confidence_score']}"
    
    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.sampled_from(['low', 'medium', 'high']),
        st.integers(min_value=1, max_value=5)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_decision_structure_property(self, sentiment_score: float, urgency_level: str, rating: int):
        """
        Property: All decisions should have required structure and valid values
        **Validates: Requirements 5.2**
        """
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=sentiment_score,
            urgency_level=urgency_level,
            rating=rating,
            categories=['support'],
            context={"content": "Test content"}
        ))
        
        # Property: Should have all required fields
        required_fields = ["decision_type", "confidence_score", "reasoning", "rule_name", "requires_approval"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Property: Decision type should be valid
        valid_decision_types = [dt for dt in DecisionType]
        assert result["decision_type"] in valid_decision_types, f"Invalid decision type: {result['decision_type']}"
        
        # Property: Reasoning should be non-empty string
        assert isinstance(result["reasoning"], str), f"Reasoning should be string, got {type(result['reasoning'])}"
        assert len(result["reasoning"]) > 0, "Reasoning should not be empty"
        
        # Property: Rule name should be non-empty string
        assert isinstance(result["rule_name"], str), f"Rule name should be string, got {type(result['rule_name'])}"
        assert len(result["rule_name"]) > 0, "Rule name should not be empty"
        
        # Property: Requires approval should be boolean
        assert isinstance(result["requires_approval"], bool), f"Requires approval should be boolean, got {type(result['requires_approval'])}"


class TestDecisionRulesStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for decision rules engine
    **Validates: Requirements 5.2**
    """
    
    def __init__(self):
        super().__init__()
        self.engine = DecisionRulesEngine()
        self.decision_history = []
        self.rule_usage_count = {}
    
    @rule(
        sentiment_score=st.floats(min_value=0.0, max_value=1.0),
        urgency_level=st.sampled_from(['low', 'medium', 'high']),
        rating=st.integers(min_value=1, max_value=5),
        categories=st.lists(st.sampled_from(['support', 'quality', 'delivery', 'pricing']), min_size=0, max_size=3)
    )
    def make_review_decision(self, sentiment_score: float, urgency_level: str, rating: int, categories: List[str]):
        """Rule: Make a review decision"""
        context = {"content": f"Test review with sentiment {sentiment_score}"}
        
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score, urgency_level, rating, categories, context
        ))
        
        # Track decision history
        decision_key = (sentiment_score, urgency_level, rating, tuple(categories))
        self.decision_history.append((decision_key, result))
        
        # Track rule usage
        rule_name = result["rule_name"]
        self.rule_usage_count[rule_name] = self.rule_usage_count.get(rule_name, 0) + 1
    
    @rule(
        sentiment_score=st.floats(min_value=0.0, max_value=1.0),
        urgency_level=st.sampled_from(['low', 'medium', 'high']),
        priority=st.sampled_from(['low', 'medium', 'high']),
        categories=st.lists(st.sampled_from(['support', 'technical', 'billing']), min_size=0, max_size=3)
    )
    def make_ticket_decision(self, sentiment_score: float, urgency_level: str, priority: str, categories: List[str]):
        """Rule: Make a ticket decision"""
        context = {"content": f"Test ticket with sentiment {sentiment_score}"}
        
        result = asyncio.run(self.engine.decide_ticket_action(
            sentiment_score, urgency_level, priority, categories, context
        ))
        
        # Track decision history
        decision_key = (sentiment_score, urgency_level, priority, tuple(categories))
        self.decision_history.append((decision_key, result))
        
        # Track rule usage
        rule_name = result["rule_name"]
        self.rule_usage_count[rule_name] = self.rule_usage_count.get(rule_name, 0) + 1
    
    @rule()
    def verify_previous_decision_consistency(self):
        """Rule: Verify that re-making a previous decision gives same result"""
        if len(self.decision_history) < 2:
            return
        
        # Pick a previous decision to re-verify
        decision_key, original_result = self.decision_history[-1]
        
        if len(decision_key) == 4:  # Review decision
            sentiment_score, urgency_level, rating, categories = decision_key
            new_result = asyncio.run(self.engine.decide_review_action(
                sentiment_score, urgency_level, rating, list(categories), 
                {"content": f"Test review with sentiment {sentiment_score}"}
            ))
        else:  # Ticket decision
            sentiment_score, urgency_level, priority, categories = decision_key
            new_result = asyncio.run(self.engine.decide_ticket_action(
                sentiment_score, urgency_level, priority, list(categories),
                {"content": f"Test ticket with sentiment {sentiment_score}"}
            ))
        
        # Verify consistency
        assert new_result["decision_type"] == original_result["decision_type"]
        assert new_result["confidence_score"] == original_result["confidence_score"]
        assert new_result["rule_name"] == original_result["rule_name"]
    
    @invariant()
    def all_decisions_are_valid(self):
        """Invariant: All decisions should be valid"""
        for decision_key, result in self.decision_history:
            assert "decision_type" in result
            assert "confidence_score" in result
            assert "reasoning" in result
            assert "rule_name" in result
            assert "requires_approval" in result
            
            assert 0.0 <= result["confidence_score"] <= 1.0
            assert isinstance(result["reasoning"], str)
            assert len(result["reasoning"]) > 0
            assert isinstance(result["requires_approval"], bool)
    
    @invariant()
    def rule_usage_is_reasonable(self):
        """Invariant: Rule usage should be reasonable"""
        total_decisions = len(self.decision_history)
        if total_decisions > 10:
            # Should not have all decisions using the same rule (unless by design)
            max_usage = max(self.rule_usage_count.values()) if self.rule_usage_count else 0
            assert max_usage < total_decisions * 0.8, "Rule usage too concentrated"
    
    @invariant()
    def safety_rules_take_precedence(self):
        """Invariant: Safety rules should take precedence when triggered"""
        for decision_key, result in self.decision_history:
            if result.get("safety_flag"):
                assert result["decision_type"] == DecisionType.ESCALATE
                assert result["requires_approval"] == True


class TestDecisionRuleEdgeCases:
    """Property-based tests for edge cases in decision rules"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DecisionRulesEngine()
    
    @given(st.text(alphabet=' \\t\\n\\r', min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_content_property(self, content: str):
        """
        Property: Whitespace-only content should be handled gracefully
        **Validates: Requirements 5.2**
        """
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.5,
            urgency_level='medium',
            rating=3,
            categories=['support'],
            context={"content": content}
        ))
        
        # Property: Should return valid decision
        assert "decision_type" in result
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert isinstance(result["reasoning"], str)
    
    @given(st.lists(st.text(min_size=0, max_size=5), min_size=0, max_size=10))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_empty_categories_property(self, categories: List[str]):
        """
        Property: Empty or invalid categories should be handled gracefully
        **Validates: Requirements 5.2**
        """
        # Filter out empty categories
        valid_categories = [cat for cat in categories if cat.strip()]
        
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.5,
            urgency_level='medium',
            rating=3,
            categories=valid_categories,
            context={"content": "Test content"}
        ))
        
        # Property: Should return valid decision regardless of categories
        assert "decision_type" in result
        assert 0.0 <= result["confidence_score"] <= 1.0
    
    @given(
        st.floats(min_value=-1.0, max_value=2.0),  # Include out-of-bounds values
        st.text(min_size=1, max_size=20),  # Invalid urgency levels
        st.integers(min_value=0, max_value=10)  # Invalid ratings
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_input_handling_property(self, sentiment_score: float, urgency_level: str, rating: int):
        """
        Property: Invalid inputs should be handled gracefully
        **Validates: Requirements 5.2**
        """
        # Should not raise an exception even with invalid inputs
        try:
            result = asyncio.run(self.engine.decide_review_action(
                sentiment_score=sentiment_score,
                urgency_level=urgency_level,
                rating=rating,
                categories=['support'],
                context={"content": "Test content"}
            ))
            
            # If it doesn't raise an exception, result should be valid
            assert "decision_type" in result
            assert isinstance(result["confidence_score"], (int, float))
            assert isinstance(result["reasoning"], str)
            
        except (ValueError, TypeError, KeyError):
            # It's acceptable to raise exceptions for clearly invalid inputs
            pass
    
    @given(st.dictionaries(st.text(min_size=1, max_size=10), st.text(min_size=0, max_size=50), min_size=0, max_size=5))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_arbitrary_context_property(self, context: Dict[str, str]):
        """
        Property: Arbitrary context data should not break decision making
        **Validates: Requirements 5.2**
        """
        # Add required content field
        context["content"] = "Test content"
        
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.5,
            urgency_level='medium',
            rating=3,
            categories=['support'],
            context=context
        ))
        
        # Property: Should return valid decision regardless of extra context
        assert "decision_type" in result
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert isinstance(result["reasoning"], str)


# Test runner for stateful testing
TestDecisionRulesStateMachine = TestDecisionRulesStateMachine.TestCase


class TestDecisionRulePerformance:
    """Property-based tests for decision rule performance"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DecisionRulesEngine()
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=5)
    def test_batch_decision_performance_property(self, batch_size: int):
        """
        Property: Decision making should scale reasonably with batch size
        **Validates: Requirements 5.2**
        """
        import time
        
        decisions = []
        start_time = time.time()
        
        for i in range(batch_size):
            result = asyncio.run(self.engine.decide_review_action(
                sentiment_score=0.5,
                urgency_level='medium',
                rating=3,
                categories=['support'],
                context={"content": f"Test content {i}"}
            ))
            decisions.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Property: Should complete in reasonable time (less than 0.1 seconds per decision)
        assert processing_time < batch_size * 0.1, f"Decision making too slow: {processing_time}s for {batch_size} decisions"
        
        # Property: Should return correct number of decisions
        assert len(decisions) == batch_size
        
        # Property: All decisions should be valid
        for decision in decisions:
            assert "decision_type" in decision
            assert 0.0 <= decision["confidence_score"] <= 1.0
    
    @given(st.text(min_size=1, max_size=10000))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=3)
    def test_large_content_handling_property(self, content: str):
        """
        Property: Should handle large content efficiently
        **Validates: Requirements 5.2**
        """
        assume(content.strip())
        
        import time
        start_time = time.time()
        
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.5,
            urgency_level='medium',
            rating=3,
            categories=['support'],
            context={"content": content}
        ))
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Property: Should complete in reasonable time (less than 2 seconds)
        assert processing_time < 2.0, f"Large content processing too slow: {processing_time}s"
        
        # Property: Should return valid result regardless of content size
        assert "decision_type" in result
        assert 0.0 <= result["confidence_score"] <= 1.0


# Helper functions for generating realistic test data
def generate_emergency_content():
    """Strategy for generating emergency-related content"""
    emergency_words = ['emergency', 'urgent', 'help', 'danger', 'unsafe', 'injury', 'sick']
    return st.text(
        alphabet=st.sampled_from(emergency_words + [' ', '.', '!', 'need', 'immediate']),
        min_size=10,
        max_size=100
    )


def generate_legal_threat_content():
    """Strategy for generating legal threat content"""
    legal_words = ['lawyer', 'sue', 'legal action', 'attorney', 'court', 'lawsuit']
    return st.text(
        alphabet=st.sampled_from(legal_words + [' ', '.', '!', 'will', 'contact', 'my']),
        min_size=10,
        max_size=100
    )


class TestDecisionRulesRealisticScenarios:
    """Property-based tests using realistic scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DecisionRulesEngine()
    
    @given(generate_emergency_content())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_emergency_scenario_property(self, content: str):
        """
        Property: Emergency content should trigger appropriate escalation
        **Validates: Requirements 5.2.2**
        """
        assume(content.strip())
        
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.2,  # Negative sentiment
            urgency_level='high',
            rating=1,
            categories=['support'],
            context={"content": content}
        ))
        
        # Property: Emergency content should be escalated
        assert result["decision_type"] == DecisionType.ESCALATE, f"Emergency content should be escalated, got {result['decision_type']}"
        assert result["confidence_score"] >= 0.8, f"Emergency escalation should have high confidence, got {result['confidence_score']}"
    
    @given(generate_legal_threat_content())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_legal_threat_scenario_property(self, content: str):
        """
        Property: Legal threat content should trigger escalation
        **Validates: Requirements 5.2.4**
        """
        assume(content.strip())
        
        result = asyncio.run(self.engine.decide_review_action(
            sentiment_score=0.3,
            urgency_level='medium',
            rating=2,
            categories=['support'],
            context={"content": content}
        ))
        
        # Property: Legal threats should be escalated
        assert result["decision_type"] == DecisionType.ESCALATE, f"Legal threat should be escalated, got {result['decision_type']}"
        assert result["confidence_score"] >= 0.8, f"Legal threat should have high confidence, got {result['confidence_score']}"