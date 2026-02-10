"""Email sync and AI processing background tasks."""
import asyncio
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

from app.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, name="app.tasks.email_sync.sync_emails")
def sync_emails(self, user_id: str):
    """Celery task for email sync - fetches emails from Gmail."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_email_sync(UUID(user_id)))
        logger.info(f"[CELERY] Email sync completed for user {user_id}")
    except Exception as exc:
        logger.error(f"[CELERY] Email sync failed for {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.email_sync.process_ai_emails")
def process_ai_emails(self, user_id: str):
    """Celery task for AI email processing with Groq LLM."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_process_ai(UUID(user_id)))
        logger.info(f"[CELERY] AI processing completed for user {user_id}")
    except Exception as exc:
        logger.error(f"[CELERY] AI processing failed for {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="app.tasks.email_sync.detect_ghosted")
def detect_ghosted_task(self, user_id: str):
    """Celery task for detecting ghosted applications."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_detect_ghosted(UUID(user_id)))
        logger.info(f"[CELERY] Ghost detection completed for user {user_id}")
    except Exception as exc:
        logger.error(f"[CELERY] Ghost detection failed for {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)


# ============== Async Implementations ==============

async def _async_email_sync(user_id: UUID):
    """Async implementation of email sync."""
    from app.routers.gmail import sync_emails_task
    await sync_emails_task(user_id, None)


async def _async_process_ai(user_id: UUID):
    """Async implementation of AI email processing."""
    from app.database import async_session_maker
    from app.models import PendingApplication, Application
    from app.services.ai_parser import AIParser
    from sqlalchemy import select
    from datetime import date
    
    async with async_session_maker() as db:
        # Get pending applications
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


async def _async_detect_ghosted(user_id: UUID):
    """Async implementation of ghost detection."""
    from app.database import async_session_maker
    from app.ml.detection.ghost_detector import GhostDetector
    
    async with async_session_maker() as db:
        detector = GhostDetector(db)
        await detector.detect_and_mark_ghosted(user_id)
