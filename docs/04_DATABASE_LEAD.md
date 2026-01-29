# Database Lead — Orbit

> **Owner:** Database Lead  
> **Scope:** Schema design, migrations, queries, performance, data integrity

---

## 🎯 Mission

Design a **clean, efficient database** for Orbit. The schema should support all current features while being flexible for future growth. Prioritize query performance and data integrity.

---

## 📐 Database Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATABASE ARCHITECTURE                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│                    ┌─────────────────┐                           │
│                    │   PostgreSQL    │                           │
│                    │      15+        │                           │
│                    └────────┬────────┘                           │
│                             │                                    │
│         ┌───────────────────┼───────────────────┐               │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   users     │    │applications │    │   emails    │         │
│  │   (auth)    │───▶│   (core)    │◀───│  (linked)   │         │
│  └─────────────┘    └──────┬──────┘    └─────────────┘         │
│                            │                                    │
│         ┌──────────────────┼──────────────────┐                 │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────┐          │
│  │    tags     │   │   events     │   │   notes     │          │
│  │ (organize)  │   │ (timeline)   │   │  (details)  │          │
│  └─────────────┘   └──────────────┘   └─────────────┘          │
│                                                                   │
│  Key Features:                                                   │
│  • UUID primary keys (security, distribution)                   │
│  • Soft deletes (data recovery)                                 │
│  • Timestamps on all tables (audit trail)                       │
│  • JSONB for flexible metadata                                  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📊 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 ER DIAGRAM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐         ┌──────────────┐         ┌────────────┐            │
│  │   users    │─────────│ applications │─────────│   events   │            │
│  │            │   1:N   │              │   1:N   │            │            │
│  │ id (PK)    │         │ id (PK)      │         │ id (PK)    │            │
│  │ email      │         │ user_id (FK) │         │ app_id (FK)│            │
│  │ google_id  │         │ company      │         │ type       │            │
│  │ name       │         │ role         │         │ data (JSON)│            │
│  │ avatar_url │         │ status       │         │ created_at │            │
│  │ created_at │         │ applied_date │         └────────────┘            │
│  └────────────┘         │ priority     │                                   │
│        │                │ source       │         ┌────────────┐            │
│        │                │ salary       │         │   notes    │            │
│        │                │ url          │─────────│            │            │
│        │                │ location     │   1:N   │ id (PK)    │            │
│        │                │ metadata     │         │ app_id (FK)│            │
│        │                │ deleted_at   │         │ content    │            │
│        │                └──────┬───────┘         │ created_at │            │
│        │                       │                 └────────────┘            │
│        │                       │                                           │
│        │         ┌─────────────┴─────────────┐                             │
│        │         │       M:N (junction)       │                             │
│        │         ▼                           ▼                             │
│  ┌─────┴──────┐ ┌────────────────┐ ┌────────────────────┐                  │
│  │   tags     │ │ application_   │ │ application_       │                  │
│  │            │ │ tags           │ │ emails             │                  │
│  │ id (PK)    │ │                │ │                    │                  │
│  │ user_id(FK)│ │ app_id (FK)    │ │ app_id (FK)        │                  │
│  │ name       │ │ tag_id (FK)    │ │ email_id (FK)      │                  │
│  │ color      │ └────────────────┘ └────────────────────┘                  │
│  └────────────┘                                                            │
│        ▲                                                                   │
│        │                         ┌────────────┐                            │
│        └─────────────────────────│   emails   │                            │
│                            1:N   │            │                            │
│                                  │ id (PK)    │                            │
│                                  │ user_id(FK)│                            │
│                                  │ gmail_id   │                            │
│                                  │ subject    │                            │
│                                  │ from_addr  │                            │
│                                  │ body       │                            │
│                                  │ received_at│                            │
│                                  └────────────┘                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Schema Definitions

### users

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    google_id       VARCHAR(255) UNIQUE,
    name            VARCHAR(255),
    avatar_url      TEXT,
    
    -- Settings
    preferences     JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);
```

### applications

```sql
CREATE TABLE applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Core fields
    company_name    VARCHAR(255) NOT NULL,
    role_title      VARCHAR(255) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'applied',
    
    -- Details
    applied_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    job_url         TEXT,
    salary_min      INTEGER,
    salary_max      INTEGER,
    salary_currency VARCHAR(3) DEFAULT 'USD',
    location        VARCHAR(255),
    remote_type     VARCHAR(20), -- 'remote', 'hybrid', 'onsite'
    
    -- Tracking
    source          VARCHAR(50), -- 'linkedin', 'direct', 'referral', etc.
    referrer_name   VARCHAR(255),
    priority        SMALLINT DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    
    -- Metadata (flexible)
    metadata        JSONB DEFAULT '{}',
    
    -- Soft delete
    deleted_at      TIMESTAMPTZ,
    
    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_status ON applications(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_applications_applied_date ON applications(applied_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_applications_company ON applications(company_name) WHERE deleted_at IS NULL;

-- Full-text search
CREATE INDEX idx_applications_search ON applications 
    USING gin(to_tsvector('english', company_name || ' ' || role_title));
```

### Status Enum Values

```sql
-- Valid status values (enforced at application level)
-- 'applied'     - Application submitted
-- 'screening'   - Recruiter screening
-- 'oa'          - Online assessment
-- 'interview'   - Interview stage(s)
-- 'offer'       - Received offer
-- 'accepted'    - Accepted offer
-- 'rejected'    - Rejected by company
-- 'withdrawn'   - Withdrawn by user
-- 'ghosted'     - No response (auto-detected)
```

### tags

```sql
CREATE TABLE tags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,
    color           VARCHAR(7) DEFAULT '#6366f1', -- Hex color
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, name)
);

CREATE INDEX idx_tags_user_id ON tags(user_id);
```

### application_tags (Junction)

```sql
CREATE TABLE application_tags (
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    tag_id          UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (application_id, tag_id)
);

CREATE INDEX idx_application_tags_tag ON application_tags(tag_id);
```

### events (Timeline)

```sql
CREATE TABLE events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    event_type      VARCHAR(50) NOT NULL,
    title           VARCHAR(255),
    description     TEXT,
    
    -- Flexible data storage
    data            JSONB DEFAULT '{}',
    
    -- Optional scheduling
    scheduled_at    TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_application ON events(application_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_scheduled ON events(scheduled_at) WHERE scheduled_at IS NOT NULL;
```

### Event Types

```sql
-- Event types
-- 'created'          - Application created
-- 'status_change'    - Status updated (data: {from, to})
-- 'interview'        - Interview scheduled (data: {round, interviewer, notes})
-- 'note_added'       - Note added
-- 'email_linked'     - Email linked to application
-- 'reminder'         - User set reminder
-- 'follow_up'        - Follow-up scheduled/sent
```

### notes

```sql
CREATE TABLE notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    content         TEXT NOT NULL,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notes_application ON notes(application_id);
```

### emails

```sql
CREATE TABLE emails (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    gmail_id        VARCHAR(255) NOT NULL,
    thread_id       VARCHAR(255),
    
    subject         TEXT,
    from_address    VARCHAR(255),
    from_name       VARCHAR(255),
    body_preview    TEXT,       -- First 500 chars
    body_html       TEXT,       -- Full HTML body (encrypted in production)
    
    received_at     TIMESTAMPTZ NOT NULL,
    
    -- Classification
    is_application_related BOOLEAN DEFAULT FALSE,
    classification  VARCHAR(50), -- 'confirmation', 'rejection', 'interview', etc.
    confidence      FLOAT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, gmail_id)
);

CREATE INDEX idx_emails_user ON emails(user_id);
CREATE INDEX idx_emails_received ON emails(received_at);
CREATE INDEX idx_emails_classification ON emails(classification) WHERE is_application_related = TRUE;
```

### application_emails (Junction)

```sql
CREATE TABLE application_emails (
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    email_id        UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    linked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    linked_by       VARCHAR(20) DEFAULT 'auto', -- 'auto' or 'manual'
    
    PRIMARY KEY (application_id, email_id)
);
```

---

## 🔄 Migrations

### Migration Naming Convention

```
YYYYMMDD_HHMMSS_description.py

Examples:
20260125_100000_create_users_table.py
20260125_100100_create_applications_table.py
20260125_100200_create_tags_and_events.py
```

### Initial Migration

```python
# alembic/versions/20260125_100000_initial_schema.py
"""Initial schema: users, applications, tags, events, notes"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260125_100000'
down_revision = None

def upgrade():
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('google_id', sa.String(255), unique=True),
        sa.Column('name', sa.String(255)),
        sa.Column('avatar_url', sa.Text),
        sa.Column('preferences', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
    )
    
    # Applications table
    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('role_title', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='applied'),
        sa.Column('applied_date', sa.Date, server_default=sa.text('CURRENT_DATE')),
        sa.Column('job_url', sa.Text),
        sa.Column('salary_min', sa.Integer),
        sa.Column('salary_max', sa.Integer),
        sa.Column('salary_currency', sa.String(3), server_default='USD'),
        sa.Column('location', sa.String(255)),
        sa.Column('remote_type', sa.String(20)),
        sa.Column('source', sa.String(50)),
        sa.Column('referrer_name', sa.String(255)),
        sa.Column('priority', sa.SmallInteger, server_default='5'),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('status_updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.CheckConstraint('priority BETWEEN 1 AND 10', name='ck_priority_range'),
    )
    
    # Continue with other tables...

def downgrade():
    op.drop_table('application_emails')
    op.drop_table('application_tags')
    op.drop_table('events')
    op.drop_table('notes')
    op.drop_table('emails')
    op.drop_table('tags')
    op.drop_table('applications')
    op.drop_table('users')
```

---

## 🔍 Query Patterns

### List Applications (with filters)

```sql
SELECT 
    a.id,
    a.company_name,
    a.role_title,
    a.status,
    a.applied_date,
    a.priority,
    array_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) as tags,
    COUNT(e.id) FILTER (WHERE e.event_type = 'interview') as interview_count
FROM applications a
LEFT JOIN application_tags at ON a.id = at.application_id
LEFT JOIN tags t ON at.tag_id = t.id
LEFT JOIN events e ON a.id = e.application_id
WHERE 
    a.user_id = :user_id
    AND a.deleted_at IS NULL
    AND (:status IS NULL OR a.status = ANY(:status))
    AND (:search IS NULL OR 
         to_tsvector('english', a.company_name || ' ' || a.role_title) 
         @@ plainto_tsquery('english', :search))
GROUP BY a.id
ORDER BY a.applied_date DESC
LIMIT :limit OFFSET :offset;
```

### Analytics: Conversion Funnel

```sql
SELECT 
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM applications
WHERE 
    user_id = :user_id
    AND deleted_at IS NULL
    AND applied_date >= :start_date
GROUP BY status
ORDER BY 
    CASE status
        WHEN 'applied' THEN 1
        WHEN 'screening' THEN 2
        WHEN 'oa' THEN 3
        WHEN 'interview' THEN 4
        WHEN 'offer' THEN 5
        WHEN 'accepted' THEN 6
        ELSE 99
    END;
```

### Analytics: Response Rate by Source

```sql
SELECT 
    source,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status NOT IN ('applied', 'ghosted')) as responded,
    ROUND(
        COUNT(*) FILTER (WHERE status NOT IN ('applied', 'ghosted')) * 100.0 / COUNT(*),
        2
    ) as response_rate
FROM applications
WHERE 
    user_id = :user_id
    AND deleted_at IS NULL
    AND source IS NOT NULL
GROUP BY source
ORDER BY response_rate DESC;
```

### Dashboard: Quick Stats

```sql
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status IN ('applied', 'screening', 'oa', 'interview')) as active,
    COUNT(*) FILTER (WHERE status IN ('interview')) as interviews,
    COUNT(*) FILTER (WHERE status IN ('offer', 'accepted')) as offers,
    COUNT(*) FILTER (WHERE applied_date >= CURRENT_DATE - INTERVAL '7 days') as this_week
FROM applications
WHERE 
    user_id = :user_id
    AND deleted_at IS NULL;
```

---

## ⚡ Performance Optimization

### Indexing Strategy

| Index Type | Use Case |
|------------|----------|
| **B-tree** | Equality, range queries (default) |
| **GIN** | Full-text search, JSONB containment |
| **Partial** | Frequently filtered subsets |

### Query Optimization Tips

1. **Use partial indexes for active records:**
   ```sql
   CREATE INDEX idx_active_apps ON applications(user_id, status) 
   WHERE deleted_at IS NULL;
   ```

2. **Avoid N+1 with eager loading:**
   ```python
   # Bad: N+1 queries
   apps = db.query(Application).filter_by(user_id=user_id).all()
   for app in apps:
       print(app.tags)  # Each triggers a query
   
   # Good: Eager load
   apps = db.query(Application)\
       .options(selectinload(Application.tags))\
       .filter_by(user_id=user_id)\
       .all()
   ```

3. **Use connection pooling:**
   ```python
   engine = create_async_engine(
       DATABASE_URL,
       pool_size=5,
       max_overflow=10,
       pool_recycle=3600
   )
   ```

---

## 🔒 Data Integrity

### Constraints

| Type | Purpose |
|------|---------|
| **Foreign Keys** | Referential integrity |
| **UNIQUE** | Prevent duplicates |
| **CHECK** | Domain validation |
| **NOT NULL** | Required fields |

### Soft Deletes

All user-facing tables use soft deletes:

```python
# Repository pattern
async def delete(self, id: UUID) -> None:
    await self.db.execute(
        update(Application)
        .where(Application.id == id)
        .values(deleted_at=datetime.now())
    )
```

### Audit Trail

All status changes logged to `events` table:

```python
# Service pattern
async def update_status(self, app_id: UUID, new_status: str):
    old_status = app.status
    app.status = new_status
    
    # Log the change
    event = Event(
        application_id=app_id,
        event_type='status_change',
        data={'from': old_status, 'to': new_status}
    )
    self.db.add(event)
```

---

## 💾 Backup Strategy

### Development
- Local PostgreSQL: Manual dumps
- Docker volume persistence

### Production (Supabase)
- Daily automated backups (included)
- Point-in-time recovery (7 days)

### Manual Backup

```bash
# Export
pg_dump -h localhost -U orbit -d orbit -F c -f backup.dump

# Import
pg_restore -h localhost -U orbit -d orbit -c backup.dump
```

---

## 🗓️ Milestones

### Week 1: Schema Design
- [ ] Finalize ER diagram
- [ ] Create all table definitions
- [ ] Set up Alembic migrations
- [ ] Seed development data

### Week 2: Repository Layer
- [ ] Base repository pattern
- [ ] User repository
- [ ] Application repository
- [ ] Pagination helpers

### Week 3: Complex Queries
- [ ] Analytics queries
- [ ] Full-text search
- [ ] Filter builder

### Week 4: Optimization
- [ ] Index audit
- [ ] Query performance testing
- [ ] Connection pooling tuned

---

## 📋 Definition of Done

Before marking schema complete:

- [ ] All tables have timestamps (created_at, updated_at)
- [ ] All foreign keys have ON DELETE behavior defined
- [ ] Indexes exist for all common query patterns
- [ ] Soft deletes implemented where needed
- [ ] Migration is reversible (up and down)
- [ ] Seed data script works
- [ ] No orphan records possible

---

*Database Lead — Orbit v1.0*
