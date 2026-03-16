from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Application
from app.schemas import (
    QuickStats,
    FunnelStage,
    ConversionFunnel,
    SourceStats,
    SourceAnalytics,
    TrendDataPoint,
    TrendsResponse,
    AIInsight,
    InsightsResponse,
)
from app.middleware.auth import get_current_user_id

router = APIRouter()


@router.get("/summary", response_model=QuickStats)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get quick stats for dashboard"""
    
    week_ago = date.today() - timedelta(days=7)
    
    query = select(
        func.count().label("total"),
        func.count().filter(
            Application.status.in_(["applied", "screening", "oa", "interview"])
        ).label("active"),
        func.count().filter(
            Application.status == "interview"
        ).label("interviews"),
        func.count().filter(
            Application.status.in_(["offer", "accepted"])
        ).label("offers"),
        func.count().filter(
            Application.applied_date >= week_ago
        ).label("this_week"),
    ).where(
        Application.user_id == user_id,
        Application.deleted_at.is_(None),
    )
    
    result = await db.execute(query)
    row = result.one()
    
    return QuickStats(
        total=row.total or 0,
        active=row.active or 0,
        interviews=row.interviews or 0,
        offers=row.offers or 0,
        this_week=row.this_week or 0,
    )


@router.get("/funnel", response_model=ConversionFunnel)
async def get_funnel(
    start_date: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get conversion funnel data"""
    
    query = select(
        Application.status,
        func.count().label("count"),
    ).where(
        Application.user_id == user_id,
        Application.deleted_at.is_(None),
    )
    
    if start_date:
        query = query.where(Application.applied_date >= start_date)
    
    query = query.group_by(Application.status)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to dict
    status_counts = {row.status: row.count for row in rows}
    total = sum(status_counts.values())
    
    # Define funnel order
    funnel_order = [
        "applied", "screening", "oa", "interview", "offer", "accepted"
    ]
    
    stages = []
    for status in funnel_order:
        count = status_counts.get(status, 0)
        percentage = (count / total * 100) if total > 0 else 0
        stages.append(FunnelStage(
            status=status,
            count=count,
            percentage=round(percentage, 1),
        ))
    
    return ConversionFunnel(stages=stages, total=total)


@router.get("/sources", response_model=SourceAnalytics)
async def get_source_analytics(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get response rate by application source"""
    
    query = select(
        Application.source,
        func.count().label("total"),
        func.count().filter(
            Application.status.not_in(["applied", "ghosted"])
        ).label("responded"),
    ).where(
        Application.user_id == user_id,
        Application.deleted_at.is_(None),
        Application.source.isnot(None),
    ).group_by(
        Application.source
    ).order_by(
        func.count().desc()
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    sources = []
    for row in rows:
        response_rate = (row.responded / row.total * 100) if row.total > 0 else 0
        sources.append(SourceStats(
            source=row.source,
            total=row.total,
            responded=row.responded,
            response_rate=round(response_rate, 1),
        ))
    
    return SourceAnalytics(sources=sources)


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    period: str = Query(default="month", pattern="^(week|month|year)$"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get application trends over time"""
    
    # Calculate date range
    today = date.today()
    if period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today - timedelta(days=30)
    else:  # year
        start_date = today - timedelta(days=365)
    
    # Query
    query = select(
        Application.applied_date,
        func.count().label("count"),
    ).where(
        Application.user_id == user_id,
        Application.deleted_at.is_(None),
        Application.applied_date >= start_date,
    ).group_by(
        Application.applied_date
    ).order_by(
        Application.applied_date
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    # Build data points with cumulative count
    data_points = []
    cumulative = 0
    date_counts = {row.applied_date: row.count for row in rows}
    
    current_date = start_date
    while current_date <= today:
        count = date_counts.get(current_date, 0)
        cumulative += count
        data_points.append(TrendDataPoint(
            date=current_date,
            count=count,
            cumulative=cumulative,
        ))
        current_date += timedelta(days=1)
    
    total = sum(dp.count for dp in data_points)
    days = (today - start_date).days or 1
    
    return TrendsResponse(
        period=period,
        data_points=data_points,
        total=total,
        average_per_day=round(total / days, 1),
    )


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get AI-generated insights using InsightsGenerator"""
    from app.ml.insights.insights_generator import InsightsGenerator
    
    # Fetch all user applications
    query = select(Application).where(
        Application.user_id == user_id,
        Application.deleted_at.is_(None),
    )
    
    result = await db.execute(query)
    applications = result.scalars().all()
    
    # Convert to dicts for the generator
    app_dicts = [
        {
            'id': str(app.id),
            'company_name': app.company_name,
            'role_title': app.role_title,
            'status': app.status,
            'source': app.source,
            'applied_date': app.applied_date,
        }
        for app in applications
    ]
    
    # Generate insights
    generator = InsightsGenerator()
    insights = generator.generate(app_dicts)
    
    # Convert to response format
    ai_insights = [
        AIInsight(
            type=insight.type,
            title=insight.title,
            description=insight.description,
            confidence=0.85,
        )
        for insight in insights
    ]
    
    return InsightsResponse(
        insights=ai_insights,
        generated_at=datetime.utcnow().isoformat(),
    )


@router.get("/ml-stats")
async def get_ml_stats(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Get ML self-learning stats for the feedback loop transparency widget.
    Returns total training examples, label breakdown, and whether the model is active.
    """
    from app.models.training_example import TrainingExample
    from app.ml.classifiers.learned_filter import learned_filter, MIN_EXAMPLES

    # Count training examples for this user
    user_total_q = select(func.count()).select_from(TrainingExample).where(
        TrainingExample.user_id == user_id
    )
    user_total = (await db.execute(user_total_q)).scalar() or 0

    user_positive_q = select(func.count()).select_from(TrainingExample).where(
        TrainingExample.user_id == user_id,
        TrainingExample.label == "positive"
    )
    user_positive = (await db.execute(user_positive_q)).scalar() or 0

    user_negative_q = select(func.count()).select_from(TrainingExample).where(
        TrainingExample.user_id == user_id,
        TrainingExample.label == "negative"
    )
    user_negative = (await db.execute(user_negative_q)).scalar() or 0

    # Global training data (what the model actually trains on)
    global_total_q = select(func.count()).select_from(TrainingExample)
    global_total = (await db.execute(global_total_q)).scalar() or 0

    return {
        "model_active": learned_filter.is_ready,
        "model_example_count": learned_filter.example_count,
        "min_examples_required": MIN_EXAMPLES,
        "user_decisions": user_total,
        "user_positive": user_positive,
        "user_negative": user_negative,
        "global_training_examples": global_total,
        "progress_pct": min(100, round((global_total / MIN_EXAMPLES) * 100)) if not learned_filter.is_ready else 100,
    }


@router.get("/ghosting")
async def get_ghosting_stats(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Get ghosting analytics: list of ghosted applications and summary stats.
    Used for the 'Ghost Town' widget on the analytics dashboard.
    """
    # Get all ghosted applications
    query = select(
        Application.id,
        Application.company_name,
        Application.role_title,
        Application.applied_date,
        Application.status_updated_at,
    ).where(
        Application.user_id == user_id,
        Application.deleted_at.is_(None),
        Application.status == "ghosted",
    ).order_by(Application.applied_date.desc()).limit(20)

    result = await db.execute(query)
    rows = result.all()

    today = date.today()

    ghosted = []
    for r in rows:
        days_waiting = (today - r.applied_date).days if r.applied_date else 0
        ghosted.append({
            "id": str(r.id),
            "company": r.company_name,
            "role": r.role_title,
            "applied_date": r.applied_date.isoformat() if r.applied_date else None,
            "days_waiting": days_waiting,
        })

    # Aggregate stats
    total_ghosted_q = select(func.count()).select_from(Application).where(
        Application.user_id == user_id,
        Application.deleted_at.is_(None),
        Application.status == "ghosted",
    )
    total_ghosted = (await db.execute(total_ghosted_q)).scalar() or 0

    total_apps_q = select(func.count()).select_from(Application).where(
        Application.user_id == user_id,
        Application.deleted_at.is_(None),
    )
    total_apps = (await db.execute(total_apps_q)).scalar() or 1

    ghost_rate = round((total_ghosted / total_apps) * 100, 1)

    return {
        "total_ghosted": total_ghosted,
        "ghost_rate": ghost_rate,
        "ghosted_applications": ghosted,
    }
