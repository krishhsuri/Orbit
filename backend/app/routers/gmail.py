from typing import List, Optional
from uuid import UUID
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, PendingApplication, Application, APPLICATION_STATUSES
from app.schemas.pending_application import PendingApplicationResponse, PendingApplicationUpdate
from app.services.gmail_service import GmailService
from app.services.ai_parser import AIParser
from app.middleware.auth import get_current_user
from email.utils import parsedate_to_datetime
import logging

logger = logging.getLogger(__name__)

MAX_PENDING_PER_USER = 200

router = APIRouter()

async def sync_emails_task(user_id: UUID, db_session_maker):
    """
    Background task to sync emails.
    Fetches emails, auto-filters non-job emails, only stores job-related ones.
    """
    from app.database import async_session_maker
    
    logger.info(f"[SYNC] Starting sync for user {user_id}")
    
    async with async_session_maker() as db:
        try:
            # 1. Fetch User
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                logger.error(f"[SYNC] User {user_id} not found")
                return
            if not user.gmail_sync_enabled:
                logger.error(f"[SYNC] Gmail sync not enabled for user {user.email}")
                return

            logger.info(f"[SYNC] Gmail sync enabled for user {user.email}")
            
            service = GmailService(user, db=None) 
            
            # Run in threadpool (fetch_recent_emails is blocking I/O)
            # Fetch more emails (100) to find at least 10 job-related ones
            import asyncio
            
            last_synced_id = user.gmail_last_synced_email_id
            emails = await asyncio.to_thread(
                service.fetch_recent_emails, 
                max_results=100,
                after_message_id=last_synced_id
            )
            
            logger.info(f"[SYNC] Fetched {len(emails)} emails from Gmail")
            
            if not emails:
                logger.warning("[SYNC] No emails returned from Gmail API")
                return

            # Print first 5 email subjects for debugging
            for i, email in enumerate(emails[:5]):
                logger.debug(f"[SYNC] Email {i+1}: {email.get('subject', 'NO SUBJECT')[:60]}")

            # 2. Process with AI Parser (Quick local ML, no LLM)
            parser = AIParser()
            job_related_count = 0
            skipped_existing = 0
            filtered_out = 0
            
            # Non-job statuses to auto-filter (ONLY truly non-job emails)
            # Keep general_hr and unknown - better to show uncertain emails than miss them
            # Also filter 'not_for_user' - emails where user wasn't in the candidate list
            NON_JOB_STATUSES = {'not_job_related', 'not_for_user'}
            
            for email_data in emails:
                # Check if already processed (by email_id)
                stmt = select(PendingApplication).where(PendingApplication.email_id == email_data['id'])
                existing = await db.execute(stmt)
                if existing.scalar_one_or_none():
                    skipped_existing += 1
                    continue

                # Quick parse - local ML only, no LLM (fast)
                # Pass user email to detect multi-candidate emails where user isn't listed
                parsed = await parser.quick_parse(email_data, user_email=user.email)
                
                # Auto-filter: Skip if not parsed or not job-related
                if not parsed:
                    filtered_out += 1
                    continue
                    
                # Auto-cleanup: Skip non-job-related emails entirely
                status = parsed.get('status', 'unknown')
                if status in NON_JOB_STATUSES:
                    logger.debug(f"[SYNC] FILTERED: {email_data.get('subject', '')[:40]} (status: {status})")
                    filtered_out += 1
                    continue
                
                # Parse actual email date from Date header
                email_date_str = email_data.get('date', '')
                try:
                    parsed_email_date = parsedate_to_datetime(email_date_str)
                except Exception:
                    parsed_email_date = datetime.now()
                
                # This is a job-related email - add to pending queue
                logger.info(f"[SYNC] JOB FOUND: {parsed.get('company')} - {status}")
                pending = PendingApplication(
                    user_id=user.id,
                    email_id=email_data['id'],
                    email_subject=email_data['subject'],
                    email_snippet=email_data['snippet'][:1000] if email_data.get('snippet') else None,
                    email_from=email_data.get('from_address'),  # Capture sender for leads
                    email_date=parsed_email_date,
                    parsed_company=parsed.get('company'),
                    parsed_role=parsed.get('role'),
                    parsed_status=status,
                    parsed_job_url=parsed.get('job_url'),
                    confidence_score=parsed.get('confidence', 0.0),
                    status="pending"
                )
                db.add(pending)
                job_related_count += 1
                
                # Auto-create global Lead for the shared job board
                if parsed.get('company'):
                    from app.models import Lead
                    # Check if lead already exists for this email
                    lead_exists = await db.execute(
                        select(Lead).where(Lead.source_email_id == email_data['id'])
                    )
                    if not lead_exists.scalar_one_or_none():
                        # Detect job site from URL
                        job_site = None
                        job_url = parsed.get('job_url')
                        if job_url:
                            try:
                                from urllib.parse import urlparse
                                domain = urlparse(job_url).hostname or ""
                                domain = domain.replace("www.", "")
                                site_map = {
                                    "linkedin.com": "LinkedIn",
                                    "wellfound.com": "Wellfound",
                                    "indeed.com": "Indeed",
                                    "glassdoor.com": "Glassdoor",
                                    "lever.co": "Lever",
                                    "greenhouse.io": "Greenhouse",
                                    "ziprecruiter.com": "ZipRecruiter",
                                    "monster.com": "Monster",
                                    "dice.com": "Dice",
                                }
                                job_site = site_map.get(domain, domain)
                            except Exception:
                                pass
                        
                        # Extract recruiter info from email from_address
                        from_addr = email_data.get('from_address', '')
                        import re
                        name_match = re.match(r'^([^<]+)\s*<', from_addr)
                        email_match = re.search(r'<([^>]+)>', from_addr) or re.search(r'([^\s]+@[^\s]+)', from_addr)
                        
                        lead = Lead(
                            company=parsed.get('company'),
                            role=parsed.get('role'),
                            job_site=job_site,
                            job_url=job_url,
                            recruiter_name=name_match.group(1).strip() if name_match else None,
                            recruiter_email=email_match.group(1) if email_match else None,
                            source_email_id=email_data['id'],
                            date=parsed_email_date,
                        )
                        db.add(lead)
            
            logger.info(f"[SYNC] Summary: {job_related_count} job-related, {skipped_existing} skipped, {filtered_out} filtered out")
            
            if job_related_count > 0:
                user.gmail_last_sync_at = datetime.now()
                # Track the newest email ID for incremental sync
                if emails:
                    user.gmail_last_synced_email_id = emails[0]['id']
                await db.commit()
                logger.info(f"[SYNC] Committed: {job_related_count} job-related emails")
            else:
                # Still update last sync time and newest ID even if no job emails found
                user.gmail_last_sync_at = datetime.now()
                if emails:
                    user.gmail_last_synced_email_id = emails[0]['id']
                await db.commit()
                logger.info("[SYNC] No job-related emails found")
            
            # Enforce per-user pending email cap
            from sqlalchemy import func
            count_q = select(func.count()).select_from(PendingApplication).where(
                PendingApplication.user_id == user_id
            )
            total = (await db.execute(count_q)).scalar() or 0
            if total > MAX_PENDING_PER_USER:
                excess = total - MAX_PENDING_PER_USER
                # Find the oldest excess IDs
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
                    await db.commit()
                    logger.info(f"[SYNC] Enforced {MAX_PENDING_PER_USER} cap: deleted {len(oldest_ids)} oldest pending emails")
                
        except Exception as e:
            logger.error(f"[SYNC] Error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()

@router.post("/sync")
async def trigger_sync(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger manual email sync via Celery (non-blocking)"""
    if not user.gmail_sync_enabled:
        raise HTTPException(status_code=400, detail="Gmail sync is not enabled")
        
    # Use Celery for true async processing (doesn't block the request)
    from app.tasks.email_sync import sync_emails
    sync_emails.delay(str(user.id))
    
    return {"status": "request_accepted", "message": "Email sync started in background"}

@router.get("/pending", response_model=List[PendingApplicationResponse])
async def list_pending_applications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all pending applications detected from emails"""
    query = select(PendingApplication).where(
        PendingApplication.user_id == user.id,
        PendingApplication.status == "pending"
    ).order_by(PendingApplication.email_date.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/pending/cleanup")
async def cleanup_non_job_related(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove all pending applications with non-job-related status"""
    # Delete entries with not_job_related status only
    stmt = delete(PendingApplication).where(
        PendingApplication.user_id == user.id,
        PendingApplication.parsed_status == 'not_job_related'
    )
    result = await db.execute(stmt)
    await db.commit()
    
    return {
        "message": f"Cleaned up {result.rowcount} non-job-related entries",
        "deleted_count": result.rowcount
    }


@router.post("/pending/process-ai")
async def process_with_ai(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process all pending emails with Groq LLM via Celery (non-blocking).
    LLM decides whether to add to applications or discard.
    """
    # Check if there are pending applications
    query = select(PendingApplication).where(
        PendingApplication.user_id == user.id,
        PendingApplication.status == "pending"
    )
    result = await db.execute(query)
    pending_count = len(result.scalars().all())
    
    if pending_count == 0:
        return {"message": "No pending applications to process", "queued": 0}
    
    # Queue AI processing via Celery (non-blocking)
    from app.tasks.email_sync import process_ai_emails
    process_ai_emails.delay(str(user.id))
    
    return {
        "message": f"AI processing started for {pending_count} emails",
        "queued": pending_count,
        "status": "processing"
    }


@router.post("/pending/{id}/confirm")
async def confirm_application(
    id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Confirm a pending application -> Create real Application"""
    query = select(PendingApplication).where(
        PendingApplication.id == id,
        PendingApplication.user_id == user.id
    )
    result = await db.execute(query)
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Pending application not found")
        
    if pending.status == "confirmed":
        raise HTTPException(status_code=400, detail="Already confirmed")

    # Create new Application
    # Map parsed status to Application status if possible
    app_status = "applied" # Default
    if pending.parsed_status and pending.parsed_status in APPLICATION_STATUSES:
        app_status = pending.parsed_status
        
    new_app = Application(
        user_id=user.id,
        company_name=pending.parsed_company or "Unknown Company",
        role_title=pending.parsed_role or "Unknown Role",
        job_url=pending.parsed_job_url,
        status=app_status,
        applied_date=pending.email_date.date() if pending.email_date else date.today(),
        source="gmail_auto",
        # Preserve email context for the detail page
        email_subject=pending.email_subject,
        email_snippet=pending.email_snippet,
        email_from=pending.email_from,
    )
    
    db.add(new_app)
    
    # Save as positive training example for self-learning
    from app.models.training_example import TrainingExample
    training = TrainingExample(
        email_subject=pending.email_subject,
        email_snippet=pending.email_snippet,
        email_from=pending.email_from or "",
        label="positive",
        user_id=user.id,
    )
    db.add(training)
    
    # Update pending status
    pending.status = "confirmed"
    
    await db.commit()
    await db.refresh(pending)
    
    # Retrain the learned filter with the new example
    from app.ml.classifiers.learned_filter import refresh_learned_model
    await refresh_learned_model()
    
    return {"message": "Application confirmed and created", "application_id": new_app.id}

@router.delete("/pending/{id}")
async def reject_application(
    id: UUID,
    reason: str = "not_for_me",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject/Dismiss a pending application.
    
    reason options:
    - "not_job_email": Not a job-related email (newsletter, spam, promo) → trains as negative
    - "not_for_me": Valid job email but not for this user (multi-candidate) → NO training
    - "wrong_detection": AI misclassified this email → trains as negative
    - "duplicate": Already tracked this application → NO training
    """
    query = select(PendingApplication).where(
        PendingApplication.id == id,
        PendingApplication.user_id == user.id
    )
    result = await db.execute(query)
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Pending application not found")
    
    # Only save as negative training example for reasons that indicate
    # the email is genuinely NOT a job application for the user
    trainable_reasons = {"not_job_email", "wrong_detection", "spam"}
    if reason in trainable_reasons:
        from app.models.training_example import TrainingExample
        training = TrainingExample(
            email_subject=pending.email_subject,
            email_snippet=pending.email_snippet,
            email_from=pending.email_from or "",
            label="negative",
            user_id=user.id,
        )
        db.add(training)
        
    pending.status = "rejected"
    await db.commit()
    
    # Retrain the learned filter if we added training data
    if reason in trainable_reasons:
        from app.ml.classifiers.learned_filter import refresh_learned_model
        await refresh_learned_model()
    
    return {"message": "Pending application rejected"}


@router.post("/detect-ghosted")
async def detect_ghosted_applications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Detect and mark ghosted applications (14+ days without response)"""
    from app.ml.detection.ghost_detector import GhostDetector
    
    detector = GhostDetector(db)
    ghosted_apps = await detector.detect_and_mark_ghosted(user.id)
    
    return {
        "message": f"Marked {len(ghosted_apps)} applications as ghosted",
        "count": len(ghosted_apps),
        "applications": ghosted_apps
    }


@router.get("/ghost-candidates")
async def get_ghost_candidates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Preview applications that would be marked as ghosted (without actually marking them)"""
    from app.ml.detection.ghost_detector import GhostDetector
    
    detector = GhostDetector(db)
    candidates = await detector.get_ghost_candidates(user.id)
    
    return {
        "count": len(candidates),
        "candidates": candidates
    }


@router.get("/pending/{id}/extract-note")
async def extract_note_from_email(
    id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract AI-generated note content from a pending application email.
    Returns structured info for auto-populating note fields.
    """
    # Get the pending application
    query = select(PendingApplication).where(
        PendingApplication.id == id,
        PendingApplication.user_id == user.id
    )
    result = await db.execute(query)
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Pending application not found")
    
    # Use AIParser's LLM client to extract note
    parser = AIParser()
    
    note_data = await parser.llm.extract_note_from_email(
        subject=pending.email_subject,
        body=pending.email_snippet or ""
    )
    
    if not note_data:
        # Fallback to basic info
        return {
            "summary": f"Email from {pending.email_from or 'unknown sender'} regarding {pending.parsed_company or 'job application'}",
            "key_dates": [],
            "requirements": [],
            "action_items": [],
            "salary_info": None,
            "contact_info": pending.email_from
        }
    
    return note_data
