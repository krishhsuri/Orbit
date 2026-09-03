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
from app.models.lead import Lead
from app.models.training_example import TrainingExample
from app.models.follow_up_result import FollowUpResult
from app.models.llm_call import LLMCall
from app.models.agent_run import AgentRun
from app.models.outreach_action import OutreachAction
from app.models.outcome import Outcome

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
    "Lead",
    "TrainingExample",
    "FollowUpResult",
    "LLMCall",
    "AgentRun",
    "OutreachAction",
    "Outcome",
    # Junction tables
    "application_tags",
    "application_emails",
    # Constants
    "APPLICATION_STATUSES",
    "EVENT_TYPES",
]
