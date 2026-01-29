"""
Tag Model
User-defined tags for organizing applications
"""

from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.application import Application


class Tag(Base, UUIDMixin, TimestampMixin):
    """Tag model for organizing applications"""
    
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )
    
    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Fields
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(
        String(7),
        default="#6366f1",
        server_default="#6366f1",
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="tags",
    )
    
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        secondary="application_tags",
        back_populates="tags",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


# Junction table for many-to-many relationship
from sqlalchemy import Table, Column, DateTime, func

application_tags = Table(
    "application_tags",
    Base.metadata,
    Column(
        "application_id",
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        PGUUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
)
