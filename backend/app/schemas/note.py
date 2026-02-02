"""
Note Schemas
Pydantic models for Note CRUD operations
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Base note schema"""
    content: str = Field(..., min_length=1, max_length=10000)


class NoteCreate(NoteBase):
    """Schema for creating a note"""
    pass


class NoteUpdate(BaseModel):
    """Schema for updating a note"""
    content: Optional[str] = Field(None, min_length=1, max_length=10000)


class NoteResponse(NoteBase):
    """Schema for note response"""
    id: UUID
    application_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
