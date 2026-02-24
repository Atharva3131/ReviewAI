"""
Demo Data Generator for Revive AI
Generates realistic sample data for demonstrations
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.customer import Customer
from app.models.review import Review, ReviewPlatform, UrgencyLevel, ReviewStatus, IssueCategory
from app.core.security import SecurityService

# Sample data
CUSTOMER_NAMES = [
    "Sarah Johnson", "Mike Chen", "Emily Davis", "James Wilson", "Lisa Anderson",
    "David Martinez", "Jennifer Taylor", "Robert Brown", "Maria Garcia", "John Smith",
    "Amanda White", "Chris Lee", "Michelle Rodriguez", "Kevin Thompson", "Laura Martinez"
]

POSITIVE_REVIEWS = [
    "Excellent service! The staff was friendly and attentive. Food was delicious!",
    "Amazing experience! Everything was perfect from start to finish. Highly recommend!",
    "Best restaurant in town! Great atmosphere, wonderful food, and fantastic service.",
    "Outstanding! The quality exceeded our expectations. Will definitely come back!",
    "Absolutely loved it! The attention to detail was impressive. Five stars!",
    "Incredible experience! Staff went above and beyond. Food was exceptional!",
    "Perfect evening! Everything was spot on. Can't wait to return!",
    "Wonderful service and amazing food! Highly recommended to everyone!",
]

NEGATIVE_REVIEWS = [
    "Terrible service! Waited 2 hours for food. Staff was rude and unhelpful. Very disappointed.",
    "Worst experience ever. Food was cold, service was slow. Won't be coming back.",
    "Extremely disappointed. Long wait times, poor quality food, and inattentive staff.",
    "Not worth the money. Service was terrible and food was mediocre at best.",
    "Very frustrating experience. Waited forever, food was wrong, no apology given.",
    "Horrible! Staff was rude, food took forever, and quality was poor. Avoid this place!",
    "Completely unacceptable. Long waits, cold food, and terrible customer service.",
    "Disappointed and frustrated. Nothing went right. Would not recommend.",
]

MIXED_REVIEWS = [
    "Food was good but service could be better. Long wait time but worth it in the end.",
    "Decent experience overall. Some issues with timing but food quality was good.",
    "Mixed feelings. Great food but service needs improvement. Might give it another try.",
    "Food was excellent but we had to wait quite a while. Service was okay.",
    "Good food, average service. Some room for improvement but not bad overall.",
    "Satisfactory experience. Food was tasty but service could be faster.",
]


async def create_demo_organization(session: AsyncSession):
    """Create demo organization"""
    org = Organization(
        name="Demo Restaurant Chain",
        domain="demo-restaurant.com",
        settings={
            "industry": "restaurant",
            "size": "medium",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en"
        }
    )
    session.add(org)
    await session.flush()
    return org


async def create_demo_user(session: AsyncSession, org_id):
    """Create demo user"""
    # Use passlib directly to hash the password
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Simple password that will work
    password_hash = pwd_context.hash("demo123")
    
    user = User(
        email="demo@restaurant.com",
        password_hash=password_hash,
        first_name="Demo",
        last_name="Manager",
        role=UserRole.ADMIN,
        organization_id=org_id,
        is_active=True,
        is_verified=True
    )
    session.add(user)
    await session.flush()
    return user


async def create_demo_customers(session: AsyncSession, org_id, count=15):
    """Create demo customers"""
    customers = []
    
    for i, name in enumerate(CUSTOMER_NAMES[:count]):
        first_name = name.split()[0].lower()
        last_name = name.split()[1].lower()
        
        customer = Customer(
            organization_id=org_id,
            name=name,
            email=f"{first_name}.{last_name}@email.com",
            phone=f"+1555{random.randint(1000000, 9999999)}",
            lifetime_value=random.randint(100, 2000),
            total_orders=random.randint(1, 20),
            churn_risk_score=random.uniform(0.1, 0.9),
            bad_review_likelihood=random.uniform(0.1, 0.8),
            last_interaction=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            preferred_contact_method=random.choice(["email", "phone", "sms"]),
            tags=f"demo,{random.choice(['Downtown', 'Uptown', 'Suburbs'])}"
        )
        customers.append(customer)
        session.add(customer)
    
    await session.flush()
    return customers


async def create_demo_reviews(session: AsyncSession, org_id, customers):
    """Create demo reviews"""
    reviews = []
    platforms = [ReviewPlatform.GOOGLE, ReviewPlatform.YELP, ReviewPlatform.FACEBOOK]
    
    # Create mix of positive, negative, and mixed reviews
    review_templates = [
        (5, POSITIVE_REVIEWS, UrgencyLevel.LOW, ReviewStatus.RESPONDED),
        (5, POSITIVE_REVIEWS, UrgencyLevel.LOW, ReviewStatus.RESPONDED),
        (4, POSITIVE_REVIEWS, UrgencyLevel.LOW, ReviewStatus.RESPONDED),
        (4, MIXED_REVIEWS, UrgencyLevel.MEDIUM, ReviewStatus.PENDING),
        (3, MIXED_REVIEWS, UrgencyLevel.MEDIUM, ReviewStatus.PENDING),
        (3, MIXED_REVIEWS, UrgencyLevel.MEDIUM, ReviewStatus.RESPONDED),
        (2, NEGATIVE_REVIEWS, UrgencyLevel.HIGH, ReviewStatus.ESCALATED),
        (2, NEGATIVE_REVIEWS, UrgencyLevel.HIGH, ReviewStatus.PENDING),
        (1, NEGATIVE_REVIEWS, UrgencyLevel.HIGH, ReviewStatus.ESCALATED),
    ]
    
    for i, (rating, content_list, urgency, status) in enumerate(review_templates):
        if i >= len(customers):
            break
            
        customer = customers[i]
        content = random.choice(content_list)
        
        # Calculate sentiment based on rating
        if rating >= 4:
            sentiment_score = random.uniform(0.7, 1.0)
        elif rating == 3:
            sentiment_score = random.uniform(0.4, 0.6)
        else:
            sentiment_score = random.uniform(0.0, 0.3)
        
        # Assign categories based on content
        categories = []
        if "service" in content.lower() or "staff" in content.lower():
            categories.append(IssueCategory.SUPPORT)
        if "wait" in content.lower() or "slow" in content.lower():
            categories.append(IssueCategory.DELIVERY)
        if "food" in content.lower() or "quality" in content.lower():
            categories.append(IssueCategory.QUALITY)
        if "price" in content.lower() or "money" in content.lower():
            categories.append(IssueCategory.PRICING)
        
        if not categories:
            categories = [IssueCategory.OTHER]
        
        review = Review(
            organization_id=org_id,
            customer_id=customer.id,
            platform=random.choice(platforms),
            external_id=f"demo_review_{i}_{random.randint(1000, 9999)}",
            rating=rating,
            content=content,
            sentiment_score=sentiment_score,
            urgency_level=urgency,
            status=status,
            issue_categories=categories,
            review_date=datetime.utcnow() - timedelta(days=random.randint(1, 30))
        )
        reviews.append(review)
        session.add(review)
    
    await session.flush()
    return reviews


async def generate_demo_data():
    """Main function to generate all demo data"""
    print("🚀 Starting Demo Data Generation...")
    print("=" * 50)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create organization
            print("\n[1/4] Creating demo organization...")
            org = await create_demo_organization(session)
            print(f"✅ Created organization: {org.name}")
            
            # Create user
            print("\n[2/4] Creating demo user...")
            user = await create_demo_user(session, org.id)
            print(f"✅ Created user: {user.email}")
            print(f"   Password: demo123")
            
            # Create customers
            print("\n[3/4] Creating demo customers...")
            customers = await create_demo_customers(session, org.id, count=15)
            print(f"✅ Created {len(customers)} customers")
            
            # Create reviews
            print("\n[4/4] Creating demo reviews...")
            reviews = await create_demo_reviews(session, org.id, customers)
            print(f"✅ Created {len(reviews)} reviews")
            
            # Commit all changes
            await session.commit()
            
            print("\n" + "=" * 50)
            print("✨ Demo Data Generation Complete!")
            print("=" * 50)
            print("\n📊 Summary:")
            print(f"   • Organization: {org.name}")
            print(f"   • User Email: {user.email}")
            print(f"   • Password: demo123")
            print(f"   • Customers: {len(customers)}")
            print(f"   • Reviews: {len(reviews)}")
            
            # Calculate stats
            positive_reviews = sum(1 for r in reviews if r.rating >= 4)
            negative_reviews = sum(1 for r in reviews if r.rating <= 2)
            mixed_reviews = sum(1 for r in reviews if r.rating == 3)
            avg_rating = sum(r.rating for r in reviews) / len(reviews)
            
            print(f"\n📈 Review Statistics:")
            print(f"   • Average Rating: {avg_rating:.1f} stars")
            print(f"   • Positive (4-5★): {positive_reviews}")
            print(f"   • Mixed (3★): {mixed_reviews}")
            print(f"   • Negative (1-2★): {negative_reviews}")
            
            print(f"\n🎯 Next Steps:")
            print(f"   1. Login at http://localhost:3000/login")
            print(f"   2. Email: {user.email}")
            print(f"   3. Password: demo123")
            print(f"   4. Explore the dashboard!")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error generating demo data: {e}")
            raise


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  REVIVE AI - DEMO DATA GENERATOR")
    print("=" * 50)
    
    asyncio.run(generate_demo_data())
