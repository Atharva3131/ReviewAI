"""
Knowledge Base Service (Category & Policy Lookup)
Store and retrieve business knowledge for response grounding
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import BusinessKnowledge

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Simple knowledge base management and retrieval"""

    def __init__(self):
        self.service_version = "1.0.0"
        logger.info("KnowledgeService initialized")

    async def get_knowledge_by_category(
        self,
        db: AsyncSession,
        category: str,
        limit: int = 5,
    ) -> list[BusinessKnowledge]:
        """
        Get knowledge items by category

        Args:
            db: Database session
            category: Knowledge category (brand_voice, policies, faqs, etc.)
            limit: Max results

        Returns:
            List of knowledge items
        """
        try:
            stmt = (
                select(BusinessKnowledge)
                .where(BusinessKnowledge.category == category)
                .limit(limit)
            )
            result = await db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to retrieve knowledge: {e}")
            return []

    async def ingest_knowledge(
        self,
        db: AsyncSession,
        category: str,
        items: list[dict],
    ) -> int:
        """
        Ingest knowledge items

        Args:
            db: Database session
            category: Knowledge category
            items: List of {title, content} dicts

        Returns:
            Number of items ingested
        """
        try:
            count = 0
            for item in items:
                knowledge = BusinessKnowledge(
                    category=category,
                    title=item["title"],
                    content=item["content"],
                    meta=item.get("metadata", {}),
                )
                db.add(knowledge)
                count += 1

            await db.commit()
            logger.info(f"Ingested {count} knowledge items in category {category}")
            return count

        except Exception as e:
            logger.error(f"Failed to ingest knowledge: {e}")
            await db.rollback()
            return 0

    @staticmethod
    async def get_default_knowledge() -> dict[str, list[dict]]:
        """Get default business knowledge for demo"""
        return {
            "brand_voice": [
                {
                    "title": "Professional but Warm Tone",
                    "content": "Always address the customer by name when possible. Use conversational but professional language. Show genuine empathy for their situation.",
                    "metadata": {"priority": "high"},
                },
                {
                    "title": "Avoid Promises You Cannot Keep",
                    "content": "Never guarantee specific outcomes. Use phrases like 'we'll do our best' or 'we'll investigate this'. Always follow company policy.",
                    "metadata": {"priority": "critical"},
                },
            ],
            "policies": [
                {
                    "title": "Refund Policy",
                    "content": "Refunds available within 30 days of purchase for defective items. No questions asked within 14 days. Shipping costs not refundable.",
                    "metadata": {"applies_to": "all_products"},
                },
                {
                    "title": "Escalation Policy",
                    "content": "Any issue rated 1-2 stars automatically escalates to management. Safety concerns escalate to compliance team immediately.",
                    "metadata": {"applies_to": "all_reviews"},
                },
            ],
            "faqs": [
                {
                    "title": "When will I receive my order?",
                    "content": "Standard shipping takes 5-7 business days. Expedited shipping available for 2-3 days.",
                    "metadata": {"category": "shipping"},
                },
                {
                    "title": "How do I return an item?",
                    "content": "Use the return label in your shipment, or request one online. Returns accepted within 30 days.",
                    "metadata": {"category": "returns"},
                },
            ],
            "recovery_templates": [
                {
                    "title": "Service Issue Recovery",
                    "content": "We sincerely apologize for the service issue you experienced. We'd like to make this right. We're offering a 20% discount on your next order as a gesture of goodwill.",
                    "metadata": {"applies_to": "service_issues"},
                },
                {
                    "title": "Delivery Delay Recovery",
                    "content": "We regret that your delivery was delayed. To apologize, we're extending your return window and offering free expedited shipping on your next order.",
                    "metadata": {"applies_to": "delivery_issues"},
                },
            ],
        }
