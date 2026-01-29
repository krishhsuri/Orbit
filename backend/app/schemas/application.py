"""
Application Schemas
Pydantic schemas for application-related requests and responses
"""

from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.application import APPLICATION_STATUSES


# Type alias for status
ApplicationStatus = Literal[
    "applied", "screening", "oa", "interview", 
    "offer", "accepted", "rejected", "withdrawn", "ghosted"
]

RemoteType = Literal["remote", "hybrid", "onsite"]


class ApplicationBase(BaseModel):
    """Base application fields"""
    
    company_name: str = Field(..., min_length=1, max_length=255)
    role_title: str = Field(..., min_length=1, max_length=255)
    applied_date: Optional[date] = None
    job_url: Optional[str] = Field(None, max_length=2000)
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: str = Field(default="USD", max_length=3)
    location: Optional[str] = Field(None, max_length=255)
    remote_type: Optional[RemoteType] = None
    source: Optional[str] = Field(None, max_length=50)
    referrer_name: Optional[str] = Field(None, max_length=255)
    priority: int = Field(default=5, ge=1, le=10)
    
    @field_validator("salary_max")
    @classmethod
    def salary_max_must_be_greater(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None and info.data.get("salary_min") is not None:
            if v < info.data["salary_min"]:
                raise ValueError("salary_max must be >= salary_min")
        return v


class ApplicationCreate(ApplicationBase):
    """Schema for creating an application"""
    
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    """Schema for updating an application"""
    
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role_title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[ApplicationStatus] = None
    applied_date: Optional[date] = None
    job_url: Optional[str] = Field(None, max_length=2000)
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=3)
    location: Optional[str] = Field(None, max_length=255)
    remote_type: Optional[RemoteType] = None
    source: Optional[str] = Field(None, max_length=50)
    referrer_name: Optional[str] = Field(None, max_length=255)
    priority: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    """Schema for updating just the status"""
    
    status: ApplicationStatus


class TagResponse(BaseModel):
    """Tag in response"""
    
    id: UUID
    name: str
    color: str
    
    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    """Event in response"""
    
    id: UUID
    event_type: str
    title: Optional[str]
    description: Optional[str]
    data: dict
    scheduled_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ApplicationResponse(ApplicationBase):
    """Full application response"""
    
    id: UUID
    user_id: UUID
    status: ApplicationStatus
    extra_data: dict = {}
    created_at: datetime
    updated_at: datetime
    status_updated_at: datetime
    
    # Related data
    tags: List[TagResponse] = []
    
    class Config:
        from_attributes = True


class ApplicationListItem(BaseModel):
    """Simplified application for list views"""
    
    id: UUID
    company_name: str
    role_title: str
    status: ApplicationStatus
    applied_date: date
    priority: int
    source: Optional[str]
    tags: List[TagResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ApplicationDetail(ApplicationResponse):
    """Detailed application response with events and notes"""
    
    events: List[EventResponse] = []
    
    class Config:
        from_attributes = True


class ApplicationFilters(BaseModel):
    """Query filters for applications list"""
    
    status: Optional[List[ApplicationStatus]] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = Field(None, min_length=1)
    source: Optional[str] = None
    priority_min: Optional[int] = Field(None, ge=1, le=10)
    priority_max: Optional[int] = Field(None, ge=1, le=10)
    applied_after: Optional[date] = None
    applied_before: Optional[date] = None
    sort: str = Field(default="-applied_date")  # - prefix for descending


class EventCreate(BaseModel):
    """Schema for creating an event"""
    
    event_type: str = Field(..., max_length=50)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    data: dict = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None
