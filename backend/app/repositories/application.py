"""
Application Repository
Specialized repository for Application model with search and filtering.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Application
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    """Repository for Application CRUD with specialized methods."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Application, db)
    
    async def get_with_relations(self, id: UUID, user_id: UUID) -> Optional[Application]:
        """Get application with tags and events loaded."""
        query = (
            select(Application)
            .options(
                selectinload(Application.tags),
                selectinload(Application.events),
                selectinload(Application.notes),
            )
            .where(Application.id == id)
            .where(Application.user_id == user_id)
            .where(Application.deleted_at.is_(None))
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_for_user(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        status: Optional[List[str]] = None,
        search: Optional[str] = None,
        source: Optional[str] = None,
        order_by: str = "applied_date",
        desc: bool = True,
    ) -> tuple[List[Application], int]:
        """List applications for a user with filtering and pagination."""
        query = (
            select(Application)
            .options(selectinload(Application.tags))
            .where(Application.user_id == user_id)
            .where(Application.deleted_at.is_(None))
        )
        
        # Status filter
        if status:
            query = query.where(Application.status.in_(status))
        
        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Application.company_name.ilike(search_term),
                    Application.role_title.ilike(search_term),
                )
            )
        
        # Source filter
        if source:
            query = query.where(Application.source == source)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Apply ordering
        order_column = getattr(Application, order_by, Application.applied_date)
        query = query.order_by(order_column.desc() if desc else order_column.asc())
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        applications = list(result.scalars().all())
        
        return applications, total
    
    async def get_by_company_for_user(
        self,
        user_id: UUID,
        company_name: str,
    ) -> List[Application]:
        """Find applications by company name for a user."""
        search_term = f"%{company_name}%"
        query = (
            select(Application)
            .where(Application.user_id == user_id)
            .where(Application.company_name.ilike(search_term))
            .where(Application.deleted_at.is_(None))
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_stats_for_user(self, user_id: UUID) -> Dict[str, int]:
        """Get quick stats for a user."""
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
        ).where(
            Application.user_id == user_id,
            Application.deleted_at.is_(None),
        )
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total": row.total or 0,
            "active": row.active or 0,
            "interviews": row.interviews or 0,
            "offers": row.offers or 0,
        }
    
    async def full_text_search(
        self,
        user_id: UUID,
        query: str,
        page: int = 1,
        limit: int = 20,
        status: Optional[List[str]] = None,
    ) -> tuple[List[Application], int]:
        """
        Full-text search on applications using PostgreSQL tsvector.
        
        Uses weighted search: company_name (A), role_title (B), location (C).
        """
        from sqlalchemy import text
        
        base_query = (
            select(Application)
            .options(selectinload(Application.tags))
            .where(Application.user_id == user_id)
            .where(Application.deleted_at.is_(None))
        )
        
        # Add full-text search filter
        if query:
            # Use plainto_tsquery for simple search terms
            base_query = base_query.where(
                text("search_vector @@ plainto_tsquery('english', :search_query)")
            ).params(search_query=query)
            
            # Order by relevance (ts_rank)
            base_query = base_query.order_by(
                text("ts_rank(search_vector, plainto_tsquery('english', :search_query)) DESC")
            ).params(search_query=query)
        
        # Status filter
        if status:
            base_query = base_query.where(Application.status.in_(status))
        
        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Apply pagination
        offset = (page - 1) * limit
        base_query = base_query.offset(offset).limit(limit)
        
        result = await self.db.execute(base_query)
        applications = list(result.scalars().all())
        
        return applications, total

