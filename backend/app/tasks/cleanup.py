"""
Periodic cleanup tasks for Orbit.
Runs via Celery Beat to maintain data hygiene.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="cleanup.purge_old_rejected")
def purge_old_rejected():
    """Delete rejected pending applications older than 30 days."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_async_purge_rejected())
        return result
    finally:
        loop.close()


async def _async_purge_rejected():
    from app.database import async_session_maker
    from app.models import PendingApplication
    from sqlalchemy import delete

    cutoff = datetime.utcnow() - timedelta(days=30)

    async with async_session_maker() as db:
        stmt = delete(PendingApplication).where(
            PendingApplication.status == "rejected",
            PendingApplication.created_at < cutoff,
        )
        result = await db.execute(stmt)
        await db.commit()
        count = result.rowcount
        logger.info(f"[CLEANUP] Purged {count} rejected pending apps older than 30 days")
        return {"purged_rejected": count}


@celery_app.task(name="cleanup.enforce_pending_cap")
def enforce_pending_cap():
    """Enforce the 200 pending email cap for all users."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_async_enforce_cap())
        return result
    finally:
        loop.close()


async def _async_enforce_cap():
    from app.database import async_session_maker
    from app.models import User, PendingApplication
    from sqlalchemy import select, delete, func

    MAX_PENDING = 200

    async with async_session_maker() as db:
        # Find users that exceed the cap
        over_cap_q = (
            select(PendingApplication.user_id, func.count().label("cnt"))
            .group_by(PendingApplication.user_id)
            .having(func.count() > MAX_PENDING)
        )
        rows = (await db.execute(over_cap_q)).all()

        total_deleted = 0
        for user_id, cnt in rows:
            excess = cnt - MAX_PENDING
            oldest_q = (
                select(PendingApplication.id)
                .where(PendingApplication.user_id == user_id)
                .order_by(PendingApplication.email_date.asc())
                .limit(excess)
            )
            oldest_ids = (await db.execute(oldest_q)).scalars().all()
            if oldest_ids:
                await db.execute(
                    delete(PendingApplication).where(PendingApplication.id.in_(oldest_ids))
                )
                total_deleted += len(oldest_ids)

        await db.commit()
        logger.info(f"[CLEANUP] Cap enforcement: deleted {total_deleted} excess pending emails across {len(rows)} users")
        return {"deleted": total_deleted, "users_affected": len(rows)}
