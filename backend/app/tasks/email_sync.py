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
        # Auto-trigger AI processing immediately after sync finishes
        await _async_process_ai_internal(user_id)
        # Auto-trigger Ghost Detection (Agent B) after AI processing
        await _async_detect_ghosted(user_id)
        # Observe replies on sent outreach threads
        await _async_observe_outcomes(user_id)
    finally:
        # CRITICAL: Dispose engine before asyncio.run() closes the loop.
        # Without this, asyncpg connections from this loop stay in the pool
        # and the next task's new loop finds dead connections -> crash.
        await engine.dispose()


async def _async_process_ai_internal(user_id: UUID):
    """Internal implementation of AI email processing (no engine disposal)."""
    from app.database import async_session_maker
    from app.models import PendingApplication, Application, User
    from app.services.ai_parser import AIParser
    from app.services.action_extractor import ActionExtractor
    from app.utils.email_utils import strip_email_thread
    from sqlalchemy import select
    from datetime import date
    from app.models.event import Event
    from datetime import datetime

    async with async_session_maker() as db:
        user_stmt = select(User).where(User.id == user_id)
        user = (await db.execute(user_stmt)).scalars().first()
        user_email = user.email if user else None

        query = select(PendingApplication).where(
            PendingApplication.user_id == user_id,
            PendingApplication.status == "pending"
        )
        result = await db.execute(query)
        pending_apps = result.scalars().all()

        if not pending_apps:
            logger.info(f"[AI] No pending apps for user {user_id}")
            return

        # Lock these pending apps by marking them as processing
        for pending in pending_apps:
            pending.status = "processing"
        await db.commit()
        
        logger.info(f"[AI] Locked {len(pending_apps)} apps for processing")

        parser = AIParser()
        action_extractor = ActionExtractor()
        added = 0
        discarded = 0


        for pending in pending_apps:
            try:
                snippet = strip_email_thread(pending.email_snippet or '')
                email_data = {
                    'subject': pending.email_subject,
                    'snippet': snippet,
                    'body_preview': snippet
                }

                llm_result = await parser.process_with_llm(email_data)

                if llm_result and llm_result.get('action') == 'add_to_tracker':
                    company_name = (llm_result.get('company') or pending.parsed_company or "Unknown Company").strip()
                    app_status = llm_result.get('status', 'applied')
                    
                    # Deduplicate: check if an application already exists for this company
                    existing_app_stmt = select(Application).where(
                        Application.user_id == user_id,
                        Application.company_name.ilike(company_name),
                        Application.deleted_at.is_(None)
                    )
                    existing_app_result = await db.execute(existing_app_stmt)
                    existing_app = existing_app_result.scalars().first()

                    if existing_app:
                        # Update existing application's status instead of creating duplicate
                        # Upgrade status if needed
                        if app_status != 'applied':
                            existing_app.status = app_status
                            existing_app.status_updated_at = datetime.utcnow()
                        
                        # Update applied_date if this email is older than current applied_date
                        new_applied_date = pending.email_date.date() if pending.email_date else date.today()
                        if existing_app.applied_date > new_applied_date:
                            existing_app.applied_date = new_applied_date
                            logger.info(f"[AI] Backdated applied_date for {company_name} to {new_applied_date}")

                        app_to_use = existing_app
                        logger.info(f"[AI] Linked to existing: {company_name} (status: {app_status})")
                    else:
                        new_app = Application(
                            user_id=user_id,
                            company_name=company_name,
                            role_title=llm_result.get('role') or pending.parsed_role or "Unknown Role",
                            job_url=pending.parsed_job_url,
                            status=app_status,
                            applied_date=pending.email_date.date() if pending.email_date else date.today(),
                            status_updated_at=pending.email_date or datetime.utcnow(),
                            source="gmail_ai",
                            email_subject=pending.email_subject,
                            email_snippet=pending.email_snippet,
                            email_from=pending.email_from
                        )
                        db.add(new_app)
                        await db.flush() # Ensure new_app.id is generated
                        app_to_use = new_app
                        added += 1
                        logger.info(f"[AI] Added new: {company_name}")
                    
                    # Batch commit for visibility (e.g. every 5 new/updated apps)
                    if (added + discarded) % 5 == 0:
                        await db.commit()
                        logger.info(f"[AI] Batch commit at {added + discarded} processed items")
                    
                    # Always record an 'email_linked' event for history (if not already recorded)
                    
                    # Check if this email was already linked as an event
                    existing_event_stmt = select(Event).where(
                        Event.application_id == app_to_use.id,
                        Event.data['email_id'].astext == pending.email_id
                    )
                    existing_event = (await db.execute(existing_event_stmt)).scalars().first()
                    
                    if not existing_event:
                        email_event = Event(
                            application_id=app_to_use.id,
                            event_type="email_linked",
                            title=f"{'Sent' if pending.source == 'cold_email' else 'Received'}: {pending.email_subject}",
                            description=pending.email_snippet,
                            data={
                                "email_id": pending.email_id,
                                "from": pending.email_from,
                                "date": str(pending.email_date),
                                "source": pending.source or "gmail_sync"
                            },
                            created_at=pending.email_date or datetime.utcnow()
                        )
                        db.add(email_event)
                        logger.info(f"[AI] Recorded event for email: {pending.email_subject[:30]}")
                    
                    # Agent A: Action Extraction
                    is_sent_by_user = False
                    if user_email and pending.email_from and user_email.lower() in pending.email_from.lower():
                        is_sent_by_user = True

                    if not is_sent_by_user:
                        await action_extractor.extract_and_record(
                            db=db,
                            application_id=app_to_use.id,
                            email_subject=pending.email_subject,
                            email_body=pending.email_snippet or "",
                            email_id=pending.email_id,
                            company=company_name,
                            role=llm_result.get('role') or pending.parsed_role,
                            email_timestamp=str(pending.email_date) if pending.email_date else None,
                        )
                    else:
                        logger.info(f"[AI] Skipping action extraction: email sent by user ({user_email})")
                    
                    pending.status = "confirmed"

                elif llm_result and llm_result.get('action') == 'discard':
                    pending.status = "rejected"
                    discarded += 1
                else:
                    # If llm_result is None (e.g. rate limit exhausted), revert to pending for next batch
                    pending.status = "pending"
                    logger.warning(f"[AI] Reverting {pending.id} to pending due to LLM failure")

            except Exception as e:
                logger.error(f"[AI] Error processing {pending.id}: {e}")
                pending.status = "pending"
                continue

        await db.commit()
        logger.info(f"[AI] Completed: {added} added, {discarded} discarded")


async def _async_process_ai(user_id: UUID):
    """Async implementation of AI email processing."""
    from app.database import engine
    try:
        await _async_process_ai_internal(user_id)
    finally:
        await engine.dispose()


async def _async_observe_outcomes(user_id: UUID):
    """Detect replies on sent outreach threads."""
    from app.database import async_session_maker, engine
    from app.services.outcome_observer import OutcomeObserver

    try:
        async with async_session_maker() as db:
            observer = OutcomeObserver()
            count = await observer.observe_replies_for_user(db, user_id)
            await db.commit()
            if count:
                logger.info("[OUTCOMES] Recorded %s replies for user %s", count, user_id)
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
