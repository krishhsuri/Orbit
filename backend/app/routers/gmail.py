from typing import List, Optional
from uuid import UUID
from datetime import datetime

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
    We need to handle the DB session manually since this runs in background.
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
            import asyncio
            
            emails = await asyncio.to_thread(service.fetch_recent_emails, max_results=50)
            
            print(f"[SYNC] Fetched {len(emails)} emails from Gmail")
            
            if not emails:
                print("[SYNC] No emails returned from Gmail API")
                return

            # Print first 3 email subjects for debugging
            for i, email in enumerate(emails[:5]):
                print(f"[SYNC] Email {i+1}: {email.get('subject', 'NO SUBJECT')[:60]}")

            # 2. Process with AI Parser (Async)
            parser = AIParser()
            new_pending_count = 0
            skipped_existing = 0
            filtered_out = 0
            
            for email_data in emails:
                # Check if already processed (by email_id)
                stmt = select(PendingApplication).where(PendingApplication.email_id == email_data['id'])
                existing = await db.execute(stmt)
                if existing.scalar_one_or_none():
                    skipped_existing += 1
                    continue

                parsed = await parser.parse_job_email(email_data)
                
                if parsed:
                    print(f"[SYNC] DETECTED JOB: {email_data.get('subject')[:50]} -> {parsed.get('company')}")
                    # Create PendingApplication
                    pending = PendingApplication(
                        user_id=user.id,
                        email_id=email_data['id'],
                        email_subject=email_data['subject'],
                        email_snippet=email_data['snippet'][:1000] if email_data.get('snippet') else None,
                        email_date=datetime.now(),
                        
                        parsed_company=parsed.get('company'),
                        parsed_role=parsed.get('role'),
                        parsed_status=parsed.get('status'),
                        parsed_job_url=parsed.get('job_url'),
                        confidence_score=parsed.get('confidence', 0.0),
                        status="pending"
                    )
                    db.add(pending)
                    new_pending_count += 1
                else:
                    filtered_out += 1
            
            print(f"[SYNC] Summary: {new_pending_count} new, {skipped_existing} skipped, {filtered_out} filtered out")
            
            if new_pending_count > 0:
                user.gmail_last_sync_at = datetime.now()
                await db.commit()
                print(f"[SYNC] Committed {new_pending_count} new applications")
            else:
                print("[SYNC] No new job applications detected")
                
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
        job_title=pending.parsed_role or "Unknown Role",
        job_url=pending.parsed_job_url,
        status=app_status,
        applied_date=pending.email_date if pending.email_date else datetime.now(),
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
