"""
Base Repository
Generic async CRUD repository pattern for SQLAlchemy models.
"""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository with async CRUD operations.
    
    Usage:
        class ApplicationRepository(BaseRepository[Application]):
            def __init__(self, db: AsyncSession):
                super().__init__(Application, db)
    """
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get(self, id: UUID) -> Optional[ModelType]:
        """Get a single record by ID."""
        query = select(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """Get a single record by a specific field."""
        column = getattr(self.model, field, None)
        if column is None:
            raise ValueError(f"Field {field} does not exist on {self.model.__name__}")
        
        query = select(self.model).where(column == value)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        desc: bool = True,
    ) -> List[ModelType]:
        """Get all records with optional filtering and pagination."""
        query = select(self.model)
        
        # Apply soft delete filter if model has deleted_at
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    if isinstance(value, list):
                        query = query.where(column.in_(value))
                    else:
                        query = query.where(column == value)
        
        # Apply ordering
        if order_by:
            order_column = getattr(self.model, order_by, None)
            if order_column is not None:
                query = query.order_by(order_column.desc() if desc else order_column.asc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering."""
        query = select(func.count()).select_from(self.model)
        
        # Apply soft delete filter if model has deleted_at
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    query = query.where(column == value)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def create(self, data: Dict[str, Any]) -> ModelType:
        """Create a new record."""
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance
    
    async def update(self, id: UUID, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update an existing record."""
        instance = await self.get(id)
        if not instance:
            return None
        
        for field, value in data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        
        if hasattr(instance, 'updated_at'):
            instance.updated_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(instance)
        return instance
    
    async def delete(self, id: UUID, soft: bool = True) -> bool:
        """Delete a record (soft delete by default)."""
        instance = await self.get(id)
        if not instance:
            return False
        
        if soft and hasattr(instance, 'deleted_at'):
            instance.deleted_at = datetime.utcnow()
        else:
            await self.db.delete(instance)
        
        await self.db.flush()
        return True
    
    async def commit(self):
        """Commit the current transaction."""
        await self.db.commit()
    
    async def rollback(self):
        """Rollback the current transaction."""
        await self.db.rollback()
