"""
Training Example Model
Stores confirmed/rejected email decisions for self-learning feedback loop.
"""

from uuid import UUID
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class TrainingExample(Base, UUIDMixin, TimestampMixin):
    """
    Each row = one user decision (confirm or reject) on a pending email.
    Used globally to train a TF-IDF + LogReg classifier.
    """
    __tablename__ = "training_examples"
    __table_args__ = (
        Index("idx_training_label", "label"),
    )

    # Who made the decision
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Original email data
    email_subject: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    email_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_from: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    # Label: "positive" (confirmed) or "negative" (rejected)
    label: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<TrainingExample {self.label}: {self.email_subject[:40]}>"
