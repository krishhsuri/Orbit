"""
Event Model
Timeline events for application tracking
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.application import Application


# Valid event types
EVENT_TYPES = [
    "created",          # Application created
    "status_change",    # Status updated (data: {from, to})
    "interview",        # Interview scheduled (data: {round, interviewer, notes})
    "note_added",       # Note added
    "email_linked",     # Email linked to application
    "reminder",         # User set reminder
    "follow_up",        # Follow-up scheduled/sent
]


class Event(Base, UUIDMixin):
    """Timeline event model"""
    
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_app_created", "application_id", "created_at"),
    )
    
    # Foreign key
    application_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Fields
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Flexible data storage
    data: Mapped[dict] = mapped_column(
        JSONB,
        server_default="{}",
        default=dict,
    )
    
    # Optional scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    
    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="events",
    )
    
    def __repr__(self) -> str:
        return f"<Event {self.event_type} @ {self.created_at}>"
