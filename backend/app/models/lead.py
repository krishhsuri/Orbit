"""
Lead Model
Global job discovery entries extracted from emails.
Shared across all users — not scoped to a single user.
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Lead(Base, UUIDMixin, TimestampMixin):
    """
    A job opportunity discovered from a user's email sync.
    Visible to ALL users (global shared job board).
    """

    __tablename__ = "leads"
    __table_args__ = (
        Index("idx_leads_company", "company"),
        Index("idx_leads_role", "role"),
        Index("idx_leads_status", "status"),
    )

    # Core fields
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_site: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        doc="Platform where the job is listed (LinkedIn, Wellfound, etc.)"
    )
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Recruiter info
    recruiter_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recruiter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Dedup — email ID that generated this lead (prevents duplicates)
    source_email_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True,
        doc="Gmail message ID that sourced this lead"
    )

    # When the job was originally found
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active",
        doc="active or archived"
    )

    def __repr__(self) -> str:
        return f"<Lead {self.company} - {self.role}>"
