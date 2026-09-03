"""add llm_calls audit table

Revision ID: c7f8e9d0a1b2
Revises: 82c0a322cfaf
Create Date: 2026-08-29 03:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7f8e9d0a1b2"
down_revision: Union[str, None] = "82c0a322cfaf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_calls",
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("purpose", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("error_class", sa.String(length=64), nullable=True),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_calls_purpose"), "llm_calls", ["purpose"], unique=False)
    op.create_index(op.f("ix_llm_calls_run_id"), "llm_calls", ["run_id"], unique=False)
    op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"], unique=False)
    op.create_index(
        "ix_llm_calls_purpose_created_at",
        "llm_calls",
        ["purpose", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_llm_calls_purpose_created_at", table_name="llm_calls")
    op.drop_index("ix_llm_calls_created_at", table_name="llm_calls")
    op.drop_index(op.f("ix_llm_calls_run_id"), table_name="llm_calls")
    op.drop_index(op.f("ix_llm_calls_purpose"), table_name="llm_calls")
    op.drop_table("llm_calls")
