"""
Quick script to recalculate urgency for existing reviews
Run this from the backend directory: python fix_urgency.py
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from app.core.database import get_async_db_context
from app.models.review import Review
from app.services.urgency_service import UrgencyService


async def fix_urgency_levels():
    """Recalculate urgency levels for all reviews"""
    try:
        async with get_async_db_context() as db:
            # Get all reviews
            result = await db.execute(select(Review))
            reviews = result.scalars().all()
            
            print(f"\nFound {len(reviews)} reviews to update\n")
            
            for review in reviews:
                # Recalculate urgency
                urgency_result = await UrgencyService.classify_urgency(
                    content=review.content,
                    rating=review.rating,
                    sentiment_score=float(review.sentiment_score) if review.sentiment_score else None,
                    title=None
                )
                
                old_urgency = review.urgency_level
                new_urgency = urgency_result["urgency_level"]
                
                review.urgency_level = new_urgency
                
                print(f"✓ Review '{review.customer_name}' (Rating: {review.rating}★): {old_urgency} → {new_urgency}")
            
            await db.commit()
            print(f"\n{'='*50}")
            print("✓ All {len(reviews)} reviews updated successfully!")
            print(f"{'='*50}\n")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*50)
    print("Fixing urgency levels for all reviews...")
    print("="*50)
    asyncio.run(fix_urgency_levels())

