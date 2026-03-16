"""Email sync and AI processing background tasks."""
import asyncio
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# ============== Async Implementations ==============

async def _async_email_sync(user_id: UUID):
    """Async implementation of email sync."""
    from app.database import engine
    from app.routers.gmail import sync_emails_task
    try:
        await sync_emails_task(user_id, None)
    finally:
        # CRITICAL: Dispose engine before asyncio.run() closes the loop.
        # Without this, asyncpg connections from this loop stay in the pool
        # and the next task's new loop finds dead connections -> crash.
        await engine.dispose()


async def _async_process_ai(user_id: UUID):
    """Async implementation of AI email processing."""
    from app.database import async_session_maker, engine
    from app.models import PendingApplication, Application
    from app.services.ai_parser import AIParser
    from sqlalchemy import select
    from datetime import date

    try:
        async with async_session_maker() as db:
            query = select(PendingApplication).where(
                PendingApplication.user_id == user_id,
                PendingApplication.status == "pending"
            )
            result = await db.execute(query)
            pending_apps = result.scalars().all()

            if not pending_apps:
                logger.info(f"[AI] No pending apps for user {user_id}")
                return

            parser = AIParser()
            added = 0
            discarded = 0

            for pending in pending_apps:
                try:
                    email_data = {
                        'subject': pending.email_subject,
                        'snippet': pending.email_snippet or '',
                        'body_preview': pending.email_snippet or ''
                    }

                    llm_result = await parser.process_with_llm(email_data)

                    if llm_result and llm_result.get('action') == 'add_to_tracker':
                        new_app = Application(
                            user_id=user_id,
                            company_name=llm_result.get('company') or pending.parsed_company or "Unknown Company",
                            role_title=llm_result.get('role') or pending.parsed_role or "Unknown Role",
                            job_url=pending.parsed_job_url,
                            status=llm_result.get('status', 'applied'),
                            applied_date=pending.email_date.date() if pending.email_date else date.today(),
                            source="gmail_ai"
                        )
                        db.add(new_app)
                        pending.status = "confirmed"
                        added += 1
                        logger.info(f"[AI] Added: {new_app.company_name}")

                    elif llm_result and llm_result.get('action') == 'discard':
                        pending.status = "rejected"
                        discarded += 1

                except Exception as e:
                    logger.error(f"[AI] Error processing {pending.id}: {e}")
                    continue

            await db.commit()
            logger.info(f"[AI] Completed: {added} added, {discarded} discarded")
    finally:
        await engine.dispose()


async def _async_detect_ghosted(user_id: UUID):
    """Async implementation of ghost detection."""
    from app.database import async_session_maker, engine
    from app.ml.detection.ghost_detector import GhostDetector

    try:
        async with async_session_maker() as db:
            detector = GhostDetector(db)
            await detector.detect_and_mark_ghosted(user_id)
    finally:
        await engine.dispose()
