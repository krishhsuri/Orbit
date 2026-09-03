"""Observed outcomes from sent outreach (reply detection)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.outreach_action import OutreachAction
    from app.models.user import User


class Outcome(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "outcomes"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outreach_action_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("outreach_actions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    reply_gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    days_to_reply: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_change: Mapped[str | None] = mapped_column(String(50), nullable=True)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped["User"] = relationship("User", backref="outcomes")
    application: Mapped["Application"] = relationship("Application", backref="outcomes")
    outreach_action: Mapped["OutreachAction"] = relationship(
        "OutreachAction", backref="outcome"
    )

    def __repr__(self) -> str:
        return f"<Outcome {self.reply_classification} action={self.outreach_action_id}>"
