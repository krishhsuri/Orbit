"""ARQ worker tasks for durable outreach execution and scheduled jobs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

logger = logging.getLogger(__name__)


async def execute_outreach_send(ctx, outreach_action_id: str) -> dict:
    from app.services.outreach_executor import OutreachExecutor

    logger.info("ARQ executing outreach send %s", outreach_action_id)
    return await OutreachExecutor().execute(UUID(outreach_action_id))


async def cron_scan_for_follow_ups(ctx) -> dict:
    """All-users Agent B scan with 6h skip (periodic path)."""
    from app.tasks.cleanup import scan_for_follow_ups

    logger.info("ARQ cron: scan_for_follow_ups")
    return await scan_for_follow_ups()


async def cron_purge_old_rejected(ctx) -> dict:
    from app.tasks.cleanup import purge_old_rejected

    logger.info("ARQ cron: purge_old_rejected")
    return await purge_old_rejected()


async def cron_enforce_pending_cap(ctx) -> dict:
    from app.tasks.cleanup import enforce_pending_cap

    logger.info("ARQ cron: enforce_pending_cap")
    return await enforce_pending_cap()


async def cron_reap_stale_outreach(ctx) -> dict:
    """
    Re-enqueue pending_undo rows whose undo window has passed.

    Covers enqueue failures and undo_window_active skips that never got a
    follow-up job.
    """
    from app.database import async_session_maker
    from app.models.outreach_action import OutreachAction
    from app.services.outreach_queue import OutreachQueueService

    now = datetime.now(timezone.utc)
    requeued = 0
    async with async_session_maker() as db:
        stmt = select(OutreachAction).where(
            OutreachAction.status == "pending_undo",
            OutreachAction.undo_until.is_not(None),
            OutreachAction.undo_until <= now,
        )
        actions = (await db.execute(stmt)).scalars().all()
        queue = OutreachQueueService()
        for action in actions:
            await queue.reenqueue_ready(action.id)
            requeued += 1
        await db.commit()

    logger.info("ARQ cron: reap_stale_outreach requeued=%s", requeued)
    return {"requeued": requeued}


async def startup(ctx) -> None:
    logger.info("ARQ worker starting")


async def shutdown(ctx) -> None:
    from app.database import engine

    await engine.dispose()
    logger.info("ARQ worker shutdown")
