#!/usr/bin/env python3
"""
Demo Data Seeding Script for Revive AI

This script creates realistic demo data and scenarios for testing and demonstration purposes.
It generates:
- Organizations with different business types
- Users with various roles
- Reviews across different platforms and sentiments
- Customers with varying risk levels
- Support tickets with different priorities
- Recovery actions and agent decisions

Usage:
    python scripts/seed_demo_data.py --environment development
    python scripts/seed_demo_data.py --clear  # Clear existing demo data first
"""

import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
import random
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    Organization, User, UserRole,
    Review, ReviewPlatform, UrgencyLevel, ReviewStatus, IssueCategory,
    Customer,
    SupportTicket, TicketStatus, TicketPriority, TicketCategory,
    RecoveryAction, ActionType, ActionStatus, ActionPriority,
    AgentDecision, InputType, DecisionType, DecisionStatus
)


# Demo data templates
ORGANIZATIONS = [
    {
        "name": "Bella's Italian Restaurant",
        "domain": "bellas-restaurant.com",
        "settings": {
            "business_type": "restaurant",
            "auto_respond_threshold": 0.7,
            "escalation_threshold": 0.9
        }
    },
    {
        "name": "TechSupport Pro",
        "domain": "techsupportpro.com",
        "settings": {
            "business_type": "saas",
            "auto_respond_threshold": 0.8,
            "escalation_threshold": 0.85
        }
    },
    {
        "name": "QuickShip Logistics",
        "domain": "quickship.com",
        "settings": {
            "business_type": "logistics",
            "auto_respond_threshold": 0.75,
            "escalation_threshold": 0.9
        }
    }
]

REVIEW_TEMPLATES = {
    "positive": [
        {
            "content": "Amazing service! The staff was incredibly friendly and the food was delicious. Will definitely come back!",
            "rating": 5,
            "sentiment_score": 0.95,
            "urgency_level": UrgencyLevel.LOW,
            "categories": [IssueCategory.QUALITY]
        },
        {
            "content": "Great experience overall. Quick delivery and excellent customer support. Highly recommend!",
            "rating": 5,
            "sentiment_score": 0.92,
            "urgency_level": UrgencyLevel.LOW,
            "categories": [IssueCategory.SUPPORT, IssueCategory.DELIVERY]
        },
        {
            "content": "Best service I've had in years. Worth every penny!",
            "rating": 4,
            "sentiment_score": 0.88,
            "urgency_level": UrgencyLevel.LOW,
            "categories": [IssueCategory.QUALITY]
        }
    ],
    "moderate": [
        {
            "content": "Service was okay but took longer than expected. Food was good though.",
            "rating": 3,
            "sentiment_score": 0.55,
            "urgency_level": UrgencyLevel.MEDIUM,
            "categories": [IssueCategory.DELIVERY, IssueCategory.QUALITY]
        },
        {
            "content": "Had some issues with my order but customer service resolved it eventually.",
            "rating": 3,
            "sentiment_score": 0.50,
            "urgency_level": UrgencyLevel.MEDIUM,
            "categories": [IssueCategory.SUPPORT]
        }
    ],
    "negative": [
        {
            "content": "Terrible experience. Waited 2 hours for my order and it arrived cold. Very disappointed.",
            "rating": 2,
            "sentiment_score": 0.15,
            "urgency_level": UrgencyLevel.HIGH,
            "categories": [IssueCategory.DELIVERY, IssueCategory.QUALITY]
        },
        {
            "content": "Worst service ever! Staff was rude and unhelpful. Will never return.",
            "rating": 1,
            "sentiment_score": 0.05,
            "urgency_level": UrgencyLevel.HIGH,
            "categories": [IssueCategory.SUPPORT, IssueCategory.QUALITY]
        },
        {
            "content": "Overpriced and poor quality. Not worth the money at all.",
            "rating": 2,
            "sentiment_score": 0.20,
            "urgency_level": UrgencyLevel.HIGH,
            "categories": [IssueCategory.PRICING, IssueCategory.QUALITY]
        }
    ]
}

CUSTOMER_NAMES = [
    "John Smith", "Sarah Johnson", "Michael Brown", "Emily Davis",
    "David Wilson", "Jessica Martinez", "James Anderson", "Jennifer Taylor",
    "Robert Thomas", "Linda Garcia", "William Rodriguez", "Mary Martinez",
    "Richard Lee", "Patricia White", "Charles Harris"
]

TICKET_TEMPLATES = {
    "high_priority": [
        {
            "subject": "Urgent: Payment not processed",
            "content": "I made a payment 3 days ago but it still hasn't been processed. This is causing serious issues for my business.",
            "priority": TicketPriority.HIGH,
            "category": TicketCategory.BILLING,
            "sentiment_score": 0.15
        },
        {
            "subject": "Service completely down",
            "content": "Your service has been down for the past 6 hours. We're losing money every minute. Need immediate resolution!",
            "priority": TicketPriority.HIGH,
            "category": TicketCategory.TECHNICAL,
            "sentiment_score": 0.10
        }
    ],
    "medium_priority": [
        {
            "subject": "Question about billing",
            "content": "I noticed an unexpected charge on my account. Can you please explain what this is for?",
            "priority": TicketPriority.MEDIUM,
            "category": TicketCategory.BILLING,
            "sentiment_score": 0.45
        },
        {
            "subject": "Feature request",
            "content": "Would love to see a dark mode option. Many users have been asking for this.",
            "priority": TicketPriority.MEDIUM,
            "category": TicketCategory.FEATURE_REQUEST,
            "sentiment_score": 0.70
        }
    ],
    "low_priority": [
        {
            "subject": "General inquiry",
            "content": "Just wanted to know more about your premium plans. What are the benefits?",
            "priority": TicketPriority.LOW,
            "category": TicketCategory.GENERAL,
            "sentiment_score": 0.75
        }
    ]
}


async def clear_demo_data(session: AsyncSession):
    """Clear all existing demo data"""
    print("🗑️  Clearing existing demo data...")
    
    # Delete in reverse order of dependencies
    await session.execute(delete(AgentDecision))
    await session.execute(delete(RecoveryAction))
    await session.execute(delete(SupportTicket))
    await session.execute(delete(Review))
    await session.execute(delete(Customer))
    await session.execute(delete(User))
    await session.execute(delete(Organization))
    
    await session.commit()
    print("✅ Demo data cleared")


async def create_organizations(session: AsyncSession) -> List[Organization]:
    """Create demo organizations"""
    print("\n📊 Creating organizations...")
    
    orgs = []
    for org_data in ORGANIZATIONS:
        org = Organization(**org_data)
        session.add(org)
        orgs.append(org)
    
    await session.commit()
    
    for org in orgs:
        await session.refresh(org)
        print(f"  ✓ Created: {org.name}")
    
    return orgs


async def create_users(session: AsyncSession, organizations: List[Organization]) -> List[User]:
    """Create demo users for each organization"""
    print("\n👥 Creating users...")
    
    users = []
    for org in organizations:
        # Admin user
        admin = User(
            organization_id=org.id,
            email=f"admin@{org.domain}",
            password_hash=get_password_hash("demo123"),
            role=UserRole.ADMIN,
            first_name="Admin",
            last_name="User"
        )
        session.add(admin)
        users.append(admin)
        
        # Regular user
        user = User(
            organization_id=org.id,
            email=f"user@{org.domain}",
            password_hash=get_password_hash("demo123"),
            role=UserRole.USER,
            first_name="Regular",
            last_name="User"
        )
        session.add(user)
        users.append(user)
    
    await session.commit()
    
    for user in users:
        await session.refresh(user)
        print(f"  ✓ Created: {user.email} ({user.role.value})")
    
    return users


async def create_customers(session: AsyncSession, organizations: List[Organization]) -> List[Customer]:
    """Create demo customers with varying risk levels"""
    print("\n👤 Creating customers...")
    
    customers = []
    for org in organizations:
        # Create 5 customers per organization with different risk profiles
        for i, name in enumerate(CUSTOMER_NAMES[:5]):
            # Vary risk levels
            if i == 0:  # High risk
                churn_risk = Decimal("0.85")
                bad_review_likelihood = Decimal("0.78")
            elif i == 1:  # Medium-high risk
                churn_risk = Decimal("0.65")
                bad_review_likelihood = Decimal("0.55")
            elif i == 2:  # Medium risk
                churn_risk = Decimal("0.45")
                bad_review_likelihood = Decimal("0.35")
            else:  # Low risk
                churn_risk = Decimal("0.15")
                bad_review_likelihood = Decimal("0.10")
            
            customer = Customer(
                organization_id=org.id,
                email=f"{name.lower().replace(' ', '.')}@email.com",
                phone=f"+1555{random.randint(1000000, 9999999)}",
                name=name,
                churn_risk_score=churn_risk,
                bad_review_likelihood=bad_review_likelihood,
                last_interaction=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                context_summary=f"Customer since {2020 + i} with {random.randint(5, 50)} interactions"
            )
            session.add(customer)
            customers.append(customer)
    
    await session.commit()
    
    for customer in customers:
        await session.refresh(customer)
        print(f"  ✓ Created: {customer.name} (Risk: {customer.risk_level})")
    
    return customers


async def create_reviews(session: AsyncSession, organizations: List[Organization], 
                        customers: List[Customer]) -> List[Review]:
    """Create demo reviews across different sentiment categories"""
    print("\n⭐ Creating reviews...")
    
    reviews = []
    platforms = [ReviewPlatform.GOOGLE, ReviewPlatform.YELP, ReviewPlatform.FACEBOOK]
    
    for org in organizations:
        org_customers = [c for c in customers if c.organization_id == org.id]
        
        # Create mix of positive, moderate, and negative reviews
        for sentiment_type, templates in REVIEW_TEMPLATES.items():
            for template in templates:
                customer = random.choice(org_customers)
                
                review = Review(
                    organization_id=org.id,
                    platform=random.choice(platforms),
                    external_id=f"review_{random.randint(100000, 999999)}",
                    customer_name=customer.name,
                    rating=template["rating"],
                    content=template["content"],
                    sentiment_score=Decimal(str(template["sentiment_score"])),
                    urgency_level=template["urgency_level"],
                    issue_categories=template["categories"],
                    status=ReviewStatus.PENDING if template["rating"] <= 3 else ReviewStatus.RESPONDED,
                    requires_private_recovery=template["rating"] <= 2,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                session.add(review)
                reviews.append(review)
    
    await session.commit()
    
    for review in reviews:
        await session.refresh(review)
        print(f"  ✓ Created: {review.rating}★ review - {review.urgency_level.value} urgency")
    
    return reviews


async def create_support_tickets(session: AsyncSession, organizations: List[Organization],
                                customers: List[Customer]) -> List[SupportTicket]:
    """Create demo support tickets"""
    print("\n🎫 Creating support tickets...")
    
    tickets = []
    
    for org in organizations:
        org_customers = [c for c in customers if c.organization_id == org.id]
        
        # Create tickets of different priorities
        for priority_type, templates in TICKET_TEMPLATES.items():
            for template in templates:
                customer = random.choice(org_customers)
                
                ticket = SupportTicket(
                    organization_id=org.id,
                    customer_id=customer.id,
                    external_id=f"ticket_{random.randint(10000, 99999)}",
                    subject=template["subject"],
                    content=template["content"],
                    status=TicketStatus.OPEN if template["priority"] == TicketPriority.HIGH else TicketStatus.IN_PROGRESS,
                    priority=template["priority"],
                    category=template["category"],
                    sentiment_score=Decimal(str(template["sentiment_score"])),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 15))
                )
                session.add(ticket)
                tickets.append(ticket)
    
    await session.commit()
    
    for ticket in tickets:
        await session.refresh(ticket)
        print(f"  ✓ Created: {ticket.priority.value} priority - {ticket.subject}")
    
    return tickets


async def create_recovery_actions(session: AsyncSession, organizations: List[Organization],
                                 customers: List[Customer], reviews: List[Review]) -> List[RecoveryAction]:
    """Create demo recovery actions"""
    print("\n🔄 Creating recovery actions...")
    
    actions = []
    
    for org in organizations:
        org_customers = [c for c in customers if c.organization_id == org.id]
        org_reviews = [r for r in reviews if r.organization_id == org.id and r.requires_private_recovery]
        
        # Create recovery actions for high-risk customers
        high_risk_customers = [c for c in org_customers if c.churn_risk_score > Decimal("0.6")]
        
        for customer in high_risk_customers:
            # Email recovery action
            email_action = RecoveryAction(
                organization_id=org.id,
                customer_id=customer.id,
                review_id=org_reviews[0].id if org_reviews else None,
                action_type=ActionType.EMAIL,
                priority=ActionPriority.HIGH,
                content=f"Dear {customer.name},\n\nWe noticed you've had some concerns recently and we sincerely apologize for any inconvenience. Your satisfaction is our top priority...",
                status=ActionStatus.SENT if random.random() > 0.3 else ActionStatus.PENDING,
                scheduled_at=datetime.utcnow() + timedelta(hours=2),
                executed_at=datetime.utcnow() if random.random() > 0.3 else None
            )
            session.add(email_action)
            actions.append(email_action)
            
            # Discount offer for very high risk
            if customer.churn_risk_score > Decimal("0.8"):
                discount_action = RecoveryAction(
                    organization_id=org.id,
                    customer_id=customer.id,
                    action_type=ActionType.DISCOUNT,
                    priority=ActionPriority.HIGH,
                    content="20% discount on next purchase as a gesture of goodwill",
                    status=ActionStatus.PENDING,
                    scheduled_at=datetime.utcnow() + timedelta(hours=1)
                )
                session.add(discount_action)
                actions.append(discount_action)
    
    await session.commit()
    
    for action in actions:
        await session.refresh(action)
        print(f"  ✓ Created: {action.action_type.value} - {action.status.value}")
    
    return actions


async def create_agent_decisions(session: AsyncSession, organizations: List[Organization],
                                reviews: List[Review]) -> List[AgentDecision]:
    """Create demo agent decisions"""
    print("\n🤖 Creating agent decisions...")
    
    decisions = []
    
    for org in organizations:
        org_reviews = [r for r in reviews if r.organization_id == org.id]
        
        for review in org_reviews[:5]:  # Create decisions for first 5 reviews per org
            # Determine decision type based on review characteristics
            if review.rating <= 2 and review.urgency_level == UrgencyLevel.HIGH:
                decision_type = DecisionType.RECOVER_PRIVATE
                confidence = Decimal("0.95")
                reasoning = "Critical negative review requiring immediate private recovery"
            elif review.rating >= 4:
                decision_type = DecisionType.RESPOND_PUBLIC
                confidence = Decimal("0.90")
                reasoning = "Positive review - thank customer publicly"
            elif review.urgency_level == UrgencyLevel.HIGH and len(review.issue_categories) > 2:
                decision_type = DecisionType.ESCALATE
                confidence = Decimal("0.60")
                reasoning = "Complex multi-issue case requiring human review"
            else:
                decision_type = DecisionType.RESPOND_PUBLIC
                confidence = Decimal("0.75")
                reasoning = "Standard case - public response appropriate"
            
            decision = AgentDecision(
                organization_id=org.id,
                input_type=InputType.REVIEW,
                input_id=review.id,
                decision_type=decision_type,
                confidence_score=confidence,
                reasoning=reasoning,
                status=DecisionStatus.EXECUTED if random.random() > 0.2 else DecisionStatus.PENDING,
                metadata={
                    "sentiment_score": float(review.sentiment_score),
                    "urgency_level": review.urgency_level.value,
                    "rating": review.rating
                }
            )
            session.add(decision)
            decisions.append(decision)
    
    await session.commit()
    
    for decision in decisions:
        await session.refresh(decision)
        print(f"  ✓ Created: {decision.decision_type.value} - confidence {decision.confidence_score}")
    
    return decisions


async def print_summary(session: AsyncSession):
    """Print summary of created demo data"""
    print("\n" + "="*60)
    print("📊 DEMO DATA SUMMARY")
    print("="*60)
    
    # Count records
    org_count = (await session.execute(select(Organization))).scalars().all()
    user_count = (await session.execute(select(User))).scalars().all()
    customer_count = (await session.execute(select(Customer))).scalars().all()
    review_count = (await session.execute(select(Review))).scalars().all()
    ticket_count = (await session.execute(select(SupportTicket))).scalars().all()
    action_count = (await session.execute(select(RecoveryAction))).scalars().all()
    decision_count = (await session.execute(select(AgentDecision))).scalars().all()
    
    print(f"\n📊 Organizations: {len(org_count)}")
    for org in org_count:
        print(f"   • {org.name}")
    
    print(f"\n👥 Users: {len(user_count)}")
    print(f"   • Admins: {sum(1 for u in user_count if u.role == UserRole.ADMIN)}")
    print(f"   • Regular Users: {sum(1 for u in user_count if u.role == UserRole.USER)}")
    
    print(f"\n👤 Customers: {len(customer_count)}")
    print(f"   • High Risk: {sum(1 for c in customer_count if c.churn_risk_score > Decimal('0.6'))}")
    print(f"   • Medium Risk: {sum(1 for c in customer_count if Decimal('0.3') < c.churn_risk_score <= Decimal('0.6'))}")
    print(f"   • Low Risk: {sum(1 for c in customer_count if c.churn_risk_score <= Decimal('0.3'))}")
    
    print(f"\n⭐ Reviews: {len(review_count)}")
    print(f"   • 5 stars: {sum(1 for r in review_count if r.rating == 5)}")
    print(f"   • 4 stars: {sum(1 for r in review_count if r.rating == 4)}")
    print(f"   • 3 stars: {sum(1 for r in review_count if r.rating == 3)}")
    print(f"   • 2 stars: {sum(1 for r in review_count if r.rating == 2)}")
    print(f"   • 1 star: {sum(1 for r in review_count if r.rating == 1)}")
    
    print(f"\n🎫 Support Tickets: {len(ticket_count)}")
    print(f"   • High Priority: {sum(1 for t in ticket_count if t.priority == TicketPriority.HIGH)}")
    print(f"   • Medium Priority: {sum(1 for t in ticket_count if t.priority == TicketPriority.MEDIUM)}")
    print(f"   • Low Priority: {sum(1 for t in ticket_count if t.priority == TicketPriority.LOW)}")
    
    print(f"\n🔄 Recovery Actions: {len(action_count)}")
    print(f"   • Sent: {sum(1 for a in action_count if a.status == ActionStatus.SENT)}")
    print(f"   • Pending: {sum(1 for a in action_count if a.status == ActionStatus.PENDING)}")
    
    print(f"\n🤖 Agent Decisions: {len(decision_count)}")
    print(f"   • Public Response: {sum(1 for d in decision_count if d.decision_type == DecisionType.RESPOND_PUBLIC)}")
    print(f"   • Private Recovery: {sum(1 for d in decision_count if d.decision_type == DecisionType.RECOVER_PRIVATE)}")
    print(f"   • Escalate: {sum(1 for d in decision_count if d.decision_type == DecisionType.ESCALATE)}")
    
    print("\n" + "="*60)
    print("✅ Demo data seeding completed successfully!")
    print("="*60)
    print("\n📝 Login Credentials:")
    for org in org_count:
        print(f"\n{org.name}:")
        print(f"  Admin: admin@{org.domain} / demo123")
        print(f"  User:  user@{org.domain} / demo123")
    print("\n")


async def seed_demo_data(clear_existing: bool = False):
    """Main function to seed all demo data"""
    async with AsyncSessionLocal() as session:
        try:
            if clear_existing:
                await clear_demo_data(session)
            
            print("\n🌱 Starting demo data seeding...")
            print("="*60)
            
            # Create data in order of dependencies
            organizations = await create_organizations(session)
            users = await create_users(session, organizations)
            customers = await create_customers(session, organizations)
            reviews = await create_reviews(session, organizations, customers)
            tickets = await create_support_tickets(session, organizations, customers)
            actions = await create_recovery_actions(session, organizations, customers, reviews)
            decisions = await create_agent_decisions(session, organizations, reviews)
            
            # Print summary
            await print_summary(session)
            
        except Exception as e:
            print(f"\n❌ Error seeding demo data: {e}")
            await session.rollback()
            raise


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Seed demo data for Revive AI")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing demo data before seeding"
    )
    parser.add_argument(
        "--environment",
        default="development",
        choices=["development", "staging"],
        help="Target environment (default: development)"
    )
    
    args = parser.parse_args()
    
    # Safety check for production
    if args.environment == "production":
        print("❌ Cannot seed demo data in production environment!")
        sys.exit(1)
    
    print(f"\n🎯 Target Environment: {args.environment}")
    
    # Run seeding
    asyncio.run(seed_demo_data(clear_existing=args.clear))


if __name__ == "__main__":
    main()
