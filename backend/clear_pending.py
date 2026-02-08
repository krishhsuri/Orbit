"""
Quick script to clear pending applications from database.
Run: python clear_pending.py
"""
import asyncio
from app.database import async_session_maker
from sqlalchemy import text

async def clear_pending():
    async with async_session_maker() as db:
        # Delete all pending applications
        result = await db.execute(text("DELETE FROM pending_applications"))
        await db.commit()
        print(f"✅ Deleted {result.rowcount} pending applications")

if __name__ == "__main__":
    asyncio.run(clear_pending())
