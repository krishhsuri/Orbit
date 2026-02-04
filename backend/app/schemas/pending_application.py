from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class PendingApplicationBase(BaseModel):
    email_subject: str
    email_snippet: Optional[str] = None
    email_from: Optional[str] = None  # Sender info (name + email)
    email_date: datetime
    
    parsed_company: Optional[str] = None
    parsed_role: Optional[str] = None
    parsed_status: Optional[str] = None
    parsed_job_url: Optional[str] = None
    
    confidence_score: float = 0.0
    status: str = "pending"

class PendingApplicationCreate(PendingApplicationBase):
    email_id: str
    user_id: UUID

class PendingApplicationUpdate(BaseModel):
    status: Optional[str] = None
    parsed_company: Optional[str] = None
    parsed_role: Optional[str] = None
    parsed_status: Optional[str] = None
    parsed_job_url: Optional[str] = None

class PendingApplicationResponse(PendingApplicationBase):
    id: UUID
    email_id: str
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
