"""
Setup Stripe products and prices
This script creates products and prices in Stripe and updates the database
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import stripe
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.subscription import SubscriptionPlan


def setup_stripe_products(db: Session):
    """Create Stripe products and prices for subscription plans"""
    
    if not settings.STRIPE_SECRET_KEY:
        print("Error: STRIPE_SECRET_KEY not configured")
        return
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    # Get all subscription plans from database
    plans = db.query(SubscriptionPlan).all()
    
    if not plans:
        print("No subscription plans found in database. Run seed_subscription_plans.py first.")
        return
    
    print(f"Found {len(plans)} subscription plans")
    print("Creating Stripe products and prices...\n")
    
    for plan in plans:
        print(f"Processing plan: {plan.name}")
        
        try:
            # Create Stripe product
            product = stripe.Product.create(
                name=plan.name,
                description=plan.description,
                metadata={
                    "plan_id": str(plan.id),
                    "features": str(plan.features),
                    "limits": str(plan.limits)
                }
            )
            print(f"  ✓ Created product: {product.id}")
            
            # Create monthly price
            monthly_price = stripe.Price.create(
                product=product.id,
                unit_amount=int(float(plan.price_monthly) * 100),  # Convert to cents
                currency="usd",
                recurring={"interval": "month"},
                metadata={"plan_id": str(plan.id), "period": "monthly"}
            )
            print(f"  ✓ Created monthly price: {monthly_price.id} (${plan.price_monthly}/month)")
            
            # Create yearly price
            yearly_price = stripe.Price.create(
                product=product.id,
                unit_amount=int(float(plan.price_yearly) * 100),  # Convert to cents
                currency="usd",
                recurring={"interval": "year"},
                metadata={"plan_id": str(plan.id), "period": "yearly"}
            )
            print(f"  ✓ Created yearly price: {yearly_price.id} (${plan.price_yearly}/year)")
            
            # Update database with Stripe IDs
            plan.stripe_price_id_monthly = monthly_price.id
            plan.stripe_price_id_yearly = yearly_price.id
            db.commit()
            
            print(f"  ✓ Updated database with Stripe IDs\n")
            
        except stripe.error.StripeError as e:
            print(f"  ✗ Stripe error: {str(e)}\n")
            db.rollback()
            continue
        except Exception as e:
            print(f"  ✗ Error: {str(e)}\n")
            db.rollback()
            continue
    
    print("Stripe setup complete!")
    print("\nNext steps:")
    print("1. Configure webhook endpoint in Stripe Dashboard")
    print("2. Add webhook secret to environment variables")
    print("3. Test checkout flow with test cards")


def list_stripe_products():
    """List all Stripe products and prices"""
    
    if not settings.STRIPE_SECRET_KEY:
        print("Error: STRIPE_SECRET_KEY not configured")
        return
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    print("Listing Stripe products and prices:\n")
    
    try:
        products = stripe.Product.list(limit=100)
        
        for product in products.data:
            print(f"Product: {product.name} ({product.id})")
            
            # Get prices for this product
            prices = stripe.Price.list(product=product.id, limit=100)
            for price in prices.data:
                interval = price.recurring.get("interval") if price.recurring else "one-time"
                amount = price.unit_amount / 100
                print(f"  - Price: ${amount} / {interval} ({price.id})")
            
            print()
    
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")


def main():
    """Main function"""
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_stripe_products()
        return
    
    print("=" * 60)
    print("Stripe Products and Prices Setup")
    print("=" * 60)
    print()
    
    if not settings.STRIPE_SECRET_KEY:
        print("Error: STRIPE_SECRET_KEY environment variable not set")
        print("Please configure your Stripe API key in .env file")
        return
    
    print(f"Using Stripe API key: {settings.STRIPE_SECRET_KEY[:7]}...")
    print()
    
    confirm = input("This will create products and prices in Stripe. Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    
    db = SessionLocal()
    try:
        setup_stripe_products(db)
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
