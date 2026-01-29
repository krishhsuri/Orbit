"""
Common Schemas
Shared Pydantic schemas for pagination, errors, and responses
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field


# Generic type for paginated responses
T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for pagination"""
    
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginationMeta(BaseModel):
    """Pagination metadata in response"""
    
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    
    data: List[T]
    meta: PaginationMeta


class ErrorDetail(BaseModel):
    """Error detail structure"""
    
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    
    error: ErrorDetail


class SuccessResponse(BaseModel):
    """Simple success response"""
    
    success: bool = True
    message: Optional[str] = None


# Common field types
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields in responses"""
    
    created_at: datetime
    updated_at: datetime


class UUIDMixin(BaseModel):
    """Mixin for UUID field in responses"""
    
    id: UUID
