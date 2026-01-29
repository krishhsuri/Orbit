"""
User Schemas
Pydantic schemas for user-related requests and responses
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user fields"""
    
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user"""
    
    google_id: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[dict] = None


class UserPreferences(BaseModel):
    """User preferences schema"""
    
    weekly_goal: int = Field(default=10, ge=1, le=50)
    email_reminders: bool = True
    weekly_summary: bool = True
    ghost_detection: bool = True
    default_view: str = Field(default="list", pattern="^(list|kanban)$")


class UserResponse(UserBase):
    """User response schema"""
    
    id: UUID
    preferences: dict = {}
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    """Public user info (for other users to see)"""
    
    id: UUID
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True
