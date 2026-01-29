"""
Analytics Schemas
Pydantic schemas for analytics endpoints
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class QuickStats(BaseModel):
    """Dashboard quick statistics"""
    
    total: int
    active: int
    interviews: int
    offers: int
    this_week: int


class FunnelStage(BaseModel):
    """Single stage in conversion funnel"""
    
    status: str
    count: int
    percentage: float


class ConversionFunnel(BaseModel):
    """Complete conversion funnel"""
    
    stages: List[FunnelStage]
    total: int


class SourceStats(BaseModel):
    """Response rate by application source"""
    
    source: str
    total: int
    responded: int
    response_rate: float


class SourceAnalytics(BaseModel):
    """Source analytics response"""
    
    sources: List[SourceStats]


class TrendDataPoint(BaseModel):
    """Single data point in time series"""
    
    date: date
    count: int
    cumulative: Optional[int] = None


class TrendsResponse(BaseModel):
    """Time series trends response"""
    
    period: str  # "week", "month", "year"
    data_points: List[TrendDataPoint]
    total: int
    average_per_day: float


class AIInsight(BaseModel):
    """AI-generated insight"""
    
    type: str  # "success", "tip", "warning"
    title: str
    description: str
    confidence: Optional[float] = None


class InsightsResponse(BaseModel):
    """AI insights response"""
    
    insights: List[AIInsight]
    generated_at: str


class AnalyticsFilters(BaseModel):
    """Common filters for analytics queries"""
    
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[List[str]] = None
