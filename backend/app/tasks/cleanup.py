"""
Periodic cleanup tasks for Orbit.
Runs via Celery Beat to maintain data hygiene.
"""

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def purge_old_rejected():
    """Delete rejected pending applications older than 30 days."""
    return await _async_purge_rejected()

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


async def enforce_pending_cap():
    """Enforce the 200 pending email cap for all users."""
    return await _async_enforce_cap()

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

async def scan_for_follow_ups():
    """Scan all active applications to evaluate if they need follow-ups."""
    return await _async_scan_follow_ups()

async def _async_scan_follow_ups():
    from app.database import async_session_maker
    from app.models import Application
    from sqlalchemy import select
    from app.services.follow_up_agent import FollowUpAgent

    async with async_session_maker() as db:
        stmt = select(Application.id).where(Application.deleted_at.is_(None))
        result = await db.execute(stmt)
        application_ids = result.scalars().all()

        agent = FollowUpAgent()
        evaluated = 0
        follow_ups_needed = 0

        for app_id in application_ids:
            try:
                evaluation = await agent.evaluate_application(db, app_id)
                if evaluation and evaluation.get("should_follow_up"):
                    follow_ups_needed += 1
                evaluated += 1
            except Exception as e:
                logger.error(f"[FOLLOW-UP] Error evaluating application {app_id}: {e}")

        logger.info(f"[FOLLOW-UP] Evaluated {evaluated} applications, {follow_ups_needed} need follow-ups")
        return {"evaluated": evaluated, "follow_ups_needed": follow_ups_needed}

