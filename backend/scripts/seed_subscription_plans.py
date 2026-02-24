"""Seed subscription plans into the database"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.subscription import SubscriptionPlan
import uuid


def seed_subscription_plans(db: Session):
    """Seed subscription plans"""
    
    # Check if plans already exist
    existing_plans = db.query(SubscriptionPlan).count()
    if existing_plans > 0:
        print(f"Subscription plans already exist ({existing_plans} plans found). Skipping seed.")
        return
    
    plans = [
        {
            "id": uuid.uuid4(),
            "name": "Starter",
            "description": "Perfect for small businesses getting started with reputation management",
            "price_monthly": 49.00,
            "price_yearly": 490.00,  # ~2 months free
            "features": {
                "review_monitoring": True,
                "automated_responses": True,
                "sentiment_analysis": True,
                "basic_analytics": True,
                "email_support": True,
                "customer_recovery": False,
                "advanced_analytics": False,
                "priority_support": False,
                "custom_integrations": False
            },
            "limits": {
                "reviews_per_month": 100,
                "recovery_actions_per_month": 0,
                "team_members": 2,
                "api_calls_per_day": 1000
            },
            "is_active": True
        },
        {
            "id": uuid.uuid4(),
            "name": "Professional",
            "description": "For growing businesses that need advanced features and customer recovery",
            "price_monthly": 149.00,
            "price_yearly": 1490.00,  # ~2 months free
            "features": {
                "review_monitoring": True,
                "automated_responses": True,
                "sentiment_analysis": True,
                "basic_analytics": True,
                "email_support": True,
                "customer_recovery": True,
                "advanced_analytics": True,
                "priority_support": True,
                "custom_integrations": False,
                "whatsapp_integration": True,
                "crm_integration": True
            },
            "limits": {
                "reviews_per_month": 500,
                "recovery_actions_per_month": 200,
                "team_members": 10,
                "api_calls_per_day": 5000
            },
            "is_active": True
        },
        {
            "id": uuid.uuid4(),
            "name": "Enterprise",
            "description": "For large organizations with custom needs and unlimited usage",
            "price_monthly": 499.00,
            "price_yearly": 4990.00,  # ~2 months free
            "features": {
                "review_monitoring": True,
                "automated_responses": True,
                "sentiment_analysis": True,
                "basic_analytics": True,
                "email_support": True,
                "customer_recovery": True,
                "advanced_analytics": True,
                "priority_support": True,
                "custom_integrations": True,
                "whatsapp_integration": True,
                "crm_integration": True,
                "dedicated_account_manager": True,
                "custom_workflows": True,
                "white_label": True
            },
            "limits": {
                "reviews_per_month": -1,  # Unlimited
                "recovery_actions_per_month": -1,  # Unlimited
                "team_members": -1,  # Unlimited
                "api_calls_per_day": -1  # Unlimited
            },
            "is_active": True
        }
    ]
    
    for plan_data in plans:
        plan = SubscriptionPlan(**plan_data)
        db.add(plan)
    
    db.commit()
    print(f"Successfully seeded {len(plans)} subscription plans")
    
    # Print plan details
    for plan_data in plans:
        print(f"\n{plan_data['name']} Plan:")
        print(f"  Monthly: ${plan_data['price_monthly']}")
        print(f"  Yearly: ${plan_data['price_yearly']}")
        print(f"  Reviews/month: {plan_data['limits']['reviews_per_month']}")
        print(f"  Team members: {plan_data['limits']['team_members']}")


def main():
    """Main function"""
    print("Seeding subscription plans...")
    
    db = SessionLocal()
    try:
        seed_subscription_plans(db)
    except Exception as e:
        print(f"Error seeding subscription plans: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    print("\nSubscription plans seeding complete!")


if __name__ == "__main__":
    main()
