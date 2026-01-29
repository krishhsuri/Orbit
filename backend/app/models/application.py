"""
Application Model
Core model for tracking job applications
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import (
    String, 
    Text, 
    Integer, 
    SmallInteger, 
    Date, 
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.tag import Tag
    from app.models.event import Event
    from app.models.note import Note


# Valid status values
APPLICATION_STATUSES = [
    "applied",      # Application submitted
    "screening",    # Recruiter screening
    "oa",           # Online assessment
    "interview",    # Interview stage(s)
    "offer",        # Received offer
    "accepted",     # Accepted offer
    "rejected",     # Rejected by company
    "withdrawn",    # Withdrawn by user
    "ghosted",      # No response (auto-detected)
]


class Application(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Job application model"""
    
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "priority BETWEEN 1 AND 10",
            name="ck_applications_priority_range",
        ),
        Index("idx_applications_user_status", "user_id", "status"),
        Index("idx_applications_user_date", "user_id", "applied_date"),
    )
    
    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Core fields
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="applied",
        server_default="applied",
    )
    
    # Details
    applied_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        server_default="USD",
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Tracking
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referrer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[int] = mapped_column(
        SmallInteger,
        default=5,
        server_default="5",
    )
    
    # Flexible metadata
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        server_default="{}",
        default=dict,
    )
    
    # Status tracking
    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="applications",
    )
    
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="application_tags",
        back_populates="applications",
        lazy="selectin",
    )
    
    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Event.created_at.desc()",
    )
    
    notes: Mapped[List["Note"]] = relationship(
        "Note",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Note.created_at.desc()",
    )
    
    def __repr__(self) -> str:
        return f"<Application {self.company_name} - {self.role_title}>"
