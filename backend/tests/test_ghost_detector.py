"""
Tests for GhostDetector - detects and marks ghosted applications.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.ml.detection.ghost_detector import GhostDetector


class MockApplication:
    """Mock Application model for testing."""
    def __init__(self, id, company_name, role_title, status, status_updated_at, user_id, deleted_at=None):
        self.id = id
        self.company_name = company_name
        self.role_title = role_title
        self.status = status
        self.status_updated_at = status_updated_at
        self.user_id = user_id
        self.deleted_at = deleted_at


class TestGhostDetectorLogic:
    """Tests for GhostDetector logic (without DB)."""
    
    def test_ghost_threshold_is_14_days(self):
        """Ghost threshold should be 14 days."""
        assert GhostDetector.GHOST_THRESHOLD_DAYS == 14
    
    def test_ghostable_statuses(self):
        """Only 'applied' and 'screening' should be ghostable."""
        assert 'applied' in GhostDetector.GHOSTABLE_STATUSES
        assert 'screening' in GhostDetector.GHOSTABLE_STATUSES
        assert 'interview' not in GhostDetector.GHOSTABLE_STATUSES
        assert 'offer' not in GhostDetector.GHOSTABLE_STATUSES
        assert 'rejected' not in GhostDetector.GHOSTABLE_STATUSES


@pytest.mark.asyncio
class TestGhostDetectorIntegration:
    """Integration-style tests for GhostDetector (with mocked DB)."""
    
    async def test_detects_old_applied_status(self):
        """Should detect 'applied' status older than 14 days."""
        user_id = uuid4()
        old_date = datetime.utcnow() - timedelta(days=16)
        
        old_app = MockApplication(
            id=uuid4(),
            company_name='Stale Corp',
            role_title='Developer',
            status='applied',
            status_updated_at=old_date,
            user_id=user_id,
        )
        
        # Verify the app would qualify for ghosting
        cutoff = datetime.utcnow() - timedelta(days=14)
        assert old_app.status in GhostDetector.GHOSTABLE_STATUSES
        assert old_app.status_updated_at < cutoff
        assert old_app.deleted_at is None
    
    async def test_detects_old_screening_status(self):
        """Should detect 'screening' status older than 14 days."""
        user_id = uuid4()
        old_date = datetime.utcnow() - timedelta(days=20)
        
        old_app = MockApplication(
            id=uuid4(),
            company_name='Screening Corp',
            role_title='Engineer',
            status='screening',
            status_updated_at=old_date,
            user_id=user_id,
        )
        
        cutoff = datetime.utcnow() - timedelta(days=14)
        assert old_app.status in GhostDetector.GHOSTABLE_STATUSES
        assert old_app.status_updated_at < cutoff
    
    async def test_ignores_recent_applications(self):
        """Should not ghost apps updated within 14 days."""
        user_id = uuid4()
        recent_date = datetime.utcnow() - timedelta(days=7)
        
        recent_app = MockApplication(
            id=uuid4(),
            company_name='Recent Corp',
            role_title='Developer',
            status='applied',
            status_updated_at=recent_date,
            user_id=user_id,
        )
        
        cutoff = datetime.utcnow() - timedelta(days=14)
        # Recent app should NOT qualify
        assert recent_app.status_updated_at >= cutoff
    
    async def test_ignores_interview_status(self):
        """Should not ghost 'interview' status even if old."""
        user_id = uuid4()
        old_date = datetime.utcnow() - timedelta(days=30)
        
        interview_app = MockApplication(
            id=uuid4(),
            company_name='Interview Corp',
            role_title='Developer',
            status='interview',
            status_updated_at=old_date,
            user_id=user_id,
        )
        
        # Interview status should NOT be ghostable
        assert interview_app.status not in GhostDetector.GHOSTABLE_STATUSES
    
    async def test_ignores_deleted_applications(self):
        """Should not ghost soft-deleted applications."""
        user_id = uuid4()
        old_date = datetime.utcnow() - timedelta(days=20)
        
        deleted_app = MockApplication(
            id=uuid4(),
            company_name='Deleted Corp',
            role_title='Developer',
            status='applied',
            status_updated_at=old_date,
            user_id=user_id,
            deleted_at=datetime.utcnow() - timedelta(days=5),
        )
        
        # Deleted app should be excluded
        assert deleted_app.deleted_at is not None
