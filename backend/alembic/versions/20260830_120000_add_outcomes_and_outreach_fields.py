"""extend outreach_actions and add outcomes table



Revision ID: f6a7b8c9d0e1

Revises: e5f6a7b8c9d0

Create Date: 2026-08-30 12:00:00.000000



"""

from typing import Sequence, Union



from alembic import op

import sqlalchemy as sa



revision: str = "f6a7b8c9d0e1"

down_revision: Union[str, None] = "e5f6a7b8c9d0"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None





def upgrade() -> None:

    op.add_column("outreach_actions", sa.Column("undo_until", sa.DateTime(timezone=True), nullable=True))

    op.add_column("outreach_actions", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("outreach_actions", sa.Column("to_address", sa.String(length=255), nullable=True))

    op.add_column("outreach_actions", sa.Column("subject", sa.String(length=500), nullable=True))

    op.add_column("outreach_actions", sa.Column("error_message", sa.Text(), nullable=True))



    op.create_table(

        "outcomes",

        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),

        sa.Column("user_id", sa.UUID(), nullable=False),

        sa.Column("application_id", sa.UUID(), nullable=False),

        sa.Column("outreach_action_id", sa.UUID(), nullable=False),

        sa.Column("reply_gmail_message_id", sa.String(length=255), nullable=True),

        sa.Column("reply_classification", sa.String(length=32), nullable=False),

        sa.Column("days_to_reply", sa.Integer(), nullable=True),

        sa.Column("status_change", sa.String(length=50), nullable=True),

        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),

        sa.ForeignKeyConstraint(["outreach_action_id"], ["outreach_actions.id"], ondelete="CASCADE"),

        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint("outreach_action_id"),

    )

    op.create_index(op.f("ix_outcomes_application_id"), "outcomes", ["application_id"], unique=False)

    op.create_index(op.f("ix_outcomes_outreach_action_id"), "outcomes", ["outreach_action_id"], unique=False)

    op.create_index(op.f("ix_outcomes_user_id"), "outcomes", ["user_id"], unique=False)





def downgrade() -> None:

    op.drop_index(op.f("ix_outcomes_user_id"), table_name="outcomes")

    op.drop_index(op.f("ix_outcomes_outreach_action_id"), table_name="outcomes")

    op.drop_index(op.f("ix_outcomes_application_id"), table_name="outcomes")

    op.drop_table("outcomes")

    op.drop_column("outreach_actions", "error_message")

    op.drop_column("outreach_actions", "subject")

    op.drop_column("outreach_actions", "to_address")

    op.drop_column("outreach_actions", "sent_at")

    op.drop_column("outreach_actions", "undo_until")

