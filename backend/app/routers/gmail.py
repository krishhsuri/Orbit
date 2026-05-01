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
from app.ml.matching.email_matcher import EmailMatcher
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
            
            # Fix #5: Pass db session so refreshed OAuth tokens are persisted
            service = GmailService(user, db=db)
            
            # Fetch more emails (500) for bulk load
            import asyncio
            
            last_synced_id = user.gmail_last_synced_email_id
            emails = await asyncio.to_thread(
                service.fetch_recent_emails, 
                max_results=500,
                after_message_id=last_synced_id
            )
            
            logger.info(f"[SYNC] Fetched {len(emails)} emails from Gmail")
            
            if not emails:
                logger.warning("[SYNC] No inbox emails returned from Gmail API, proceeding to sent emails...")

            # Print first 5 email subjects for debugging
            for i, email in enumerate(emails[:5]):
                logger.debug(f"[SYNC] Email {i+1}: {email.get('subject', 'NO SUBJECT')[:60]}")

            # 2. Process with AI Parser (Quick local ML, no LLM)
            parser = AIParser()
            matcher = EmailMatcher()  # Fix #11: wire up matcher
            
            from app.ml.parsers.digest_parser import DigestParser
            digest_parser = DigestParser()
            
            # Load user's existing applications for matching
            apps_result = await db.execute(
                select(Application.id, Application.company_name).where(
                    Application.user_id == user_id,
                    Application.deleted_at.is_(None)
                )
            )
            existing_apps = [
                {'id': str(row.id), 'company_name': row.company_name}
                for row in apps_result.fetchall()
            ]
            
            job_related_count = 0
            skipped_existing = 0
            filtered_out = 0
            matched_as_update = 0
            digest_leads_count = 0
            parsed_email_date = None  # Will be set per-email in the loop
            
            # Non-job statuses to auto-filter (ONLY truly non-job emails)
            # Keep general_hr and unknown - better to show uncertain emails than miss them
            # Also filter 'not_for_user' - emails where user wasn't in the candidate list
            NON_JOB_STATUSES = {'not_job_related', 'not_for_user'}
            
            seen_batch_ids = set()
            
            for email_data in emails:
                if email_data['id'] in seen_batch_ids:
                    continue
                seen_batch_ids.add(email_data['id'])
                
                # Check if already processed (by email_id)
                stmt = select(PendingApplication).where(PendingApplication.email_id == email_data['id'])
                existing = await db.execute(stmt)
                if existing.scalar_one_or_none():
                    skipped_existing += 1
                    continue

                # --- DIGEST BRANCH ---
                # Check if this is a job digest email (Unstop, Hirist, etc.)
                # Parse date first so it's available for digest lead creation
                email_date_str = email_data.get('date', '')
                try:
                    parsed_email_date = parsedate_to_datetime(email_date_str)
                except Exception:
                    parsed_email_date = datetime.now()

                if digest_parser.is_digest_email(
                    email_data.get('from_address', ''),
                    email_data.get('subject', ''),
                    email_data.get('body_preview', '')
                ):
                    logger.info(f"[SYNC] DIGEST detected: {email_data.get('subject', '')[:50]}")
                    listings = await digest_parser.extract_leads(
                        email_id=email_data['id'],
                        sender=email_data.get('from_address', ''),
                        body=email_data.get('body_preview', ''),
                        email_date=parsed_email_date,
                    )
                    for listing in listings:
                        # on_conflict_do_nothing for composite unique (source_email_id, company, role)
                        from sqlalchemy.dialects.postgresql import insert as pg_insert
                        stmt_lead = pg_insert(Lead).values(
                            company=listing['company'],
                            role=listing['role'],
                            stipend=listing.get('stipend'),
                            location=listing.get('location'),
                            job_url=listing.get('job_url'),
                            job_site=listing.get('job_site'),
                            recruiter_email=listing.get('recruiter_email'),
                            source_email_id=listing['source_email_id'],
                            date=listing['date'],
                            is_from_digest=True,
                        ).on_conflict_do_nothing(constraint='uq_lead_email_company_role')
                        result_lead = await db.execute(stmt_lead)
                        if result_lead.rowcount:
                            digest_leads_count += 1
                    filtered_out += 1  # Don't create PendingApplication for digest emails
                    continue  # Skip the normal ML pipeline

                # Quick parse - local ML only, no LLM (fast)
                # Pass user email to detect multi-candidate emails where user isn't listed
                parsed = await parser.quick_parse(email_data, user_email=user.email)
                
                # Auto-filter: Skip if not parsed or not job-related
                if not parsed:
                    filtered_out += 1
                    continue
                    
                # Auto-cleanup: Skip non-job-related emails entirely
                parsed_status = parsed.get('status', 'unknown')
                if parsed_status in NON_JOB_STATUSES:
                    logger.debug(f"[SYNC] FILTERED: {email_data.get('subject', '')[:40]} (status: {parsed_status})")
                    filtered_out += 1
                    continue

                # Fix #11: Try to match this email to an existing application
                # If matched, update that app's status instead of creating a new pending entry
                nlp_result = {'entities': {'organizations': []}, 'company': parsed.get('company')}
                matched_app_id, match_confidence = matcher.match(email_data, existing_apps, nlp_result)
                
                if matched_app_id and match_confidence >= 0.80:
                    # Map the local ML status to an Application status
                    from app.services.ai_parser import STATUS_MAPPING
                    new_status = STATUS_MAPPING.get(parsed_status, None)
                    if new_status and new_status in APPLICATION_STATUSES:
                        await db.execute(
                            update(Application)
                            .where(Application.id == UUID(matched_app_id))
                            .values(status=new_status, status_updated_at=datetime.utcnow())
                        )
                        matched_as_update += 1
                        logger.info(f"[SYNC] MATCHED+UPDATED app {matched_app_id} status → {new_status}")
                    continue  # Don't create a duplicate pending entry
                
                # Parse actual email date from Date header (if not already done in digest branch)
                if parsed_email_date is None:
                    email_date_str = email_data.get('date', '')
                    try:
                        parsed_email_date = parsedate_to_datetime(email_date_str)
                    except Exception:
                        parsed_email_date = datetime.now()
                
                # This is a job-related email - add to pending queue
                logger.info(f"[SYNC] JOB FOUND: {parsed.get('company')} - {parsed_status}")
                pending = PendingApplication(
                    user_id=user.id,
                    email_id=email_data['id'],
                    email_subject=email_data['subject'],
                    email_snippet=email_data.get('body_preview', ''),
                    email_from=email_data.get('from_address'),
                    email_date=parsed_email_date,
                    parsed_company=parsed.get('company'),
                    parsed_role=parsed.get('role'),
                    parsed_status=parsed_status,
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
                        
                        # Extract recruiter info from raw from_address (includes display name)
                        from_addr_raw = email_data.get('from_address_raw', email_data.get('from_address', ''))
                        import re as _re
                        name_match = _re.match(r'^([^<]+)\s*<', from_addr_raw)
                        email_match = _re.search(r'<([^>]+)>', from_addr_raw) or _re.search(r'([^\s]+@[^\s]+)', from_addr_raw)
                        
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
            
            logger.info(f"[SYNC] Summary: {job_related_count} job-related, {digest_leads_count} digest leads, {matched_as_update} status-updates, {skipped_existing} skipped, {filtered_out} filtered out")
            
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

            # --- SENT EMAILS BRANCH (Cold Application Tracking) ---
            try:
                logger.info(f"[SYNC] Fetching sent emails for cold application detection")
                last_synced_sent_id = user.gmail_last_synced_sent_id
                sent_emails = await asyncio.to_thread(
                    service.fetch_sent_emails,
                    max_results=500,
                    after_message_id=last_synced_sent_id
                )
                
                logger.info(f"[SYNC] Fetched {len(sent_emails)} sent emails from Gmail")
                
                if sent_emails:
                    from app.ml.classifiers.cold_email_detector import ColdEmailDetector
                    cold_detector = ColdEmailDetector()
                    
                    cold_app_count = 0
                    skipped_sent = 0
                    seen_sent_ids = set()
                    
                    for sent_email in sent_emails:
                        if sent_email['id'] in seen_batch_ids or sent_email['id'] in seen_sent_ids:
                            continue
                        seen_sent_ids.add(sent_email['id'])
                        
                        # Check if already processed
                        stmt = select(PendingApplication).where(PendingApplication.email_id == sent_email['id'])
                        existing = await db.execute(stmt)
                        if existing.scalar_one_or_none():
                            skipped_sent += 1
                            continue
                            
                        # Detect cold application
                        detection = cold_detector.detect(sent_email)
                        
                        if detection['is_cold_email']:
                            logger.info(f"[SYNC] COLD EMAIL DETECTED: {sent_email.get('subject')[:50]} (conf: {detection['confidence']:.2f})")
                            
                            # Parse date
                            email_date_str = sent_email.get('date', '')
                            try:
                                parsed_sent_date = parsedate_to_datetime(email_date_str)
                            except Exception:
                                parsed_sent_date = datetime.now()
                                
                            # Create PendingApplication
                            pending = PendingApplication(
                                user_id=user.id,
                                email_id=sent_email['id'],
                                email_subject=sent_email['subject'],
                                email_snippet=sent_email.get('body_preview', ''),
                                email_from=sent_email.get('to_address'),  # We use 'to' for the company contact in sent emails
                                email_date=parsed_sent_date,
                                parsed_company=detection['company'],
                                parsed_role=detection['role'],
                                parsed_status='applied',  # Sent cold emails always map to applied
                                parsed_job_url=None,
                                confidence_score=detection['confidence'],
                                source='cold_email',
                                status="pending"
                            )
                            db.add(pending)
                            cold_app_count += 1
                            
                            # Also add global Lead if company extracted
                            if detection['company']:
                                from app.models import Lead
                                lead_exists = await db.execute(
                                    select(Lead).where(Lead.source_email_id == sent_email['id'])
                                )
                                if not lead_exists.scalar_one_or_none():
                                    raw_to = sent_email.get('to_address_raw', sent_email.get('to_address', ''))
                                    import re as _re
                                    name_match = _re.match(r'^([^<]+)\s*<', raw_to)
                                    email_match = _re.search(r'<([^>]+)>', raw_to) or _re.search(r'([^\s]+@[^\s]+)', raw_to)
                                    
                                    lead = Lead(
                                        company=detection['company'],
                                        role=detection['role'] or "Unknown Role",
                                        job_site="Cold Email",
                                        job_url=None,
                                        recruiter_name=name_match.group(1).strip() if name_match else None,
                                        recruiter_email=email_match.group(1) if email_match else None,
                                        source_email_id=sent_email['id'],
                                        date=parsed_sent_date,
                                    )
                                    db.add(lead)
                    
                    # Update sync tracking for sent emails
                    user.gmail_last_synced_sent_id = sent_emails[0]['id']
                    if cold_app_count > 0:
                        await db.commit()
                        logger.info(f"[SYNC] Committed {cold_app_count} cold application emails")
                    else:
                        await db.commit()
                        logger.info(f"[SYNC] Processed sent emails, skipped {skipped_sent}")

            except Exception as e:
                logger.error(f"[SYNC] Error processing sent emails: {e}")
                # We don't rollback the entire transaction here, 
                # we just skip the sent email portion if it fails

            
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

SYNC_LOCKS = set()

@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger manual email sync in the background (non-blocking)"""
    if not user.gmail_sync_enabled:
        raise HTTPException(status_code=400, detail="Gmail sync is not enabled")
        
    user_key = str(user.id)
    if user_key in SYNC_LOCKS:
        return {"status": "request_ignored", "message": "Sync is already in progress"}
        
    SYNC_LOCKS.add(user_key)
        
    from app.tasks.email_sync import _async_email_sync
    
    async def _safe_sync():
        try:
            await _async_email_sync(user.id)
        finally:
            SYNC_LOCKS.discard(user_key)
            
    background_tasks.add_task(_safe_sync)
    
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
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process all pending emails with Groq LLM in the background.
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
    
    # Queue AI processing in the background (non-blocking)
    from app.tasks.email_sync import _async_process_ai
    background_tasks.add_task(_async_process_ai, user.id)
    
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

    # Map parsed status to Application status
    app_status = "applied"  # Default
    if pending.parsed_status:
        from app.services.ai_parser import STATUS_MAPPING
        mapped = STATUS_MAPPING.get(pending.parsed_status.lower(), pending.parsed_status)
        if mapped in APPLICATION_STATUSES:
            app_status = mapped

    # Fix #12: Deduplicate — check if an application already exists for this company
    existing_app_stmt = select(Application).where(
        Application.user_id == user.id,
        Application.company_name.ilike(pending.parsed_company or ""),
        Application.deleted_at.is_(None)
    )
    existing_app_result = await db.execute(existing_app_stmt)
    existing_app = existing_app_result.scalar_one_or_none()
    
    if existing_app:
        # Update existing application's status instead of creating duplicate
        if app_status != 'applied':  # Only upgrade status, don't downgrade
            existing_app.status = app_status
            existing_app.status_updated_at = datetime.utcnow()
        pending.status = "confirmed"
        await db.commit()
        
        # Save positive training example
        from app.models.training_example import TrainingExample
        training = TrainingExample(
            email_subject=pending.email_subject,
            email_snippet=pending.email_snippet,
            email_from=pending.email_from or "",
            label="positive",
            user_id=user.id,
        )
        db.add(training)
        await db.commit()
        
        from app.ml.classifiers.learned_filter import refresh_learned_model
        await refresh_learned_model()
        
        return {"message": "Existing application updated", "application_id": existing_app.id}
    
    # No existing app — create a new one
    new_app = Application(
        user_id=user.id,
        company_name=pending.parsed_company or "Unknown Company",
        role_title=pending.parsed_role or "Unknown Role",
        job_url=pending.parsed_job_url,
        status=app_status,
        applied_date=pending.email_date.date() if pending.email_date else date.today(),
        source=pending.source or "gmail_auto",
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


@router.post("/pending/{id}/undo-reject")
async def undo_reject_application(
    id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Undo a pending application rejection.
    - Reverts status back to 'pending'
    - Deletes the negative TrainingExample that was created (un-poisons the model)
    - Retrains the learned filter
    """
    query = select(PendingApplication).where(
        PendingApplication.id == id,
        PendingApplication.user_id == user.id
    )
    result = await db.execute(query)
    pending = result.scalar_one_or_none()

    if not pending:
        raise HTTPException(status_code=404, detail="Pending application not found")

    if pending.status != "rejected":
        raise HTTPException(status_code=400, detail="Application is not rejected, cannot undo")

    # Revert status
    pending.status = "pending"

    # Delete the most recent negative TrainingExample for this email (un-poison)
    from app.models.training_example import TrainingExample
    from sqlalchemy import desc
    neg_example = await db.execute(
        select(TrainingExample)
        .where(
            TrainingExample.user_id == user.id,
            TrainingExample.label == "negative",
            TrainingExample.email_subject == pending.email_subject,
        )
        .order_by(desc(TrainingExample.created_at))
        .limit(1)
    )
    neg_row = neg_example.scalar_one_or_none()
    if neg_row:
        await db.delete(neg_row)

    await db.commit()

    # Retrain to remove the deleted negative example from model
    from app.ml.classifiers.learned_filter import refresh_learned_model
    await refresh_learned_model()

    return {"message": "Rejection undone successfully", "id": str(id)}


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
