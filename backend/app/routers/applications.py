"""
Applications Router
CRUD endpoints for job applications
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Application, Event, Tag, application_tags
from app.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatusUpdate,
    ApplicationResponse,
    ApplicationListItem,
    ApplicationDetail,
    ApplicationFilters,
    EventCreate,
    EventResponse,
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,
    SuccessResponse,
)
from app.middleware.auth import get_current_user_id

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ApplicationListItem])
async def list_applications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Comma-separated statuses"),
    search: Optional[str] = Query(default=None, min_length=1),
    source: Optional[str] = Query(default=None),
    sort: str = Query(default="-applied_date"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """List all applications with filters and pagination"""
    
    # Base query
    query = (
        select(Application)
        .options(selectinload(Application.tags))
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
    )
    
    # Apply filters
    if status:
        status_list = [s.strip() for s in status.split(",")]
        query = query.where(Application.status.in_(status_list))
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Application.company_name.ilike(search_term),
                Application.role_title.ilike(search_term),
            )
        )
    
    if source:
        query = query.where(Application.source == source)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    if sort.startswith("-"):
        sort_column = getattr(Application, sort[1:], Application.applied_date)
        query = query.order_by(sort_column.desc())
    else:
        sort_column = getattr(Application, sort, Application.applied_date)
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    # Execute
    result = await db.execute(query)
    applications = result.scalars().all()
    
    # Build response
    total_pages = (total + limit - 1) // limit
    
    return PaginatedResponse(
        data=[ApplicationListItem.model_validate(app) for app in applications],
        meta=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new application"""
    
    # Create application
    application = Application(
        user_id=user_id,
        company_name=data.company_name,
        role_title=data.role_title,
        applied_date=data.applied_date or datetime.now().date(),
        job_url=data.job_url,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        salary_currency=data.salary_currency,
        location=data.location,
        remote_type=data.remote_type,
        source=data.source,
        referrer_name=data.referrer_name,
        priority=data.priority,
        status="applied",
        status_updated_at=datetime.utcnow(),
    )
    
    db.add(application)
    await db.flush()
    
    # Handle tags
    if data.tags:
        for tag_name in data.tags:
            # Find or create tag
            tag_query = select(Tag).where(
                Tag.user_id == user_id,
                Tag.name == tag_name,
            )
            result = await db.execute(tag_query)
            tag = result.scalar_one_or_none()
            
            if not tag:
                tag = Tag(user_id=user_id, name=tag_name)
                db.add(tag)
                await db.flush()
            
            application.tags.append(tag)
    
    # Create initial event
    event = Event(
        application_id=application.id,
        event_type="created",
        title="Application created",
        data={"status": "applied"},
    )
    db.add(event)
    
    await db.commit()
    await db.refresh(application)
    
    return ApplicationResponse.model_validate(application)


@router.get("/{application_id}", response_model=ApplicationDetail)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get a single application by ID"""
    
    query = (
        select(Application)
        .options(
            selectinload(Application.tags),
            selectinload(Application.events),
        )
        .where(Application.id == application_id)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
    )
    
    result = await db.execute(query)
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    return ApplicationDetail.model_validate(application)


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: UUID,
    data: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update an application"""
    
    query = (
        select(Application)
        .options(selectinload(Application.tags))
        .where(Application.id == application_id)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
    )
    
    result = await db.execute(query)
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    
    # Handle status change
    old_status = application.status
    
    for field, value in update_data.items():
        setattr(application, field, value)
    
    application.updated_at = datetime.utcnow()
    
    # If status changed, update status_updated_at and create event
    if data.status and data.status != old_status:
        application.status_updated_at = datetime.utcnow()
        
        event = Event(
            application_id=application.id,
            event_type="status_change",
            title=f"Status changed to {data.status}",
            data={"from": old_status, "to": data.status},
        )
        db.add(event)
    
    await db.commit()
    await db.refresh(application)
    
    return ApplicationResponse.model_validate(application)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: UUID,
    data: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Quick status update endpoint"""
    
    query = (
        select(Application)
        .options(selectinload(Application.tags))
        .where(Application.id == application_id)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
    )
    
    result = await db.execute(query)
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    old_status = application.status
    application.status = data.status
    application.status_updated_at = datetime.utcnow()
    application.updated_at = datetime.utcnow()
    
    # Create status change event
    event = Event(
        application_id=application.id,
        event_type="status_change",
        title=f"Status changed to {data.status}",
        data={"from": old_status, "to": data.status},
    )
    db.add(event)
    
    await db.commit()
    await db.refresh(application)
    
    return ApplicationResponse.model_validate(application)


@router.delete("/{application_id}", response_model=SuccessResponse)
async def delete_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Soft delete an application"""
    
    query = (
        select(Application)
        .where(Application.id == application_id)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
    )
    
    result = await db.execute(query)
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    application.deleted_at = datetime.utcnow()
    await db.commit()
    
    return SuccessResponse(message="Application deleted")


@router.get("/{application_id}/events", response_model=List[EventResponse])
async def get_application_events(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get timeline events for an application"""
    
    # Verify ownership
    app_query = (
        select(Application.id)
        .where(Application.id == application_id)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
    )
    
    result = await db.execute(app_query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    # Get events
    events_query = (
        select(Event)
        .where(Event.application_id == application_id)
        .order_by(Event.created_at.desc())
    )
    
    result = await db.execute(events_query)
    events = result.scalars().all()
    
    return [EventResponse.model_validate(e) for e in events]


@router.post("/{application_id}/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_application_event(
    application_id: UUID,
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Add a new event to an application timeline"""
    
    # Verify ownership
    app_query = (
        select(Application.id)
        .where(Application.id == application_id)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
    )
    
    result = await db.execute(app_query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    # Create event
    event = Event(
        application_id=application_id,
        event_type=data.event_type,
        title=data.title,
        description=data.description,
        data=data.data,
        scheduled_at=data.scheduled_at,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return EventResponse.model_validate(event)
