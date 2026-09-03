"""add leads.user_id and scope dedup per user

Revision ID: d4e5f6a7b8c9
Revises: c7f8e9d0a1b2
Create Date: 2026-08-29 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c7f8e9d0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_leads_user_id"), "leads", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_leads_user_id_users",
        "leads",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_lead_email_company_role", "leads", type_="unique")
    op.create_unique_constraint(
        "uq_lead_user_email_company_role",
        "leads",
        ["user_id", "source_email_id", "company", "role"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_lead_user_email_company_role", "leads", type_="unique")
    op.create_unique_constraint(
        "uq_lead_email_company_role",
        "leads",
        ["source_email_id", "company", "role"],
    )
    op.drop_constraint("fk_leads_user_id_users", "leads", type_="foreignkey")
    op.drop_index(op.f("ix_leads_user_id"), table_name="leads")
    op.drop_column("leads", "user_id")
