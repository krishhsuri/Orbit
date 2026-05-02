import sys
import os
import asyncio
from uuid import UUID

# Add app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import async_session_maker, engine
from app.models import PendingApplication, User
from app.tasks.email_sync import _async_process_ai_internal
from sqlalchemy import select

async def process_all_pending():
    """Find all users with pending applications and process them."""
    print("Starting manual processing of all pending applications...")
    
    async with async_session_maker() as db:
        # 1. Get all unique user IDs that have pending applications
        stmt = select(PendingApplication.user_id).where(
            PendingApplication.status == "pending"
        ).distinct()
        result = await db.execute(stmt)
        user_ids = result.scalars().all()
        
        if not user_ids:
            print("No pending applications found in the database.")
            return

        print(f"Found pending applications for {len(user_ids)} users.")
        
        for user_id in user_ids:
            print(f"Processing for user: {user_id}")
            try:
                # We use the internal task so we don't dispose the engine multiple times
                await _async_process_ai_internal(user_id)
                print(f"Finished processing for user: {user_id}")
            except Exception as e:
                print(f"Error processing for user {user_id}: {e}")

    print("All processing complete.")

if __name__ == "__main__":
    try:
        asyncio.run(process_all_pending())
    finally:
        # Clean up connections
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(engine.dispose())
        else:
            asyncio.run(engine.dispose())
