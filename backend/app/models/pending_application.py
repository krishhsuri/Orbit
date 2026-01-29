"""
Pending Application Model
Stores AI-parsed applications waiting for user confirmation.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin

class PendingApplication(Base, UUIDMixin, TimestampMixin):
    """
    Represents a job application detected from email but not yet confirmed.
    """
    __tablename__ = "pending_applications"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )

    # Gmail message ID to prevent duplicate processing
    email_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # Original email data for reference
    email_subject: Mapped[str] = mapped_column(String(500), nullable=False)
    email_snippet: Mapped[str] = mapped_column(String(1000), nullable=True)
    email_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # AI Parsed Data
    parsed_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parsed_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parsed_status: Mapped[str | None] = mapped_column(String(50), nullable=True) # e.g. "applied", "interview"
    parsed_job_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    
    # Overall confidence in the parsing (0.0 - 1.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Status of this pending item
    # "pending": waiting for review
    # "confirmed": user accepted it (converted to Application)
    # "rejected": user dismissed it
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # Relationships
    user = relationship("User", backref="pending_applications")

    def __repr__(self) -> str:
        return f"<PendingApplication {self.parsed_company} - {self.parsed_role}>"
