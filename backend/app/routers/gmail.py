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
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

async def sync_emails_task(user_id: UUID, db_session_maker):
    """
    Background task to sync emails.
    Fetches emails, auto-filters non-job emails, only stores job-related ones.
    """
    from app.database import async_session_maker
    
    print(f"[SYNC] Starting sync for user {user_id}")
    
    async with async_session_maker() as db:
        try:
            # 1. Fetch User
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                print(f"[SYNC] ERROR: User {user_id} not found")
                return
            if not user.gmail_sync_enabled:
                print(f"[SYNC] ERROR: Gmail sync not enabled for user {user.email}")
                return

            print(f"[SYNC] Gmail sync enabled for user {user.email}")
            
            service = GmailService(user, db=None) 
            
            # Run in threadpool (fetch_recent_emails is blocking I/O)
            # Fetch more emails (100) to find at least 10 job-related ones
            import asyncio
            
            emails = await asyncio.to_thread(service.fetch_recent_emails, max_results=100)
            
            print(f"[SYNC] Fetched {len(emails)} emails from Gmail")
            
            if not emails:
                print("[SYNC] No emails returned from Gmail API")
                return

            # Print first 5 email subjects for debugging
            for i, email in enumerate(emails[:5]):
                print(f"[SYNC] Email {i+1}: {email.get('subject', 'NO SUBJECT')[:60]}")

            # 2. Process with AI Parser (Quick local ML, no LLM)
            parser = AIParser()
            job_related_count = 0
            skipped_existing = 0
            filtered_out = 0
            
            # Non-job statuses to auto-filter (don't store these at all)
            NON_JOB_STATUSES = {'not_job_related', 'general_hr', 'unknown'}
            
            for email_data in emails:
                # Check if already processed (by email_id)
                stmt = select(PendingApplication).where(PendingApplication.email_id == email_data['id'])
                existing = await db.execute(stmt)
                if existing.scalar_one_or_none():
                    skipped_existing += 1
                    continue

                # Quick parse - local ML only, no LLM (fast)
                parsed = await parser.quick_parse(email_data)
                
                # Auto-filter: Skip if not parsed or not job-related
                if not parsed:
                    filtered_out += 1
                    continue
                    
                # Auto-cleanup: Skip non-job-related emails entirely
                status = parsed.get('status', 'unknown')
                if status in NON_JOB_STATUSES:
                    print(f"[SYNC] FILTERED: {email_data.get('subject', '')[:40]} (status: {status})")
                    filtered_out += 1
                    continue
                
                # This is a job-related email - add to pending queue
                print(f"[SYNC] JOB FOUND: {parsed.get('company')} - {status}")
                pending = PendingApplication(
                    user_id=user.id,
                    email_id=email_data['id'],
                    email_subject=email_data['subject'],
                    email_snippet=email_data['snippet'][:1000] if email_data.get('snippet') else None,
                    email_date=datetime.now(),
                    parsed_company=parsed.get('company'),
                    parsed_role=parsed.get('role'),
                    parsed_status=status,
                    parsed_job_url=parsed.get('job_url'),
                    confidence_score=parsed.get('confidence', 0.0),
                    status="pending"
                )
                db.add(pending)
                job_related_count += 1
            
            print(f"[SYNC] Summary: {job_related_count} job-related, {skipped_existing} skipped, {filtered_out} filtered out")
            
            if job_related_count > 0:
                user.gmail_last_sync_at = datetime.now()
                await db.commit()
                print(f"[SYNC] Committed: {job_related_count} job-related emails")
            else:
                print("[SYNC] No job-related emails found")
                
        except Exception as e:
            print(f"[SYNC] ERROR: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()

@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger manual email sync"""
    if not user.gmail_sync_enabled:
        raise HTTPException(status_code=400, detail="Gmail sync is not enabled")
        
    # Add background task
    # We pass user.id and rely on the task to instantiate its own session
    background_tasks.add_task(sync_emails_task, user.id, None)
    
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
    # Delete entries with not_job_related or general_hr status
    stmt = delete(PendingApplication).where(
        PendingApplication.user_id == user.id,
        PendingApplication.parsed_status.in_(('not_job_related', 'general_hr'))
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
    Process all pending emails with Groq LLM.
    LLM decides whether to add to applications or discard.
    """
    # Get all pending applications
    query = select(PendingApplication).where(
        PendingApplication.user_id == user.id,
        PendingApplication.status == "pending"
    )
    result = await db.execute(query)
    pending_apps = result.scalars().all()
    
    if not pending_apps:
        return {"message": "No pending applications to process", "added": 0, "discarded": 0}
    
    parser = AIParser()
    added_count = 0
    discarded_count = 0
    processed_ids = []
    
    for pending in pending_apps:
        try:
            # Prepare email data for LLM
            email_data = {
                'subject': pending.email_subject,
                'snippet': pending.email_snippet or '',
                'body_preview': pending.email_snippet or ''
            }
            
            # Send to Groq for analysis
            llm_result = await parser.process_with_llm(email_data)
            
            if llm_result and llm_result.get('action') == 'add_to_tracker':
                # Create Application
                new_app = Application(
                    user_id=user.id,
                    company_name=llm_result.get('company') or pending.parsed_company or "Unknown Company",
                    role_title=llm_result.get('role') or pending.parsed_role or "Unknown Role",
                    job_url=pending.parsed_job_url,
                    status=llm_result.get('status', 'applied'),
                    applied_date=pending.email_date.date() if pending.email_date else date.today(),
                    source="gmail_ai"
                )
                db.add(new_app)
                
                # Mark as confirmed
                pending.status = "confirmed"
                added_count += 1
                processed_ids.append(str(pending.id))
                print(f"[AI] Added: {new_app.company_name} - {new_app.status}")
                
            elif llm_result and llm_result.get('action') == 'discard':
                # Mark as rejected (discarded by AI)
                pending.status = "rejected"
                discarded_count += 1
                processed_ids.append(str(pending.id))
                print(f"[AI] Discarded: {pending.email_subject[:40]} - {llm_result.get('reason')}")
                
        except Exception as e:
            print(f"[AI] Error processing {pending.id}: {e}")
            continue
    
    await db.commit()
    
    return {
        "message": f"Processed {len(processed_ids)} emails with AI",
        "added": added_count,
        "discarded": discarded_count,
        "processed_ids": processed_ids
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
        source="gmail_auto"
    )
    
    db.add(new_app)
    
    # Update pending status
    pending.status = "confirmed"
    
    await db.commit()
    await db.refresh(pending)
    
    return {"message": "Application confirmed and created", "application_id": new_app.id}

@router.delete("/pending/{id}")
async def reject_application(
    id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject/Dismiss a pending application"""
    query = select(PendingApplication).where(
        PendingApplication.id == id,
        PendingApplication.user_id == user.id
    )
    result = await db.execute(query)
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Pending application not found")
        
    pending.status = "rejected"
    await db.commit()
    
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

