"""
Reset demo user password
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def reset_password():
    """Reset demo user password"""
    print("🔑 Resetting demo user password...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Find the demo user
            result = await session.execute(
                select(User).where(User.email == "demo@restaurant.com")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ Demo user not found!")
                return
            
            # Update password
            new_password = "demo123"
            user.password_hash = pwd_context.hash(new_password)
            
            await session.commit()
            
            print("✅ Password reset successfully!")
            print(f"\n📧 Email: demo@restaurant.com")
            print(f"🔐 Password: {new_password}")
            print(f"\n🎯 Login at: http://localhost:3000/login")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(reset_password())
