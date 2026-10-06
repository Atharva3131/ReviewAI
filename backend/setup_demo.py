#!/usr/bin/env python3
"""
Setup script for ReviewAI demo
- Initializes database
- Loads demo knowledge base
- Trains ML models
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.database import engine, Base
from app.services.knowledge_service import KnowledgeService
from app.services.ml_churn_model import get_ml_churn_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database():
    """Initialize database tables"""
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables created")
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {e}")
        raise


async def setup_ml_models():
    """Train or load ML models"""
    logger.info("Setting up ML models...")
    try:
        ml_model = await get_ml_churn_model()
        logger.info("✓ ML churn model ready")
    except Exception as e:
        logger.error(f"✗ Failed to setup ML model: {e}")
        raise


async def load_demo_knowledge():
    """Load demo knowledge base"""
    logger.info("Loading demo knowledge base...")
    try:
        knowledge_service = KnowledgeService()
        knowledge = await knowledge_service.get_default_knowledge()
        logger.info(f"✓ Demo knowledge loaded ({len(knowledge)} categories)")
        for category, items in knowledge.items():
            logger.info(f"  - {category}: {len(items)} items")
    except Exception as e:
        logger.error(f"✗ Failed to load knowledge: {e}")
        raise


async def main():
    """Run all setup steps"""
    logger.info("=" * 60)
    logger.info("ReviewAI Demo Setup")
    logger.info("=" * 60)

    try:
        await setup_database()
        await setup_ml_models()
        await load_demo_knowledge()

        logger.info("=" * 60)
        logger.info("✓ Setup complete!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Set DATABASE_URL if not using default")
        logger.info("2. Run: uvicorn app.main:app --reload")
        logger.info("3. Open: http://localhost:8000/api/v1/demo/demo-status")
        logger.info("4. Test: POST to /api/v1/demo/ingest-demo-review")

    except Exception as e:
        logger.error(f"\n✗ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
