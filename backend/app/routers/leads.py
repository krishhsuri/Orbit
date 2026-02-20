"""
Leads router — global shared job board.
All leads are visible to all authenticated users.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Lead, User
from app.schemas.lead import LeadResponse, LeadCreate
from app.middleware.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    role: Optional[str] = Query(None, description="Filter by role (partial match)"),
    company: Optional[str] = Query(None, description="Filter by company (partial match)"),
    search: Optional[str] = Query(None, description="Search across company and role"),
    status: str = Query("active", description="Filter by status (active/archived)"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all leads globally with optional filters."""
    query = select(Lead).where(Lead.status == status)

    if role:
        query = query.where(Lead.role.ilike(f"%{role}%"))
    if company:
        query = query.where(Lead.company.ilike(f"%{company}%"))
    if search:
        query = query.where(
            Lead.company.ilike(f"%{search}%") | Lead.role.ilike(f"%{search}%")
        )

    query = query.order_by(Lead.date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/count")
async def lead_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get total lead count."""
    count = (await db.execute(
        select(func.count()).select_from(Lead).where(Lead.status == "active")
    )).scalar() or 0
    return {"count": count}


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single lead by ID."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/", response_model=LeadResponse, status_code=201)
async def create_lead(
    data: LeadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually create a lead."""
    lead = Lead(
        company=data.company,
        role=data.role,
        job_site=data.job_site,
        job_url=data.job_url,
        recruiter_name=data.recruiter_name,
        recruiter_email=data.recruiter_email,
        date=data.date,
        status=data.status,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive a lead (soft delete)."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = "archived"
    await db.commit()
    return {"message": "Lead archived"}
