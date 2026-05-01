"""Full database reset for clean re-ingestion."""
import asyncio
from app.database import async_session_maker
from sqlalchemy import text

async def reset_all():
    async with async_session_maker() as db:
        # Delete in FK-safe order (children first)
        tables = [
            ("follow_up_results", "Agent B evaluations"),
            ("events", "timeline events"),
            ("notes", "application notes"),
            ("application_tags", "tag links"),
            ("application_emails", "email links"),
            ("pending_applications", "pending emails"),
            ("applications", "confirmed applications"),
        ]

        for table, label in tables:
            result = await db.execute(text(f"DELETE FROM {table}"))
            print(f"  Cleared {table}: {result.rowcount} {label} deleted")

        # Reset sync markers on users
        await db.execute(text(
            "UPDATE users SET gmail_last_synced_email_id = NULL, gmail_last_synced_sent_id = NULL"
        ))
        print("  Reset Gmail sync markers")

        await db.commit()
        print("\nDone - database is clean.")

asyncio.run(reset_all())
