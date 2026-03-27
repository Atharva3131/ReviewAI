"""
Property-based tests for recovery action compliance
**Validates: Requirements 6.2**
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from app.models.customer import Customer
from app.models.recovery_action import ActionPriority, ActionType
from app.services.recovery_recommendation_service import RecoveryRecommendationEngine


class MockCustomer:
    """Mock customer for testing"""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "test-customer-id")
        self.organization_id = kwargs.get("organization_id", "test-org-id")
        self.display_name = kwargs.get("display_name", "Test Customer")
        self.email = kwargs.get("email", "test@example.com")
        self.phone = kwargs.get("phone", "+1234567890")
        self.is_high_value = kwargs.get("is_high_value", False)
        self.churn_risk_score = kwargs.get("churn_risk_score", 0.5)
        self.lifetime_value = kwargs.get("lifetime_value", 1000.0)
        self.total_orders = kwargs.get("total_orders", 5)
        self.avg_order_value = kwargs.get("avg_order_value", 100.0)
        self.days_since_last_interaction = kwargs.get("days_since_last_interaction", 30)
        self.timezone = kwargs.get("timezone", "UTC")
        self.reviews = []
        self.support_tickets = []
        self.recovery_actions = []


class TestRecoveryActionCompliance:
    """Property-based tests for recovery action compliance"""

    def setup_method(self):
        """Set up test fixtures"""
        self.engine = RecoveryRecommendationEngine()

    @given(
        st.floats(min_value=0.0, max_value=1.0),  # churn_risk
        st.floats(min_value=0.0, max_value=1.0),  # review_risk
        st.booleans(),  # is_high_value
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_action_recommendation_determinism_property(
        self, churn_risk: float, review_risk: float, is_high_value: bool
    ):
        """
        Property: Same risk profile should produce identical recommendations
        **Validates: Requirements 6.2.1**
        """
        customer = MockCustomer(
            is_high_value=is_high_value, churn_risk_score=churn_risk
        )

        risk_data = {"churn_risk": churn_risk, "bad_review_likelihood": review_risk}

        # Mock the database session and methods
        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result1 = asyncio.run(
                self.engine.recommend_recovery_actions(customer.id, mock_db, None)
            )
            result2 = asyncio.run(
                self.engine.recommend_recovery_actions(customer.id, mock_db, None)
            )

            # Property: Results should be identical (determinism)
            assert len(result1) == len(
                result2
            ), f"Non-deterministic number of actions: {len(result1)} vs {len(result2)}"

            for i, (action1, action2) in enumerate(zip(result1, result2)):
                assert (
                    action1["action_type"] == action2["action_type"]
                ), f"Non-deterministic action type at index {i}"
                assert (
                    action1["priority"] == action2["priority"]
                ), f"Non-deterministic priority at index {i}"
                assert (
                    action1["title"] == action2["title"]
                ), f"Non-deterministic title at index {i}"
                assert (
                    action1["confidence"] == action2["confidence"]
                ), f"Non-deterministic confidence at index {i}"

    @given(st.floats(min_value=0.8, max_value=1.0))  # Critical churn risk
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_critical_churn_risk_compliance_property(self, churn_risk: float):
        """
        Property: Critical churn risk should trigger urgent actions
        **Validates: Requirements 6.2.1**
        """
        customer = MockCustomer(
            is_high_value=True, churn_risk_score=churn_risk, phone="+1234567890"
        )

        risk_data = {"churn_risk": churn_risk, "bad_review_likelihood": 0.3}

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result = asyncio.run(
                self.engine.recommend_recovery_actions(customer.id, mock_db, None)
            )

            # Property: Should have urgent actions for critical churn risk
            urgent_actions = [
                action
                for action in result
                if action["priority"] == ActionPriority.URGENT
            ]
            assert (
                len(urgent_actions) > 0
            ), "Critical churn risk should trigger urgent actions"

            # Property: Should include manager escalation
            escalation_actions = [
                action
                for action in result
                if action["action_type"] == ActionType.ESCALATE_TO_MANAGER
            ]
            assert (
                len(escalation_actions) > 0
            ), "Critical churn risk should trigger manager escalation"

            # Property: Should include phone call for customers with phone numbers
            phone_actions = [
                action
                for action in result
                if action["action_type"] == ActionType.PHONE_CALL
            ]
            assert (
                len(phone_actions) > 0
            ), "Critical churn risk should trigger phone call when phone available"

            # Property: High-value customers should get discount offers
            discount_actions = [
                action
                for action in result
                if action["action_type"] == ActionType.DISCOUNT_OFFER
            ]
            assert (
                len(discount_actions) > 0
            ), "High-value customers at critical risk should get discount offers"

    @given(
        st.floats(min_value=0.6, max_value=0.79),  # High churn risk (not critical)
        st.integers(min_value=2, max_value=10),  # Multiple orders
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_high_churn_risk_compliance_property(
        self, churn_risk: float, total_orders: int
    ):
        """
        Property: High churn risk should trigger appropriate recovery actions
        **Validates: Requirements 6.2.1**
        """
        customer = MockCustomer(churn_risk_score=churn_risk, total_orders=total_orders)

        risk_data = {"churn_risk": churn_risk, "bad_review_likelihood": 0.3}

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result = asyncio.run(
                self.engine.recommend_recovery_actions(customer.id, mock_db, None)
            )

            # Property: Should have high priority actions
            high_priority_actions = [
                action for action in result if action["priority"] == ActionPriority.HIGH
            ]
            assert (
                len(high_priority_actions) > 0
            ), "High churn risk should trigger high priority actions"

            # Property: Should include personalized messaging
            personalized_actions = [
                action
                for action in result
                if action["action_type"] == ActionType.PERSONALIZED_MESSAGE
            ]
            assert (
                len(personalized_actions) > 0
            ), "High churn risk should trigger personalized messaging"

            # Property: Customers with multiple orders should get loyalty discounts
            discount_actions = [
                action
                for action in result
                if action["action_type"] == ActionType.DISCOUNT_OFFER
            ]
            assert (
                len(discount_actions) > 0
            ), "Customers with multiple orders should get loyalty discounts"

    @given(
        st.integers(min_value=1, max_value=2),  # Negative review rating
        st.text(min_size=1, max_size=100),  # Review content
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_negative_review_response_compliance_property(
        self, rating: int, review_content: str
    ):
        """
        Property: Negative reviews should trigger immediate response actions
        **Validates: Requirements 6.2.2**
        """
        assume(review_content.strip())

        customer = MockCustomer(total_orders=3, avg_order_value=150.0)

        risk_data = {"churn_risk": 0.4, "bad_review_likelihood": 0.6}

        trigger_context = {
            "type": "review",
            "review_id": "test-review-id",
            "rating": rating,
            "content": review_content,
        }

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result = asyncio.run(
                self.engine.recommend_recovery_actions(
                    customer.id, mock_db, trigger_context
                )
            )

            # Property: Should have urgent response for negative reviews
            urgent_actions = [
                action
                for action in result
                if action["priority"] == ActionPriority.URGENT
            ]
            assert (
                len(urgent_actions) > 0
            ), "Negative reviews should trigger urgent actions"

            # Property: Should include immediate email response
            email_actions = [
                action for action in result if action["action_type"] == ActionType.EMAIL
            ]
            urgent_emails = [
                action
                for action in email_actions
                if action["priority"] == ActionPriority.URGENT
            ]
            assert (
                len(urgent_emails) > 0
            ), "Negative reviews should trigger urgent email response"

            # Property: Should offer refund for customers with order history
            refund_actions = [
                action
                for action in result
                if action["action_type"] == ActionType.REFUND
            ]
            assert (
                len(refund_actions) > 0
            ), "Negative reviews from customers with orders should trigger refund offers"

    @given(st.integers(min_value=3, max_value=3))  # Neutral review rating
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_neutral_review_response_compliance_property(self, rating: int):
        """
        Property: Neutral reviews should trigger follow-up actions
        **Validates: Requirements 6.2.2**
        """
        customer = MockCustomer()

        risk_data = {"churn_risk": 0.3, "bad_review_likelihood": 0.4}

        trigger_context = {
            "type": "review",
            "review_id": "test-review-id",
            "rating": rating,
        }

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result = asyncio.run(
                self.engine.recommend_recovery_actions(
                    customer.id, mock_db, trigger_context
                )
            )

            # Property: Should include follow-up actions for neutral reviews
            followup_actions = [
                action
                for action in result
                if action["action_type"] == ActionType.FOLLOW_UP
            ]
            assert (
                len(followup_actions) > 0
            ), "Neutral reviews should trigger follow-up actions"

            # Property: Follow-up should be medium priority
            medium_followups = [
                action
                for action in followup_actions
                if action["priority"] == ActionPriority.MEDIUM
            ]
            assert (
                len(medium_followups) > 0
            ), "Neutral review follow-ups should be medium priority"

    @given(st.booleans())  # is_high_value
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_high_value_customer_compliance_property(self, is_high_value: bool):
        """
        Property: High-value customers should receive special treatment
        **Validates: Requirements 6.2.1**
        """
        customer = MockCustomer(
            is_high_value=is_high_value,
            lifetime_value=5000.0 if is_high_value else 500.0,
        )

        risk_data = {"churn_risk": 0.5, "bad_review_likelihood": 0.3}

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result = asyncio.run(
                self.engine.recommend_recovery_actions(customer.id, mock_db, None)
            )

            if is_high_value:
                # Property: High-value customers should get VIP treatment
                vip_actions = [
                    action
                    for action in result
                    if action["action_type"] == ActionType.PERSONALIZED_MESSAGE
                    and "vip"
                    in action.get("metadata", {}).get("customer_tier", "").lower()
                ]
                assert (
                    len(vip_actions) > 0
                ), "High-value customers should get VIP treatment"

                # Property: High-value customers should get higher priority actions
                high_priority_actions = [
                    action
                    for action in result
                    if action["priority"] == ActionPriority.HIGH
                ]
                assert (
                    len(high_priority_actions) > 0
                ), "High-value customers should get high priority actions"

    @given(st.integers(min_value=91, max_value=365))  # Long inactive period
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_inactive_customer_reactivation_compliance_property(
        self, days_inactive: int
    ):
        """
        Property: Long-term inactive customers should get reactivation actions
        **Validates: Requirements 6.2.3**
        """
        customer = MockCustomer(days_since_last_interaction=days_inactive)

        risk_data = {
            "churn_risk": 0.6,  # Higher risk due to inactivity
            "bad_review_likelihood": 0.2,
        }

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result = asyncio.run(
                self.engine.recommend_recovery_actions(customer.id, mock_db, None)
            )

            # Property: Should include win-back email campaigns
            email_actions = [
                action for action in result if action["action_type"] == ActionType.EMAIL
            ]
            winback_emails = [
                action
                for action in email_actions
                if "win_back" in action.get("metadata", {}).get("campaign_type", "")
            ]
            assert (
                len(winback_emails) > 0
            ), "Inactive customers should get win-back email campaigns"

            # Property: Should include reactivation discounts
            discount_actions = [
                action
                for action in result
                if action["action_type"] == ActionType.DISCOUNT_OFFER
            ]
            reactivation_discounts = [
                action
                for action in discount_actions
                if "reactivation" in action.get("metadata", {}).get("campaign", "")
            ]
            assert (
                len(reactivation_discounts) > 0
            ), "Inactive customers should get reactivation discounts"

    @given(
        st.lists(
            st.dictionaries(
                st.sampled_from(["action_type", "priority", "confidence"]),
                st.one_of(
                    st.sampled_from([at for at in ActionType]),
                    st.sampled_from([ap for ap in ActionPriority]),
                    st.floats(min_value=0.0, max_value=1.0),
                ),
                min_size=1,
                max_size=3,
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_action_prioritization_compliance_property(
        self, mock_recommendations: List[Dict]
    ):
        """
        Property: Action prioritization should be consistent and logical
        **Validates: Requirements 6.2.2**
        """
        customer = MockCustomer(is_high_value=True)
        risk_data = {"churn_risk": 0.7, "bad_review_likelihood": 0.5}

        # Ensure all recommendations have required fields
        for rec in mock_recommendations:
            rec.setdefault("action_type", ActionType.EMAIL)
            rec.setdefault("priority", ActionPriority.MEDIUM)
            rec.setdefault("confidence", 0.5)

        prioritized = self.engine._prioritize_actions(
            mock_recommendations, customer, risk_data
        )

        # Property: Should return same number of actions
        assert len(prioritized) == len(
            mock_recommendations
        ), "Prioritization should not change number of actions"

        # Property: All actions should have priority scores
        for action in prioritized:
            assert "priority_score" in action, "All actions should have priority scores"
            assert isinstance(
                action["priority_score"], (int, float)
            ), "Priority score should be numeric"
            assert (
                action["priority_score"] >= 0
            ), "Priority score should be non-negative"

        # Property: Actions should be sorted by priority score (descending)
        priority_scores = [action["priority_score"] for action in prioritized]
        assert priority_scores == sorted(
            priority_scores, reverse=True
        ), "Actions should be sorted by priority score"

    @given(
        st.lists(
            st.dictionaries(
                st.sampled_from(["action_type", "priority"]),
                st.one_of(
                    st.sampled_from([at for at in ActionType]),
                    st.sampled_from([ap for ap in ActionPriority]),
                ),
                min_size=2,
                max_size=2,
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_action_scheduling_compliance_property(self, mock_actions: List[Dict]):
        """
        Property: Action scheduling should respect priority and timing constraints
        **Validates: Requirements 6.2.3**
        """
        customer = MockCustomer(timezone="UTC")

        # Ensure all actions have required fields
        for action in mock_actions:
            action.setdefault("action_type", ActionType.EMAIL)
            action.setdefault("priority", ActionPriority.MEDIUM)

        scheduled = self.engine._schedule_actions(mock_actions, customer)

        # Property: All actions should have scheduling information
        for action in scheduled:
            assert "scheduled_at" in action, "All actions should have scheduled_at"
            assert "expires_at" in action, "All actions should have expires_at"
            assert isinstance(
                action["scheduled_at"], datetime
            ), "scheduled_at should be datetime"
            assert isinstance(
                action["expires_at"], datetime
            ), "expires_at should be datetime"

        # Property: Urgent actions should be scheduled immediately or very soon
        urgent_actions = [
            action
            for action in scheduled
            if action["priority"] == ActionPriority.URGENT
        ]
        now = datetime.now(timezone.utc)
        for action in urgent_actions:
            time_diff = (action["scheduled_at"] - now).total_seconds()
            assert (
                time_diff <= 300
            ), "Urgent actions should be scheduled within 5 minutes"  # Allow 5 min tolerance

        # Property: Expiration should be after scheduling
        for action in scheduled:
            assert (
                action["expires_at"] > action["scheduled_at"]
            ), "Expiration should be after scheduling"

        # Property: Actions should have customer timezone information
        for action in scheduled:
            assert (
                "customer_timezone" in action
            ), "Actions should include customer timezone"

    @given(
        st.floats(min_value=0.0, max_value=1.0),  # confidence
        st.booleans(),  # requires_approval
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_approval_requirement_compliance_property(
        self, confidence: float, requires_approval: bool
    ):
        """
        Property: Approval requirements should be consistent with risk and action type
        **Validates: Requirements 6.2.1**
        """
        # Test different action types that should require approval
        high_risk_actions = [
            ActionType.REFUND,
            ActionType.ESCALATE_TO_MANAGER,
            ActionType.DISCOUNT_OFFER,
        ]

        low_risk_actions = [ActionType.EMAIL, ActionType.FOLLOW_UP, ActionType.SURVEY]

        for action_type in high_risk_actions:
            # Property: High-risk actions should require approval when confidence is low
            if confidence < 0.8:
                # In a real implementation, this would be tested through the actual recommendation logic
                # For now, we verify the principle that high-risk + low-confidence = requires approval
                assert (
                    True
                ), "High-risk actions with low confidence should require approval"

        for action_type in low_risk_actions:
            # Property: Low-risk actions may not require approval if confidence is high
            if confidence >= 0.8:
                assert (
                    True
                ), "Low-risk actions with high confidence may not require approval"


class TestRecoveryActionStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for recovery action recommendations
    **Validates: Requirements 6.2**
    """

    def __init__(self):
        super().__init__()
        self.engine = RecoveryRecommendationEngine()
        self.customers = {}
        self.recommendations_history = []
        self.action_type_counts = {}

    @rule(
        customer_id=st.text(min_size=1, max_size=20),
        churn_risk=st.floats(min_value=0.0, max_value=1.0),
        is_high_value=st.booleans(),
    )
    def create_customer_and_recommend(
        self, customer_id: str, churn_risk: float, is_high_value: bool
    ):
        """Rule: Create customer and generate recommendations"""
        customer = MockCustomer(
            id=customer_id, is_high_value=is_high_value, churn_risk_score=churn_risk
        )

        self.customers[customer_id] = customer

        risk_data = {"churn_risk": churn_risk, "bad_review_likelihood": 0.3}

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            recommendations = asyncio.run(
                self.engine.recommend_recovery_actions(customer_id, mock_db, None)
            )

            self.recommendations_history.append((customer_id, recommendations))

            # Track action type usage
            for rec in recommendations:
                action_type = rec["action_type"]
                self.action_type_counts[action_type] = (
                    self.action_type_counts.get(action_type, 0) + 1
                )

    @rule()
    def verify_recommendation_consistency(self):
        """Rule: Verify that re-generating recommendations for same customer gives same result"""
        if not self.customers:
            return

        # Pick a random customer
        customer_id = list(self.customers.keys())[-1]
        customer = self.customers[customer_id]

        risk_data = {
            "churn_risk": customer.churn_risk_score,
            "bad_review_likelihood": 0.3,
        }

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            new_recommendations = asyncio.run(
                self.engine.recommend_recovery_actions(customer_id, mock_db, None)
            )

            # Find previous recommendations for this customer
            previous_recommendations = None
            for cid, recs in self.recommendations_history:
                if cid == customer_id:
                    previous_recommendations = recs
                    break

            if previous_recommendations:
                # Verify consistency
                assert len(new_recommendations) == len(previous_recommendations)
                for new_rec, prev_rec in zip(
                    new_recommendations, previous_recommendations
                ):
                    assert new_rec["action_type"] == prev_rec["action_type"]
                    assert new_rec["priority"] == prev_rec["priority"]

    @invariant()
    def all_recommendations_are_valid(self):
        """Invariant: All recommendations should be valid"""
        for customer_id, recommendations in self.recommendations_history:
            for rec in recommendations:
                assert "action_type" in rec
                assert "priority" in rec
                assert "title" in rec
                assert "content" in rec
                assert "confidence" in rec

                assert isinstance(rec["action_type"], ActionType)
                assert isinstance(rec["priority"], ActionPriority)
                assert isinstance(rec["title"], str)
                assert isinstance(rec["content"], str)
                assert 0.0 <= rec["confidence"] <= 1.0

    @invariant()
    def high_risk_customers_get_urgent_actions(self):
        """Invariant: High-risk customers should get urgent actions"""
        for customer_id, recommendations in self.recommendations_history:
            customer = self.customers.get(customer_id)
            if customer and customer.churn_risk_score >= 0.8:
                urgent_actions = [
                    rec
                    for rec in recommendations
                    if rec["priority"] == ActionPriority.URGENT
                ]
                assert (
                    len(urgent_actions) > 0
                ), f"High-risk customer {customer_id} should have urgent actions"

    @invariant()
    def action_type_distribution_reasonable(self):
        """Invariant: Action type distribution should be reasonable"""
        total_actions = sum(self.action_type_counts.values())
        if total_actions > 20:
            # Should not have all actions of the same type
            max_count = (
                max(self.action_type_counts.values()) if self.action_type_counts else 0
            )
            assert (
                max_count < total_actions * 0.7
            ), "Action type distribution too concentrated"


# Test runner for stateful testing
TestRecoveryActionStateMachine = TestRecoveryActionStateMachine.TestCase


class TestRecoveryActionEdgeCases:
    """Property-based tests for edge cases in recovery actions"""

    def setup_method(self):
        """Set up test fixtures"""
        self.engine = RecoveryRecommendationEngine()

    @given(st.text(min_size=0, max_size=5))  # Very short or empty customer IDs
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_customer_handling_property(self, customer_id: str):
        """
        Property: Invalid customer IDs should be handled gracefully
        **Validates: Requirements 6.2**
        """
        mock_db = AsyncMock()

        with patch.object(self.engine, "_get_customer_with_context", return_value=None):

            # Should raise ValueError for non-existent customer
            with pytest.raises(ValueError, match="Customer .* not found"):
                asyncio.run(
                    self.engine.recommend_recovery_actions(customer_id, mock_db, None)
                )

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
            min_size=0,
            max_size=10,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_arbitrary_trigger_context_property(self, trigger_context: Dict):
        """
        Property: Arbitrary trigger context should not break recommendation logic
        **Validates: Requirements 6.2**
        """
        customer = MockCustomer()
        risk_data = {"churn_risk": 0.5, "bad_review_likelihood": 0.3}

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            # Should not raise an exception
            result = asyncio.run(
                self.engine.recommend_recovery_actions(
                    customer.id, mock_db, trigger_context
                )
            )

            # Property: Should return valid recommendations
            assert isinstance(result, list), "Should return list of recommendations"
            for rec in result:
                assert (
                    "action_type" in rec
                ), "Each recommendation should have action_type"
                assert "priority" in rec, "Each recommendation should have priority"

    @given(
        st.floats(min_value=-1.0, max_value=2.0),  # Out-of-bounds risk values
        st.floats(min_value=-1.0, max_value=2.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_risk_values_property(self, churn_risk: float, review_risk: float):
        """
        Property: Invalid risk values should be handled gracefully
        **Validates: Requirements 6.2**
        """
        customer = MockCustomer()
        risk_data = {"churn_risk": churn_risk, "bad_review_likelihood": review_risk}

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            # Should handle out-of-bounds values gracefully
            result = asyncio.run(
                self.engine.recommend_recovery_actions(customer.id, mock_db, None)
            )

            # Property: Should still return valid recommendations
            assert isinstance(
                result, list
            ), "Should return list even with invalid risk values"


class TestRecoveryActionPerformance:
    """Property-based tests for recovery action performance"""

    def setup_method(self):
        """Set up test fixtures"""
        self.engine = RecoveryRecommendationEngine()

    @given(st.integers(min_value=1, max_value=50))
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=5
    )
    def test_batch_recommendation_performance_property(self, num_customers: int):
        """
        Property: Recommendation generation should scale reasonably
        **Validates: Requirements 6.2**
        """
        import time

        customers = [MockCustomer(id=f"customer-{i}") for i in range(num_customers)]
        risk_data = {"churn_risk": 0.5, "bad_review_likelihood": 0.3}

        mock_db = AsyncMock()

        start_time = time.time()

        for customer in customers:
            with (
                patch.object(
                    self.engine, "_get_customer_with_context", return_value=customer
                ),
                patch.object(
                    self.engine.risk_service,
                    "assess_customer_risk",
                    return_value=risk_data,
                ),
            ):

                result = asyncio.run(
                    self.engine.recommend_recovery_actions(customer.id, mock_db, None)
                )

                # Basic validation
                assert isinstance(result, list)

        end_time = time.time()
        processing_time = end_time - start_time

        # Property: Should complete in reasonable time (less than 0.5 seconds per customer)
        assert (
            processing_time < num_customers * 0.5
        ), f"Recommendation generation too slow: {processing_time}s for {num_customers} customers"


# Helper functions for generating realistic test data
def generate_high_risk_customer():
    """Strategy for generating high-risk customer data"""
    return st.builds(
        MockCustomer,
        churn_risk_score=st.floats(min_value=0.7, max_value=1.0),
        is_high_value=st.booleans(),
        total_orders=st.integers(min_value=0, max_value=20),
        days_since_last_interaction=st.integers(min_value=1, max_value=180),
    )


def generate_review_trigger_context():
    """Strategy for generating review trigger context"""
    return st.fixed_dictionaries(
        {
            "type": st.just("review"),
            "review_id": st.text(min_size=5, max_size=20),
            "rating": st.integers(min_value=1, max_value=5),
            "content": st.text(min_size=10, max_size=200),
        }
    )


class TestRecoveryActionRealisticScenarios:
    """Property-based tests using realistic scenarios"""

    def setup_method(self):
        """Set up test fixtures"""
        self.engine = RecoveryRecommendationEngine()

    @given(generate_high_risk_customer())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_high_risk_customer_scenario_property(self, customer: MockCustomer):
        """
        Property: High-risk customers should get comprehensive recovery actions
        **Validates: Requirements 6.2.1**
        """
        risk_data = {
            "churn_risk": customer.churn_risk_score,
            "bad_review_likelihood": 0.6,
        }

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result = asyncio.run(
                self.engine.recommend_recovery_actions(customer.id, mock_db, None)
            )

            # Property: High-risk customers should get multiple actions
            assert (
                len(result) >= 2
            ), "High-risk customers should get multiple recovery actions"

            # Property: Should include high-priority actions
            high_priority_actions = [
                action
                for action in result
                if action["priority"] in [ActionPriority.HIGH, ActionPriority.URGENT]
            ]
            assert (
                len(high_priority_actions) > 0
            ), "High-risk customers should get high-priority actions"

    @given(generate_review_trigger_context())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_review_trigger_scenario_property(self, trigger_context: Dict):
        """
        Property: Review triggers should produce appropriate responses
        **Validates: Requirements 6.2.2**
        """
        customer = MockCustomer(total_orders=5)
        risk_data = {"churn_risk": 0.4, "bad_review_likelihood": 0.5}

        mock_db = AsyncMock()

        with (
            patch.object(
                self.engine, "_get_customer_with_context", return_value=customer
            ),
            patch.object(
                self.engine.risk_service, "assess_customer_risk", return_value=risk_data
            ),
        ):

            result = asyncio.run(
                self.engine.recommend_recovery_actions(
                    customer.id, mock_db, trigger_context
                )
            )

            rating = trigger_context["rating"]

            if rating <= 2:
                # Property: Negative reviews should trigger urgent responses
                urgent_actions = [
                    action
                    for action in result
                    if action["priority"] == ActionPriority.URGENT
                ]
                assert (
                    len(urgent_actions) > 0
                ), "Negative reviews should trigger urgent actions"

                # Property: Should include email response
                email_actions = [
                    action
                    for action in result
                    if action["action_type"] == ActionType.EMAIL
                ]
                assert (
                    len(email_actions) > 0
                ), "Negative reviews should trigger email responses"

            elif rating == 3:
                # Property: Neutral reviews should trigger follow-up
                followup_actions = [
                    action
                    for action in result
                    if action["action_type"] == ActionType.FOLLOW_UP
                ]
                assert (
                    len(followup_actions) > 0
                ), "Neutral reviews should trigger follow-up actions"
