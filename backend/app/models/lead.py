"""
Lead Model
Job discovery entries extracted from a user's email sync.
Scoped per user — not a global board of other users' Gmail data.
"""

from typing import Optional
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import String, Text, DateTime, Index, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Lead(Base, UUIDMixin, TimestampMixin):
    """A job opportunity discovered from a user's email sync."""

    __tablename__ = "leads"
    __table_args__ = (
        Index("idx_leads_company", "company"),
        Index("idx_leads_role", "role"),
        Index("idx_leads_status", "status"),
        UniqueConstraint(
            "user_id",
            "source_email_id",
            "company",
            "role",
            name="uq_lead_user_email_company_role",
        ),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
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

    # Dedup — email ID that generated this lead
    # NOTE: NOT unique alone — one digest email generates many leads.
    # Use composite unique (source_email_id, company, role) instead.
    source_email_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True,
        doc="Gmail message ID that sourced this lead"
    )

    # Enriched fields extracted from digest emails
    stipend: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_from_digest: Mapped[bool] = mapped_column(default=False, doc="True if extracted from a job digest email")

    # When the job was originally found
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active",
        doc="active or archived"
    )

    def __repr__(self) -> str:
        return f"<Lead {self.company} - {self.role}>"
