"""Wave 2 hygiene: email_thread_id, soft delete, events.updated_at, follow_up history.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-31 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("email_thread_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_applications_email_thread_id",
        "applications",
        ["email_thread_id"],
        unique=False,
    )

    op.add_column(
        "emails",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "events",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Allow append-only follow-up decision history (was unique=True).
    op.drop_index("ix_follow_up_results_application_id", table_name="follow_up_results")
    op.create_index(
        "ix_follow_up_results_application_id",
        "follow_up_results",
        ["application_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_follow_up_results_application_id", table_name="follow_up_results")
    op.create_index(
        "ix_follow_up_results_application_id",
        "follow_up_results",
        ["application_id"],
        unique=True,
    )

    op.drop_column("events", "updated_at")
    op.drop_column("emails", "deleted_at")
    op.drop_index("ix_applications_email_thread_id", table_name="applications")
    op.drop_column("applications", "email_thread_id")
