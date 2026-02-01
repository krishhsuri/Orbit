"""
Insights Generator - Generate actionable insights from application data
Provides analytics-driven tips and observations to help users improve their job search.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """Represents a single insight/tip for the user."""
    title: str
    description: str
    type: str  # 'success', 'warning', 'tip', 'info'
    category: str  # 'response_rate', 'momentum', 'ghosted', 'conversion'
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class InsightsGenerator:
    """
    Generates personalized insights from user's application data.
    
    Insights include:
    - Response rates by source
    - Ghosted application warnings
    - Weekly momentum tracking
    - Interview conversion rates
    """
    
    def __init__(self):
        pass
    
    def generate(self, applications: List[Dict[str, Any]]) -> List[Insight]:
        """
        Generate insights from application data.
        
        Args:
            applications: List of application dicts
            
        Returns:
            List of Insight objects (max 5)
        """
        insights = []
        
        if not applications:
            insights.append(Insight(
                title="Start your job search!",
                description="Add your first job application to start tracking your progress.",
                type="tip",
                category="onboarding"
            ))
            return insights
        
        # Calculate various metrics
        total_apps = len(applications)
        
        # 1. Source performance insight
        source_insight = self._analyze_source_performance(applications)
        if source_insight:
            insights.append(source_insight)
        
        # 2. Ghosted rate warning
        ghosted_insight = self._analyze_ghosted_rate(applications)
        if ghosted_insight:
            insights.append(ghosted_insight)
        
        # 3. Weekly momentum
        momentum_insight = self._analyze_momentum(applications)
        if momentum_insight:
            insights.append(momentum_insight)
        
        # 4. Interview conversion rate
        conversion_insight = self._analyze_conversion_rate(applications)
        if conversion_insight:
            insights.append(conversion_insight)
        
        # 5. Recent success
        success_insight = self._analyze_recent_success(applications)
        if success_insight:
            insights.append(success_insight)
        
        # Return top 5 insights
        return insights[:5]
    
    def _analyze_source_performance(self, applications: List[Dict[str, Any]]) -> Optional[Insight]:
        """Analyze response rates by source."""
        source_stats = defaultdict(lambda: {'total': 0, 'responded': 0})
        
        for app in applications:
            source = app.get('source') or 'direct'
            source_stats[source]['total'] += 1
            
            # Responded = any status other than 'applied' or 'ghosted'
            if app.get('status') not in ['applied', 'ghosted']:
                source_stats[source]['responded'] += 1
        
        # Need at least 2 sources to compare
        if len(source_stats) < 2:
            return None
        
        # Calculate response rates
        for source in source_stats:
            total = source_stats[source]['total']
            responded = source_stats[source]['responded']
            source_stats[source]['response_rate'] = responded / total if total > 0 else 0
        
        # Find best source
        best_source = max(source_stats.items(), key=lambda x: x[1]['response_rate'])
        worst_source = min(source_stats.items(), key=lambda x: x[1]['response_rate'])
        
        if best_source[1]['response_rate'] > worst_source[1]['response_rate'] + 0.1:
            return Insight(
                title=f"{best_source[0].title()} works best for you",
                description=f"{best_source[0].title()} has a {best_source[1]['response_rate']:.0%} response rate vs {worst_source[1]['response_rate']:.0%} for {worst_source[0]}.",
                type="success",
                category="response_rate",
                data=dict(source_stats)
            )
        
        return None
    
    def _analyze_ghosted_rate(self, applications: List[Dict[str, Any]]) -> Optional[Insight]:
        """Check for high ghosted rate."""
        total = len(applications)
        ghosted = sum(1 for app in applications if app.get('status') == 'ghosted')
        
        if total < 5:
            return None
        
        ghosted_rate = ghosted / total
        
        if ghosted_rate > 0.4:
            return Insight(
                title="High ghost rate detected",
                description=f"{ghosted} of {total} applications ({ghosted_rate:.0%}) received no response. Consider following up after 1 week.",
                type="warning",
                category="ghosted",
                data={'ghosted_count': ghosted, 'total': total, 'rate': ghosted_rate}
            )
        elif ghosted_rate > 0.25:
            return Insight(
                title="Some applications may need follow-up",
                description=f"{ghosted} applications haven't received a response. A polite follow-up email can help.",
                type="tip",
                category="ghosted",
                data={'ghosted_count': ghosted, 'total': total, 'rate': ghosted_rate}
            )
        
        return None
    
    def _analyze_momentum(self, applications: List[Dict[str, Any]]) -> Optional[Insight]:
        """Analyze weekly application momentum."""
        now = datetime.utcnow()
        this_week_start = now - timedelta(days=now.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        
        this_week_count = 0
        last_week_count = 0
        
        for app in applications:
            applied_date = app.get('applied_date')
            if not applied_date:
                continue
            
            # Handle both date and datetime
            if isinstance(applied_date, str):
                try:
                    applied_date = datetime.fromisoformat(applied_date.replace('Z', '+00:00'))
                except:
                    continue
            elif hasattr(applied_date, 'replace'):  # date object
                applied_date = datetime.combine(applied_date, datetime.min.time())
            
            if applied_date >= this_week_start:
                this_week_count += 1
            elif applied_date >= last_week_start:
                last_week_count += 1
        
        if this_week_count > last_week_count and this_week_count >= 3:
            return Insight(
                title="Great momentum! 🚀",
                description=f"You applied to {this_week_count} jobs this week, up from {last_week_count} last week. Keep it up!",
                type="success",
                category="momentum",
                data={'this_week': this_week_count, 'last_week': last_week_count}
            )
        elif this_week_count < last_week_count and this_week_count < 3:
            return Insight(
                title="Keep the momentum going",
                description=f"Only {this_week_count} applications this week vs {last_week_count} last week. Aim for at least 5 per week.",
                type="tip",
                category="momentum",
                data={'this_week': this_week_count, 'last_week': last_week_count}
            )
        
        return None
    
    def _analyze_conversion_rate(self, applications: List[Dict[str, Any]]) -> Optional[Insight]:
        """Analyze interview conversion rate."""
        total = len(applications)
        if total < 5:
            return None
        
        interview_statuses = ['interview', 'offer', 'accepted']
        interviews = sum(1 for app in applications if app.get('status') in interview_statuses)
        
        interview_rate = interviews / total
        
        if interview_rate >= 0.15:
            return Insight(
                title="Strong interview rate! 💪",
                description=f"You're converting {interview_rate:.0%} of applications to interviews. Industry average is ~10%.",
                type="success",
                category="conversion",
                data={'interviews': interviews, 'total': total, 'rate': interview_rate}
            )
        elif interviews == 0 and total >= 10:
            return Insight(
                title="Time to optimize your resume?",
                description=f"No interviews from {total} applications. Consider getting resume feedback or tailoring applications.",
                type="tip",
                category="conversion",
                data={'interviews': interviews, 'total': total}
            )
        
        return None
    
    def _analyze_recent_success(self, applications: List[Dict[str, Any]]) -> Optional[Insight]:
        """Check for recent offers or acceptances."""
        success_statuses = ['offer', 'accepted']
        
        recent_successes = [
            app for app in applications
            if app.get('status') in success_statuses
        ]
        
        if recent_successes:
            offers = sum(1 for app in recent_successes if app.get('status') == 'offer')
            accepted = sum(1 for app in recent_successes if app.get('status') == 'accepted')
            
            if accepted > 0:
                return Insight(
                    title="Congratulations! 🎉",
                    description=f"You've accepted {accepted} offer(s). Great job on your job search!",
                    type="success",
                    category="success"
                )
            elif offers > 0:
                return Insight(
                    title="You have offer(s) pending! 🎯",
                    description=f"You have {offers} outstanding offer(s). Don't forget to respond!",
                    type="info",
                    category="success"
                )
        
        return None


# Singleton instance
insights_generator = InsightsGenerator()
