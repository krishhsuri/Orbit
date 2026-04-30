import asyncio
import os
import sys

# Add backend dir to path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.database import async_session_maker
from app.models.application import Application, APPLICATION_STATUSES
from collections import defaultdict

# Priority map to decide which duplicate to keep
STATUS_PRIORITY = {status: idx for idx, status in enumerate(APPLICATION_STATUSES)}

async def run_cleanup():
    print("Starting duplicate cleanup...")
    async with async_session_maker() as db:
        # Get all applications
        stmt = select(Application).where(Application.deleted_at.is_(None))
        result = await db.execute(stmt)
        apps = result.scalars().all()

        # Group by (user_id, company_name lowercase)
        grouped_apps = defaultdict(list)
        for app in apps:
            key = (str(app.user_id), app.company_name.lower().strip())
            grouped_apps[key].append(app)

        deleted_count = 0
        for key, duplicates in grouped_apps.items():
            if len(duplicates) > 1:
                print(f"Found {len(duplicates)} duplicates for {duplicates[0].company_name}")
                
                # Sort by status priority (highest first), then by most recently updated
                duplicates.sort(key=lambda a: (
                    STATUS_PRIORITY.get(a.status, -1),
                    a.status_updated_at.timestamp() if a.status_updated_at else 0
                ), reverse=True)

                # Keep the first one (highest priority)
                keep_app = duplicates[0]
                delete_apps = duplicates[1:]

                # Delete the rest
                for app in delete_apps:
                    print(f"  -> Deleting duplicate ID: {app.id} (Status: {app.status})")
                    await db.delete(app)
                    deleted_count += 1
                
                print(f"  -> Keeping ID: {keep_app.id} (Status: {keep_app.status})")

        if deleted_count > 0:
            await db.commit()
            print(f"Cleanup complete. Deleted {deleted_count} duplicates.")
        else:
            print("No duplicates found.")

if __name__ == "__main__":
    asyncio.run(run_cleanup())
