"""
Follow-Up Result Model
Stores pre-computed follow-up evaluations from Agent B.
Populated by ARQ cron (all users, 6h skip) or POST /agents/scan-now (current user).
The /agents page reads from this table — no on-the-fly LLM on page load.
"""

from uuid import UUID
from datetime import datetime

from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class FollowUpResult(Base, UUIDMixin, TimestampMixin):
    """
    Persisted output of Agent B (Follow-up Decision & Drafting Agent).
    Append-only history — one evaluation row per scan.
    """
    __tablename__ = "follow_up_results"

    application_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    should_follow_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    days_since_last_contact: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email_draft: Mapped[str | None] = mapped_column(Text, nullable=True)

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    application = relationship("Application", backref="follow_up_result")
    user = relationship("User", backref="follow_up_results")

    def __repr__(self) -> str:
        return f"<FollowUpResult app={self.application_id} follow_up={self.should_follow_up}>"
