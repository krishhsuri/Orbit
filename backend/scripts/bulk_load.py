import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, update, select
from app.database import async_session_maker
from app.models import Application, PendingApplication, Lead, Event, Note, User
from app.tasks.email_sync import _async_email_sync

async def run():
    print("Clearing database...")
    async with async_session_maker() as db:
        await db.execute(delete(Event))
        await db.execute(delete(Note))
        await db.execute(delete(Application))
        await db.execute(delete(PendingApplication))
        await db.execute(delete(Lead))
        
        # Reset sync tokens for all users so it fetches from 60 days ago
        await db.execute(update(User).values(
            gmail_last_synced_email_id=None,
            gmail_last_synced_sent_id=None
        ))
        
        await db.commit()
        
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            print(f"Starting bulk 60-day sync for user {user.email}...")
            user_id = user.id
        else:
            print("No user found! Please log in first.")
            return

    # Trigger the sync and AI processing pipeline
    try:
        await _async_email_sync(user_id)
        print("Bulk sync and AI processing complete! Check your Kanban board.")
    except Exception as e:
        print(f"Error during sync: {e}")

if __name__ == "__main__":
    asyncio.run(run())
