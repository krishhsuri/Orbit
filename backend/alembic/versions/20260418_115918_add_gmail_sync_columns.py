"""add_gmail_sync_columns

Revision ID: eb8383aa7f6e
Revises: 834aab695e36
Create Date: 2026-04-18 11:59:18.061096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb8383aa7f6e'
down_revision: Union[str, None] = '834aab695e36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('gmail_last_synced_sent_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'gmail_last_synced_sent_id')
