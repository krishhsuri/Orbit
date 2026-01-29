"""
Note Model
User notes attached to applications
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application


class Note(Base, UUIDMixin, TimestampMixin):
    """Note model for application details"""
    
    __tablename__ = "notes"
    
    # Foreign key
    application_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="notes",
    )
    
    def __repr__(self) -> str:
        return f"<Note {self.id}>"
