"""
Email Model
Synced emails from Gmail for application tracking
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Table,
    Column,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import SoftDeleteMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.application import Application


class Email(Base, UUIDMixin, SoftDeleteMixin):
    """Synced email model"""

    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint("user_id", "gmail_id", name="uq_emails_user_gmail"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    gmail_id: Mapped[str] = mapped_column(String(255), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_preview: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Full or truncated body; callers use smart_truncate
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    is_application_related: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    classification: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="emails",
    )

    applications: Mapped[List["Application"]] = relationship(
        "Application",
        secondary="application_emails",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Email {self.subject}>"


application_emails = Table(
    "application_emails",
    Base.metadata,
    Column(
        "application_id",
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "email_id",
        PGUUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "linked_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
    Column(
        "linked_by",
        String(20),
        server_default="auto",
        nullable=False,
    ),
)
