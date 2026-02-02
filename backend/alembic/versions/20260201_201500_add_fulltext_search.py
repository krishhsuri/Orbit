"""Add full-text search to applications

Revision ID: 20260201_201500
Revises: 20260129_182531
Create Date: 2026-02-01 20:15:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260201_201500_add_fulltext_search'
down_revision: Union[str, None] = '20260129_182531_create_pending_applications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add full-text search vector column and GIN index."""
    
    # Add tsvector column for full-text search
    # Uses STORED generated column for automatic updates
    op.execute("""
        ALTER TABLE applications 
        ADD COLUMN IF NOT EXISTS search_vector tsvector 
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(company_name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(role_title, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(location, '')), 'C')
        ) STORED;
    """)
    
    # Create GIN index for fast full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_search_vector 
        ON applications USING GIN(search_vector);
    """)
    
    # Create additional indexes for common query patterns
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_status 
        ON applications(status) 
        WHERE deleted_at IS NULL;
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_user_status 
        ON applications(user_id, status) 
        WHERE deleted_at IS NULL;
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_applied_date 
        ON applications(applied_date DESC) 
        WHERE deleted_at IS NULL;
    """)


def downgrade() -> None:
    """Remove full-text search components."""
    op.execute("DROP INDEX IF EXISTS idx_applications_applied_date;")
    op.execute("DROP INDEX IF EXISTS idx_applications_user_status;")
    op.execute("DROP INDEX IF EXISTS idx_applications_status;")
    op.execute("DROP INDEX IF EXISTS idx_applications_search_vector;")
    op.execute("ALTER TABLE applications DROP COLUMN IF EXISTS search_vector;")
