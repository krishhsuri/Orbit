import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import update, select
from app.database import async_session_maker
from app.models import User
from app.tasks.email_sync import _async_email_sync

async def run():
    print("Preparing to sync old cold emails non-destructively...")
    async with async_session_maker() as db:
        # Reset only the sent email sync token so it fetches from up to 60 days ago
        await db.execute(update(User).values(
            gmail_last_synced_sent_id=None
        ))
        await db.commit()
        
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            print(f"Starting sync for user {user.email}...")
            user_id = user.id
        else:
            print("No user found! Please log in first.")
            return

    # Trigger the sync and AI processing pipeline
    try:
        await _async_email_sync(user_id)
        print("Sync complete! Check your pending applications for newly discovered cold emails.")
    except Exception as e:
        print(f"Error during sync: {e}")

if __name__ == "__main__":
    asyncio.run(run())