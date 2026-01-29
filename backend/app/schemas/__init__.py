"""
Schemas Package
Export all Pydantic schemas
"""

from app.schemas.common import (
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,
    ErrorDetail,
    ErrorResponse,
    SuccessResponse,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserPreferences,
    UserResponse,
    UserPublic,
)
from app.schemas.application import (
    ApplicationBase,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatusUpdate,
    ApplicationResponse,
    ApplicationListItem,
    ApplicationDetail,
    ApplicationFilters,
    ApplicationStatus,
    TagResponse,
    EventResponse,
    EventCreate,
)
from app.schemas.analytics import (
    QuickStats,
    FunnelStage,
    ConversionFunnel,
    SourceStats,
    SourceAnalytics,
    TrendDataPoint,
    TrendsResponse,
    AIInsight,
    InsightsResponse,
    AnalyticsFilters,
)

__all__ = [
    # Common
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "SuccessResponse",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserPreferences",
    "UserResponse",
    "UserPublic",
    # Application
    "ApplicationBase",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationStatusUpdate",
    "ApplicationResponse",
    "ApplicationListItem",
    "ApplicationDetail",
    "ApplicationFilters",
    "ApplicationStatus",
    "TagResponse",
    "EventResponse",
    "EventCreate",
    # Analytics
    "QuickStats",
    "FunnelStage",
    "ConversionFunnel",
    "SourceStats",
    "SourceAnalytics",
    "TrendDataPoint",
    "TrendsResponse",
    "AIInsight",
    "InsightsResponse",
    "AnalyticsFilters",
]
