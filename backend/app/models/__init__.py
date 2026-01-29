"""
Models Package
Export all SQLAlchemy models
"""

from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
from app.models.user import User
from app.models.application import Application, APPLICATION_STATUSES
from app.models.tag import Tag, application_tags
from app.models.event import Event, EVENT_TYPES
from app.models.note import Note
from app.models.email import Email, application_emails
from app.models.pending_application import PendingApplication

__all__ = [
    # Base
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    # Models
    "User",
    "Application",
    "Tag",
    "Event",
    "Note",
    "Email",
    "PendingApplication",
    # Junction tables
    "application_tags",
    "application_emails",
    # Constants
    "APPLICATION_STATUSES",
    "EVENT_TYPES",
]
