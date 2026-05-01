"""
Periodic cleanup tasks for Orbit.
Runs via Celery Beat to maintain data hygiene.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

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
    """Scan all active applications and persist Agent B evaluations."""
    return await _async_scan_follow_ups()

async def _async_scan_follow_ups():
    """
    Scheduled Agent B trigger (per whiteboard architecture).
    
    Flow:
    1. Fetch all active applications across all users
    2. Skip recently evaluated ones (< 6 hours ago)
    3. Run FollowUpAgent.evaluate_application() on each
    4. Upsert results into follow_up_results table
    
    The /agents page then simply reads from this table — no LLM calls on page load.
    """
    from app.database import async_session_maker
    from app.models import Application
    from app.models.follow_up_result import FollowUpResult
    from sqlalchemy import select
    from app.services.follow_up_agent import FollowUpAgent

    async with async_session_maker() as db:
        # Only evaluate active applications (not deleted, not terminal status)
        stmt = (
            select(Application)
            .where(Application.deleted_at.is_(None))
            .where(Application.status.notin_(["rejected", "offer", "accepted", "withdrawn"]))
        )
        result = await db.execute(stmt)
        applications = result.scalars().all()

        if not applications:
            logger.info("[FOLLOW-UP] No eligible applications to scan")
            return {"evaluated": 0, "follow_ups_needed": 0}

        # Skip apps that were evaluated recently (< 6 hours)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
        existing_results_stmt = (
            select(FollowUpResult.application_id, FollowUpResult.evaluated_at)
            .where(FollowUpResult.evaluated_at > cutoff)
        )
        recent_evals = {
            row.application_id: row.evaluated_at
            for row in (await db.execute(existing_results_stmt)).all()
        }

        agent = FollowUpAgent()
        evaluated = 0
        follow_ups_needed = 0

        for app in applications:
            # Skip recently evaluated
            if app.id in recent_evals:
                continue

            try:
                evaluation = await agent.evaluate_application(db, app.id)
                if not evaluation:
                    continue

                now = datetime.now(timezone.utc)

                # Upsert: check if result already exists for this application
                existing_stmt = select(FollowUpResult).where(
                    FollowUpResult.application_id == app.id
                )
                existing = (await db.execute(existing_stmt)).scalar_one_or_none()

                if existing:
                    # Update existing result
                    existing.should_follow_up = evaluation.get("should_follow_up", False)
                    existing.days_since_last_contact = evaluation.get("days_since_last_contact", 0)
                    existing.decision_reason = evaluation.get("decision_reason", "")
                    existing.email_draft = evaluation.get("email_draft")
                    existing.evaluated_at = now
                    # Don't reset dismissed — if user dismissed it, respect that
                    # unless the evaluation changed from False to True
                    if not existing.should_follow_up:
                        existing.dismissed = False
                else:
                    # Create new result
                    new_result = FollowUpResult(
                        application_id=app.id,
                        user_id=app.user_id,
                        should_follow_up=evaluation.get("should_follow_up", False),
                        days_since_last_contact=evaluation.get("days_since_last_contact", 0),
                        decision_reason=evaluation.get("decision_reason", ""),
                        email_draft=evaluation.get("email_draft"),
                        evaluated_at=now,
                        dismissed=False,
                    )
                    db.add(new_result)

                if evaluation.get("should_follow_up"):
                    follow_ups_needed += 1
                evaluated += 1

            except Exception as e:
                logger.error(f"[FOLLOW-UP] Error evaluating application {app.id}: {e}")

        await db.commit()
        logger.info(f"[FOLLOW-UP] Evaluated {evaluated} applications, {follow_ups_needed} need follow-ups")
        return {"evaluated": evaluated, "follow_ups_needed": follow_ups_needed}
