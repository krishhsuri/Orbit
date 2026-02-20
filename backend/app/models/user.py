"""
User Model
Stores user account information and preferences
"""

from datetime import datetime
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.tag import Tag
    from app.models.email import Email


class User(Base, UUIDMixin, TimestampMixin):
    """User account model"""
    
    __tablename__ = "users"
    
    # Core fields
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False,
        index=True,
    )
    google_id: Mapped[str | None] = mapped_column(
        String(255), 
        unique=True, 
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Settings stored as JSON
    preferences: Mapped[dict] = mapped_column(
        JSONB, 
        server_default="{}",
        default=dict,
    )
    
    # Auth tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
    )

    # Gmail Integration
    gmail_refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
    )
    gmail_sync_enabled: Mapped[bool] = mapped_column(default=False)
    gmail_last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
    )
    gmail_last_synced_email_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        doc="Gmail message ID of the newest email processed in last sync"
    )
    
    # Relationships
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    emails: Mapped[List["Email"]] = relationship(
        "Email",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
