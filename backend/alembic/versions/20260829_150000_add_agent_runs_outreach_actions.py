"""add agent_runs and outreach_actions tables



Revision ID: e5f6a7b8c9d0

Revises: d4e5f6a7b8c9

Create Date: 2026-08-29 15:00:00.000000



"""

from typing import Sequence, Union



from alembic import op

import sqlalchemy as sa

from sqlalchemy.dialects import postgresql



revision: str = "e5f6a7b8c9d0"

down_revision: Union[str, None] = "d4e5f6a7b8c9"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None





def upgrade() -> None:

    op.create_table(

        "agent_runs",

        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),

        sa.Column("user_id", sa.UUID(), nullable=False),

        sa.Column("application_id", sa.UUID(), nullable=False),

        sa.Column("trigger", sa.String(length=32), nullable=False),

        sa.Column("status", sa.String(length=32), nullable=False),

        sa.Column("tool_trace", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.Column("iterations", sa.Integer(), nullable=False),

        sa.Column("tool_call_count", sa.Integer(), nullable=False),

        sa.Column("prompt_tokens", sa.Integer(), nullable=False),

        sa.Column("completion_tokens", sa.Integer(), nullable=False),

        sa.Column("estimated_cost_usd", sa.Numeric(precision=12, scale=8), nullable=False),

        sa.Column("latency_ms", sa.Numeric(precision=12, scale=3), nullable=False),

        sa.Column("final_decision", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("policy_vetoes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.Column("error_message", sa.Text(), nullable=True),

        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),

        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),

        sa.PrimaryKeyConstraint("id"),

    )

    op.create_index(op.f("ix_agent_runs_application_id"), "agent_runs", ["application_id"], unique=False)

    op.create_index(op.f("ix_agent_runs_user_id"), "agent_runs", ["user_id"], unique=False)



    op.create_table(

        "outreach_actions",

        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),

        sa.Column("user_id", sa.UUID(), nullable=False),

        sa.Column("application_id", sa.UUID(), nullable=False),

        sa.Column("agent_run_id", sa.UUID(), nullable=True),

        sa.Column("action_type", sa.String(length=32), nullable=False),

        sa.Column("draft", sa.Text(), nullable=True),

        sa.Column("risk_tier", sa.String(length=16), nullable=False),

        sa.Column("approval_mode", sa.String(length=16), nullable=False),

        sa.Column("status", sa.String(length=32), nullable=False),

        sa.Column("gmail_message_id", sa.String(length=255), nullable=True),

        sa.Column("thread_id", sa.String(length=255), nullable=True),

        sa.Column("idempotency_key", sa.String(length=255), nullable=False),

        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),

        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),

        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint("idempotency_key", name="uq_outreach_idempotency_key"),

    )

    op.create_index(op.f("ix_outreach_actions_agent_run_id"), "outreach_actions", ["agent_run_id"], unique=False)

    op.create_index(op.f("ix_outreach_actions_application_id"), "outreach_actions", ["application_id"], unique=False)

    op.create_index(op.f("ix_outreach_actions_user_id"), "outreach_actions", ["user_id"], unique=False)





def downgrade() -> None:

    op.drop_index(op.f("ix_outreach_actions_user_id"), table_name="outreach_actions")

    op.drop_index(op.f("ix_outreach_actions_application_id"), table_name="outreach_actions")

    op.drop_index(op.f("ix_outreach_actions_agent_run_id"), table_name="outreach_actions")

    op.drop_table("outreach_actions")

    op.drop_index(op.f("ix_agent_runs_user_id"), table_name="agent_runs")

    op.drop_index(op.f("ix_agent_runs_application_id"), table_name="agent_runs")

    op.drop_table("agent_runs")

