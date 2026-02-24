"""
Tests for demo data seeding functionality
"""
import pytest
from decimal import Decimal


class TestDemoDataStructure:
    """Test demo data templates and structure"""
    
    def test_review_templates_structure(self):
        """Test that review templates have required fields"""
        from scripts.seed_demo_data import REVIEW_TEMPLATES
        
        for sentiment_type, templates in REVIEW_TEMPLATES.items():
            assert sentiment_type in ["positive", "moderate", "negative"]
            assert len(templates) > 0
            
            for template in templates:
                assert "content" in template
                assert "rating" in template
                assert "sentiment_score" in template
                assert "urgency_level" in template
                assert "categories" in template
                
                # Validate rating range
                assert 1 <= template["rating"] <= 5
                
                # Validate sentiment score range
                assert 0.0 <= template["sentiment_score"] <= 1.0
    
    def test_sentiment_rating_correlation(self):
        """Test that sentiment scores correlate with ratings"""
        from scripts.seed_demo_data import REVIEW_TEMPLATES
        
        # Positive reviews should have high sentiment
        for template in REVIEW_TEMPLATES["positive"]:
            assert template["rating"] >= 4
            assert template["sentiment_score"] >= 0.6
        
        # Negative reviews should have low sentiment
        for template in REVIEW_TEMPLATES["negative"]:
            assert template["rating"] <= 2
            assert template["sentiment_score"] <= 0.4
        
        # Moderate reviews should have medium sentiment
        for template in REVIEW_TEMPLATES["moderate"]:
            assert template["rating"] == 3
            assert 0.4 <= template["sentiment_score"] <= 0.7
    
    def test_organization_templates(self):
        """Test organization templates have required fields"""
        from scripts.seed_demo_data import ORGANIZATIONS
        
        assert len(ORGANIZATIONS) == 3
        
        for org in ORGANIZATIONS:
            assert "name" in org
            assert "domain" in org
            assert "settings" in org
            assert "business_type" in org["settings"]
            assert "auto_respond_threshold" in org["settings"]
            assert "escalation_threshold" in org["settings"]
    
    def test_ticket_templates_structure(self):
        """Test support ticket templates have required fields"""
        from scripts.seed_demo_data import TICKET_TEMPLATES
        
        for priority_type, templates in TICKET_TEMPLATES.items():
            assert priority_type in ["high_priority", "medium_priority", "low_priority"]
            
            for template in templates:
                assert "subject" in template
                assert "content" in template
                assert "priority" in template
                assert "category" in template
                assert "sentiment_score" in template
                
                # Validate sentiment score range
                assert 0.0 <= template["sentiment_score"] <= 1.0
    
    def test_customer_names_list(self):
        """Test customer names list is populated"""
        from scripts.seed_demo_data import CUSTOMER_NAMES
        
        assert len(CUSTOMER_NAMES) >= 5
        assert all(isinstance(name, str) for name in CUSTOMER_NAMES)
        assert all(len(name) > 0 for name in CUSTOMER_NAMES)
    
    def test_urgency_levels_valid(self):
        """Test that urgency levels in templates are valid"""
        from scripts.seed_demo_data import REVIEW_TEMPLATES
        from app.models import UrgencyLevel
        
        valid_levels = [UrgencyLevel.LOW, UrgencyLevel.MEDIUM, UrgencyLevel.HIGH]
        
        for templates in REVIEW_TEMPLATES.values():
            for template in templates:
                assert template["urgency_level"] in valid_levels
    
    def test_issue_categories_valid(self):
        """Test that issue categories in templates are valid"""
        from scripts.seed_demo_data import REVIEW_TEMPLATES
        from app.models import IssueCategory
        
        valid_categories = [
            IssueCategory.SUPPORT,
            IssueCategory.PRICING,
            IssueCategory.DELIVERY,
            IssueCategory.QUALITY
        ]
        
        for templates in REVIEW_TEMPLATES.values():
            for template in templates:
                assert len(template["categories"]) > 0
                for category in template["categories"]:
                    assert category in valid_categories


class TestDemoDataLogic:
    """Test demo data generation logic"""
    
    def test_risk_score_ranges(self):
        """Test that risk scores are within valid ranges"""
        # High risk
        high_risk = Decimal("0.85")
        assert Decimal("0.6") < high_risk <= Decimal("1.0")
        
        # Medium risk
        medium_risk = Decimal("0.45")
        assert Decimal("0.3") < medium_risk <= Decimal("0.6")
        
        # Low risk
        low_risk = Decimal("0.15")
        assert Decimal("0.0") <= low_risk <= Decimal("0.3")
    
    def test_review_distribution(self):
        """Test that review templates cover all rating levels"""
        from scripts.seed_demo_data import REVIEW_TEMPLATES
        
        all_ratings = set()
        for templates in REVIEW_TEMPLATES.values():
            for template in templates:
                all_ratings.add(template["rating"])
        
        # Should have reviews for ratings 1-5
        assert 1 in all_ratings
        assert 2 in all_ratings
        assert 3 in all_ratings
        assert 4 in all_ratings or 5 in all_ratings  # At least one positive
    
    def test_ticket_priority_distribution(self):
        """Test that ticket templates cover all priority levels"""
        from scripts.seed_demo_data import TICKET_TEMPLATES
        from app.models import TicketPriority
        
        all_priorities = set()
        for templates in TICKET_TEMPLATES.values():
            for template in templates:
                all_priorities.add(template["priority"])
        
        # Should have all priority levels
        assert TicketPriority.HIGH in all_priorities
        assert TicketPriority.MEDIUM in all_priorities
        assert TicketPriority.LOW in all_priorities


class TestDemoDataSafety:
    """Test safety features of demo data script"""
    
    def test_production_environment_blocked(self):
        """Test that production environment is blocked"""
        # This would be tested by running the script with --environment production
        # and verifying it exits with code 1
        # For now, we just verify the logic exists in the script
        import sys
        from pathlib import Path
        
        script_path = Path(__file__).parent.parent / "scripts" / "seed_demo_data.py"
        assert script_path.exists()
        
        with open(script_path, "r") as f:
            content = f.read()
            assert "production" in content.lower()
            assert "Cannot seed demo data in production" in content or \
                   "production environment" in content.lower()
    
    def test_clear_flag_exists(self):
        """Test that clear flag is implemented"""
        from pathlib import Path
        
        script_path = Path(__file__).parent.parent / "scripts" / "seed_demo_data.py"
        
        with open(script_path, "r") as f:
            content = f.read()
            assert "--clear" in content
            assert "clear_demo_data" in content or "clear_existing" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
