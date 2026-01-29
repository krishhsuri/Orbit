# Backend Lead Engineer — Orbit

> **Owner:** Backend Lead  
> **Scope:** API design, business logic, services, data access layer

---

## 🎯 Mission

Build a **robust, scalable** backend for Orbit. The API should be fast, well-documented, and follow REST best practices. Focus on clean architecture that's easy to test and extend.

---

## 📐 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        BACKEND ARCHITECTURE                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐                                                 │
│  │   FastAPI   │ ◀── HTTP Requests from Frontend                 │
│  │   (main.py) │                                                 │
│  └──────┬──────┘                                                 │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │  Middleware │───▶│   Routers   │───▶│  Services   │          │
│  │  (Auth,CORS)│    │  (Endpoints)│    │  (Business) │          │
│  └─────────────┘    └─────────────┘    └──────┬──────┘          │
│                                               │                  │
│                                               ▼                  │
│                     ┌─────────────────────────────────┐          │
│                     │         Repository Layer         │          │
│                     │    (Data Access Abstraction)     │          │
│                     └──────────────┬──────────────────┘          │
│                                    │                             │
│         ┌──────────────────────────┼──────────────────────────┐  │
│         ▼                          ▼                          ▼  │
│  ┌─────────────┐           ┌─────────────┐           ┌────────┐ │
│  │ PostgreSQL  │           │    Redis    │           │ Gmail  │ │
│  │ (Primary DB)│           │   (Cache)   │           │  API   │ │
│  └─────────────┘           └─────────────┘           └────────┘ │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Framework** | FastAPI | Async, auto-docs, type hints |
| **ORM** | SQLAlchemy 2.0 | Async support, mature |
| **Migrations** | Alembic | Standard for SQLAlchemy |
| **Validation** | Pydantic v2 | FastAPI native, fast |
| **Auth** | PyJWT + OAuth2 | Industry standard |
| **Database** | PostgreSQL 15 | Reliable, JSONB support |
| **Cache** | Redis | Sessions, rate limiting |
| **Task Queue** | Celery (optional) | Background jobs |
| **Testing** | Pytest + httpx | Async test client |

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Settings (pydantic-settings)
│   ├── database.py              # DB connection, session
│   │
│   ├── models/                  # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py              # Base model class
│   │   ├── user.py
│   │   ├── application.py
│   │   ├── tag.py
│   │   ├── event.py
│   │   └── email.py
│   │
│   ├── schemas/                 # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── application.py
│   │   ├── analytics.py
│   │   └── common.py            # Pagination, errors
│   │
│   ├── routers/                 # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py              # /auth/*
│   │   ├── applications.py      # /api/applications/*
│   │   ├── tags.py              # /api/tags/*
│   │   ├── analytics.py         # /api/analytics/*
│   │   ├── emails.py            # /api/emails/*
│   │   └── health.py            # /health
│   │
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── application_service.py
│   │   ├── analytics_service.py
│   │   ├── email_service.py
│   │   └── gmail_service.py
│   │
│   ├── repositories/            # Data access
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user_repo.py
│   │   ├── application_repo.py
│   │   └── email_repo.py
│   │
│   ├── middleware/              # Request middleware
│   │   ├── __init__.py
│   │   ├── auth.py              # JWT validation
│   │   ├── rate_limit.py
│   │   └── logging.py
│   │
│   ├── utils/                   # Utilities
│   │   ├── __init__.py
│   │   ├── encryption.py
│   │   ├── jwt.py
│   │   └── exceptions.py
│   │
│   └── tasks/                   # Background tasks (Celery)
│       ├── __init__.py
│       └── email_sync.py
│
├── alembic/                     # Migrations
│   ├── versions/
│   └── env.py
│
├── tests/
│   ├── conftest.py              # Fixtures
│   ├── test_auth.py
│   ├── test_applications.py
│   └── test_analytics.py
│
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## 🔌 API Design

### Base URL
- Development: `http://localhost:8000`
- Production: `https://api.orbitapp.io`

### Versioning
All API routes prefixed with `/api/v1/`

### Authentication
- OAuth2 with Google
- JWT access tokens (15 min expiry)
- Refresh tokens (7 days, HttpOnly cookie)

---

## 📋 API Endpoints

### Auth Routes (`/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/login` | Initiate Google OAuth |
| GET | `/auth/callback` | OAuth callback |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout (clear tokens) |
| GET | `/auth/me` | Get current user |

### Application Routes (`/api/v1/applications`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/applications` | List all (paginated, filtered) |
| POST | `/applications` | Create new application |
| GET | `/applications/:id` | Get single application |
| PATCH | `/applications/:id` | Update application |
| DELETE | `/applications/:id` | Soft delete application |
| GET | `/applications/:id/events` | Get timeline events |
| POST | `/applications/:id/events` | Add event |

#### Query Parameters for List
```
GET /api/v1/applications?
  page=1&
  limit=20&
  status=applied,interview&
  tags=faang,remote&
  search=google&
  sort=-applied_date
```

### Tag Routes (`/api/v1/tags`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tags` | List user's tags |
| POST | `/tags` | Create tag |
| PATCH | `/tags/:id` | Update tag |
| DELETE | `/tags/:id` | Delete tag |

### Analytics Routes (`/api/v1/analytics`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/summary` | Quick stats |
| GET | `/analytics/funnel` | Conversion funnel |
| GET | `/analytics/trends` | Time-series data |
| GET | `/analytics/insights` | AI-generated insights |

### Email Routes (`/api/v1/emails`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/emails` | List synced emails |
| POST | `/emails/sync` | Trigger Gmail sync |
| GET | `/emails/:id` | Get email detail |
| POST | `/emails/:id/link` | Link to application |

---

## 📊 Response Formats

### Success Response
```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 87
  }
}
```

### Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": {
      "company_name": ["This field is required"]
    }
  }
}
```

### Standard Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Invalid request body |
| `NOT_FOUND` | 404 | Resource not found |
| `UNAUTHORIZED` | 401 | Missing/invalid token |
| `FORBIDDEN` | 403 | No permission |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## 🔒 Authentication Flow

### OAuth2 + JWT Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Browser │────▶│ Backend │────▶│ Google  │────▶│  Token  │
│         │     │ /login  │     │ OAuth   │     │ Exchange│
└─────────┘     └─────────┘     └─────────┘     └────┬────┘
                                                     │
     ┌───────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ Backend generates:                                            │
│ • Access Token (JWT, 15 min, returned in response body)      │
│ • Refresh Token (7 days, stored in HttpOnly cookie)          │
└──────────────────────────────────────────────────────────────┘
```

### JWT Payload
```json
{
  "sub": "user_uuid",
  "email": "user@example.com",
  "exp": 1706198400,
  "iat": 1706197500
}
```

---

## 🏗️ Service Layer Patterns

### Application Service Example

```python
# services/application_service.py
class ApplicationService:
    def __init__(self, repo: ApplicationRepository):
        self.repo = repo
    
    async def create_application(
        self, 
        user_id: UUID, 
        data: ApplicationCreate
    ) -> Application:
        # Business validation
        if data.applied_date > datetime.now():
            raise ValidationError("Applied date cannot be in future")
        
        # Create application
        application = await self.repo.create(
            user_id=user_id,
            **data.model_dump()
        )
        
        # Create initial event
        await self.repo.create_event(
            application_id=application.id,
            event_type="created",
            data={"status": "applied"}
        )
        
        return application
    
    async def update_status(
        self,
        user_id: UUID,
        app_id: UUID,
        new_status: str
    ) -> Application:
        application = await self.repo.get_by_id(app_id)
        
        if application.user_id != user_id:
            raise ForbiddenError("Not your application")
        
        old_status = application.status
        application = await self.repo.update(
            app_id, 
            status=new_status,
            status_updated_at=datetime.now()
        )
        
        # Log status change event
        await self.repo.create_event(
            application_id=app_id,
            event_type="status_change",
            data={"from": old_status, "to": new_status}
        )
        
        return application
```

---

## 🧪 Testing Strategy

### Test Structure
```
tests/
├── unit/
│   ├── test_services.py
│   └── test_utils.py
├── integration/
│   ├── test_auth_flow.py
│   └── test_applications.py
└── conftest.py
```

### Test Database
- Use PostgreSQL test database (not SQLite)
- Fixtures create/teardown test data
- Use transactions for isolation

### Coverage Target
- **Unit tests:** 90% coverage on services
- **Integration tests:** All API endpoints
- **Critical paths:** Auth, CRUD, analytics

---

## 📅 Milestones

### Week 1: Foundation
- [ ] FastAPI project setup
- [ ] Database models (User, Application, Tag, Event)
- [ ] Alembic migrations
- [ ] Health check endpoint
- [ ] Docker setup

### Week 2: Auth + CRUD
- [ ] Google OAuth integration
- [ ] JWT middleware
- [ ] Applications CRUD endpoints
- [ ] Tags endpoints
- [ ] Pagination helpers

### Week 3: Features
- [ ] Analytics endpoints
- [ ] Event timeline
- [ ] Search & filters
- [ ] Rate limiting

### Week 4: Polish
- [ ] Error handling standardization
- [ ] API documentation (OpenAPI)
- [ ] Integration tests
- [ ] Performance optimization

---

## 📋 Definition of Done

Before marking any endpoint complete:

- [ ] Endpoint documented in OpenAPI
- [ ] Input validation with Pydantic
- [ ] Proper error handling
- [ ] Auth required (unless public)
- [ ] Rate limiting applied
- [ ] Unit tests written
- [ ] Integration test written
- [ ] No N+1 query issues

---

*Backend Lead Engineer — Orbit v1.0*
