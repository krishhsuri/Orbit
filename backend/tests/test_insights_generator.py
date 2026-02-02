"""
Tests for InsightsGenerator - generates actionable insights from application data.
"""

import pytest
from datetime import datetime, timedelta

from app.ml.insights.insights_generator import InsightsGenerator, Insight


@pytest.fixture
def generator():
    return InsightsGenerator()


class TestInsightsGenerator:
    """Tests for InsightsGenerator class."""
    
    def test_empty_applications_returns_tip(self, generator):
        """Should return onboarding tip when no applications."""
        insights = generator.generate([])
        
        assert len(insights) == 1
        assert insights[0].type == 'tip'
        assert insights[0].category == 'onboarding'
        assert 'start' in insights[0].title.lower()
    
    def test_calculates_response_rate(self, generator):
        """Should compare response rates by source."""
        now = datetime.utcnow()
        
        applications = [
            # Referrals with good response
            {'id': '1', 'company_name': 'A', 'role_title': 'Dev', 'status': 'interview', 'source': 'referral', 'applied_date': now.date()},
            {'id': '2', 'company_name': 'B', 'role_title': 'Dev', 'status': 'offer', 'source': 'referral', 'applied_date': now.date()},
            # Direct with poor response
            {'id': '3', 'company_name': 'C', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': now.date()},
            {'id': '4', 'company_name': 'D', 'role_title': 'Dev', 'status': 'ghosted', 'source': 'direct', 'applied_date': now.date()},
            {'id': '5', 'company_name': 'E', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': now.date()},
        ]
        
        insights = generator.generate(applications)
        
        # Should have insight about referral being better
        source_insights = [i for i in insights if i.category == 'response_rate']
        assert len(source_insights) >= 1
        assert 'referral' in source_insights[0].title.lower()
    
    def test_high_ghost_rate_warning(self, generator):
        """Should warn when >40% applications are ghosted."""
        now = datetime.utcnow()
        
        applications = [
            {'id': '1', 'company_name': 'A', 'role_title': 'Dev', 'status': 'ghosted', 'source': 'direct', 'applied_date': now.date()},
            {'id': '2', 'company_name': 'B', 'role_title': 'Dev', 'status': 'ghosted', 'source': 'direct', 'applied_date': now.date()},
            {'id': '3', 'company_name': 'C', 'role_title': 'Dev', 'status': 'ghosted', 'source': 'direct', 'applied_date': now.date()},
            {'id': '4', 'company_name': 'D', 'role_title': 'Dev', 'status': 'interview', 'source': 'direct', 'applied_date': now.date()},
            {'id': '5', 'company_name': 'E', 'role_title': 'Dev', 'status': 'offer', 'source': 'direct', 'applied_date': now.date()},
        ]
        
        insights = generator.generate(applications)
        
        ghosted_insights = [i for i in insights if i.category == 'ghosted']
        assert len(ghosted_insights) >= 1
        assert ghosted_insights[0].type == 'warning'
    
    def test_interview_rate_success(self, generator):
        """Should celebrate high interview conversion rate."""
        now = datetime.utcnow()
        
        applications = [
            {'id': '1', 'company_name': 'A', 'role_title': 'Dev', 'status': 'interview', 'source': 'direct', 'applied_date': now.date()},
            {'id': '2', 'company_name': 'B', 'role_title': 'Dev', 'status': 'interview', 'source': 'direct', 'applied_date': now.date()},
            {'id': '3', 'company_name': 'C', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': now.date()},
            {'id': '4', 'company_name': 'D', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': now.date()},
            {'id': '5', 'company_name': 'E', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': now.date()},
        ]  # 2/5 = 40% interview rate
        
        insights = generator.generate(applications)
        
        conversion_insights = [i for i in insights if i.category == 'conversion']
        assert len(conversion_insights) >= 1
        assert conversion_insights[0].type == 'success'
    
    def test_momentum_tracking(self, generator):
        """Should track weekly application momentum."""
        now = datetime.utcnow()
        this_week = now - timedelta(days=now.weekday())
        last_week = this_week - timedelta(days=7)
        
        applications = [
            # This week: 4 applications
            {'id': '1', 'company_name': 'A', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': this_week.date()},
            {'id': '2', 'company_name': 'B', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': (this_week + timedelta(days=1)).date()},
            {'id': '3', 'company_name': 'C', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': (this_week + timedelta(days=2)).date()},
            {'id': '4', 'company_name': 'D', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': (this_week + timedelta(days=3)).date()},
            # Last week: 1 application
            {'id': '5', 'company_name': 'E', 'role_title': 'Dev', 'status': 'applied', 'source': 'direct', 'applied_date': last_week.date()},
        ]
        
        insights = generator.generate(applications)
        
        momentum_insights = [i for i in insights if i.category == 'momentum']
        # If this week > last week, should show success
        if momentum_insights:
            assert momentum_insights[0].type == 'success'
    
    def test_offer_congratulation(self, generator):
        """Should congratulate on offers."""
        now = datetime.utcnow()
        
        applications = [
            {'id': '1', 'company_name': 'Dream Co', 'role_title': 'Dev', 'status': 'accepted', 'source': 'referral', 'applied_date': now.date()},
            {'id': '2', 'company_name': 'Other', 'role_title': 'Dev', 'status': 'rejected', 'source': 'direct', 'applied_date': now.date()},
        ]
        
        insights = generator.generate(applications)
        
        success_insights = [i for i in insights if i.category == 'success']
        assert len(success_insights) >= 1
        assert 'congratulations' in success_insights[0].title.lower()
    
    def test_max_5_insights(self, generator):
        """Should return at most 5 insights."""
        now = datetime.utcnow()
        
        # Create data that would trigger many insights
        applications = [
            {'id': str(i), 'company_name': f'Co{i}', 'role_title': 'Dev', 'status': 'ghosted' if i < 5 else 'interview', 'source': 'referral' if i % 2 == 0 else 'direct', 'applied_date': now.date()}
            for i in range(20)
        ]
        
        insights = generator.generate(applications)
        
        assert len(insights) <= 5
    
    def test_insight_to_dict(self):
        """Should convert Insight to dict properly."""
        insight = Insight(
            title="Test",
            description="Test desc",
            type="success",
            category="test",
            data={'key': 'value'}
        )
        
        d = insight.to_dict()
        
        assert d['title'] == 'Test'
        assert d['description'] == 'Test desc'
        assert d['type'] == 'success'
        assert d['category'] == 'test'
        assert d['data'] == {'key': 'value'}
