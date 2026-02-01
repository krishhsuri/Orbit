"""
Ghost Detector - Automatically detect ghosted applications
Marks applications as "ghosted" when there's no response after a threshold period.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID
import logging

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class GhostDetector:
    """
    Detects applications that have been ghosted (no response).
    
    Criteria for ghosting:
    - Status is 'applied' or 'screening'
    - No status update for GHOST_THRESHOLD_DAYS
    - No linked emails received recently
    """
    
    # Number of days without response to consider ghosted
    GHOST_THRESHOLD_DAYS = 14
    
    # Statuses that can be marked as ghosted
    GHOSTABLE_STATUSES = ['applied', 'screening']
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def detect_and_mark_ghosted(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Detect and mark ghosted applications for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of applications that were marked as ghosted
        """
        from app.models import Application, Event
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.GHOST_THRESHOLD_DAYS)
        
        # Query for stale applications
        stmt = select(Application).where(
            and_(
                Application.user_id == user_id,
                Application.status.in_(self.GHOSTABLE_STATUSES),
                Application.status_updated_at < cutoff_date,
                Application.deleted_at.is_(None)
            )
        )
        
        result = await self.db.execute(stmt)
        ghosted_apps = result.scalars().all()
        
        marked_apps = []
        
        for app in ghosted_apps:
            old_status = app.status
            
            # Update status to ghosted
            app.status = 'ghosted'
            app.status_updated_at = datetime.utcnow()
            
            # Create event for audit trail
            event = Event(
                application_id=app.id,
                event_type='auto_ghosted',
                title='Marked as Ghosted',
                description=f'No response for {self.GHOST_THRESHOLD_DAYS}+ days',
                data={
                    'previous_status': old_status,
                    'days_since_update': (datetime.utcnow() - app.status_updated_at).days if app.status_updated_at else self.GHOST_THRESHOLD_DAYS,
                    'detected_by': 'ghost_detector'
                }
            )
            self.db.add(event)
            
            marked_apps.append({
                'id': str(app.id),
                'company_name': app.company_name,
                'role_title': app.role_title,
                'previous_status': old_status,
                'days_since_update': (datetime.utcnow() - app.status_updated_at).days if app.status_updated_at else self.GHOST_THRESHOLD_DAYS
            })
            
            logger.info(f"Marked as ghosted: {app.company_name} - {app.role_title}")
        
        if marked_apps:
            await self.db.commit()
            logger.info(f"Marked {len(marked_apps)} applications as ghosted for user {user_id}")
        
        return marked_apps
    
    async def get_ghost_candidates(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get applications that are candidates for ghosting (preview without marking).
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of applications that would be marked as ghosted
        """
        from app.models import Application
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.GHOST_THRESHOLD_DAYS)
        
        stmt = select(Application).where(
            and_(
                Application.user_id == user_id,
                Application.status.in_(self.GHOSTABLE_STATUSES),
                Application.status_updated_at < cutoff_date,
                Application.deleted_at.is_(None)
            )
        )
        
        result = await self.db.execute(stmt)
        candidates = result.scalars().all()
        
        return [
            {
                'id': str(app.id),
                'company_name': app.company_name,
                'role_title': app.role_title,
                'status': app.status,
                'days_since_update': (datetime.utcnow() - app.status_updated_at).days if app.status_updated_at else self.GHOST_THRESHOLD_DAYS
            }
            for app in candidates
        ]
