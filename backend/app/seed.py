"""
Seed script to create demo user for development
Run: python -m app.seed
"""

import asyncio
from uuid import UUID

from app.database import async_session_maker
from app.models import User


DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def seed_demo_user():
    """Create demo user if not exists"""
    async with async_session_maker() as session:
        try:
            # Check if user exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.id == DEMO_USER_ID)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"✓ Demo user already exists: {existing.email}")
                return
            
            # Create demo user
            demo_user = User(
                id=DEMO_USER_ID,
                email="demo@orbit.dev",
                name="Demo User",
                preferences={"weekly_goal": 10},
            )
            session.add(demo_user)
            await session.commit()
            print("✓ Created demo user: demo@orbit.dev")
            
        except Exception as e:
            print(f"✗ Error creating demo user: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_demo_user())
