"""Lead schemas for API validation."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class LeadBase(BaseModel):
    company: str
    role: Optional[str] = None
    job_site: Optional[str] = None
    job_url: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    date: Optional[datetime] = None
    status: str = "active"


class LeadCreate(LeadBase):
    """For manually creating a lead."""
    pass


class LeadResponse(LeadBase):
    id: UUID
    source_email_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
