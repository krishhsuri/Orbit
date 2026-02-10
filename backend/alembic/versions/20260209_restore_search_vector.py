"""restore_search_vector

Revision ID: 20260209_restore_search
Revises: b61a59e0aa6b
Create Date: 2026-02-09 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260209_restore_search'
down_revision: Union[str, None] = 'b61a59e0aa6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Restore search_vector column and indexes that were dropped."""
    # Restore search_vector computed column
    op.add_column('applications', sa.Column(
        'search_vector',
        postgresql.TSVECTOR(),
        sa.Computed(
            "(setweight(to_tsvector('english', COALESCE(company_name, '')), 'A') || "
            "setweight(to_tsvector('english', COALESCE(role_title, '')), 'B') || "
            "setweight(to_tsvector('english', COALESCE(location, '')), 'C'))",
            persisted=True
        ),
        nullable=True
    ))
    
    # Recreate GIN index for full-text search
    op.create_index(
        'idx_applications_search_vector',
        'applications',
        ['search_vector'],
        unique=False,
        postgresql_using='gin'
    )
    
    # Recreate partial indexes
    op.create_index(
        'idx_applications_status',
        'applications',
        ['status'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    
    op.create_index(
        'idx_applications_applied_date',
        'applications',
        [sa.text('applied_date DESC')],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade() -> None:
    """Drop the restored search_vector and indexes."""
    op.drop_index('idx_applications_applied_date', table_name='applications')
    op.drop_index('idx_applications_status', table_name='applications')
    op.drop_index('idx_applications_search_vector', table_name='applications')
    op.drop_column('applications', 'search_vector')
