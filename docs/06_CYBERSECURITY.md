# Cybersecurity Engineer — Orbit

> **Owner:** Security Lead  
> **Scope:** Authentication, authorization, data protection, vulnerability prevention, compliance

---

## 🎯 Mission

Make Orbit **secure by default**. Users trust us with sensitive job application data and email access. We must protect this data at rest, in transit, and ensure only authorized access.

---

## 🛡️ Security Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY ARCHITECTURE                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         PERIMETER SECURITY                               │ │
│  │  • Cloudflare DDoS protection                                           │ │
│  │  • WAF rules (SQL injection, XSS)                                       │ │
│  │  • Rate limiting at edge                                                │ │
│  │  • SSL/TLS termination                                                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                         │
│                                     ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                       APPLICATION SECURITY                               │ │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │ │
│  │  │ Authentication│  │ Authorization │  │ Input Valid.  │              │ │
│  │  │ (OAuth + JWT) │  │ (RBAC/ABAC)   │  │ (Zod/Pydantic)│              │ │
│  │  └───────────────┘  └───────────────┘  └───────────────┘              │ │
│  │                                                                          │ │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │ │
│  │  │  Rate Limit   │  │   CORS        │  │   CSP         │              │ │
│  │  │  (per user)   │  │  (whitelist)  │  │  (headers)    │              │ │
│  │  └───────────────┘  └───────────────┘  └───────────────┘              │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                         │
│                                     ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                          DATA SECURITY                                   │ │
│  │  • Encryption at rest (AES-256)                                         │ │
│  │  • Encryption in transit (TLS 1.3)                                      │ │
│  │  • PII minimization                                                     │ │
│  │  • Secure credential storage                                            │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Authentication System

### OAuth 2.0 + JWT Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. User clicks "Login with Google"                                        │
│     │                                                                        │
│     ▼                                                                        │
│  2. Frontend redirects to: /auth/login                                      │
│     │                                                                        │
│     ▼                                                                        │
│  3. Backend redirects to Google OAuth consent screen                        │
│     │                                                                        │
│     ▼                                                                        │
│  4. User grants permission                                                  │
│     │                                                                        │
│     ▼                                                                        │
│  5. Google redirects to: /auth/callback?code=xxx                           │
│     │                                                                        │
│     ▼                                                                        │
│  6. Backend exchanges code for tokens                                       │
│     │                                                                        │
│     ├──▶ Access Token stored in memory (frontend)                          │
│     │    • 15 minute expiry                                                 │
│     │    • Used in Authorization header                                     │
│     │                                                                        │
│     └──▶ Refresh Token stored in HttpOnly cookie                           │
│          • 7 day expiry                                                     │
│          • Secure, SameSite=Strict                                          │
│          • Never accessible to JavaScript                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Token Security Rules

| Token Type | Storage | Lifetime | Accessible to JS |
|------------|---------|----------|------------------|
| **Access Token** | Memory (React state/store) | 15 minutes | Yes (needed for API calls) |
| **Refresh Token** | HttpOnly Cookie | 7 days | No (security) |
| **CSRF Token** | Meta tag | Session | Yes |

### JWT Implementation

```python
# backend/app/utils/jwt.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict) -> str:
    """Create short-lived access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """Create long-lived refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode token."""
    try:
        secret = settings.SECRET_KEY if token_type == "access" else settings.REFRESH_SECRET_KEY
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        
        if payload.get("type") != token_type:
            raise JWTError("Invalid token type")
        
        return payload
    except JWTError:
        return None
```

### OAuth Callback

```python
# backend/app/routers/auth.py
from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/callback")
async def oauth_callback(
    code: str,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback from Google."""
    
    # Exchange code for Google tokens
    google_tokens = await exchange_code_for_tokens(code)
    
    # Get user info from Google
    user_info = await get_google_user_info(google_tokens["access_token"])
    
    # Find or create user
    user = await find_or_create_user(db, user_info)
    
    # Generate our tokens
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Set refresh token as HttpOnly cookie
    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/success")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # HTTPS only
        samesite="strict",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/auth"  # Only sent to auth endpoints
    )
    
    # Access token in URL fragment (not query param, more secure)
    response.headers["Location"] = f"{settings.FRONTEND_URL}/auth/success#token={access_token}"
    
    return response
```

---

## 🚧 Authorization (RBAC)

### Route Protection Middleware

```python
# backend/app/middleware/auth.py
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(request: Request) -> User:
    """Extract and verify user from request."""
    
    # Get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    
    # Verify token
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get user from database
    user = await get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# Usage in routes
@router.get("/applications")
async def list_applications(
    current_user: User = Depends(get_current_user)
):
    # Only returns applications for the authenticated user
    return await application_service.list_by_user(current_user.id)
```

### Resource Ownership Checks

```python
# backend/app/services/application_service.py

async def get_application(
    user_id: UUID, 
    application_id: UUID
) -> Application:
    """Get application with ownership check."""
    
    application = await repo.get_by_id(application_id)
    
    if not application:
        raise NotFoundError("Application not found")
    
    # CRITICAL: Verify ownership
    if application.user_id != user_id:
        raise ForbiddenError("Access denied")
    
    return application
```

---

## 🧹 Input Validation

### Backend Validation (Pydantic)

```python
# backend/app/schemas/application.py
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional
import bleach

class ApplicationCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    role_title: str = Field(..., min_length=1, max_length=255)
    job_url: Optional[HttpUrl] = None
    salary_min: Optional[int] = Field(None, ge=0, le=10_000_000)
    salary_max: Optional[int] = Field(None, ge=0, le=10_000_000)
    notes: Optional[str] = Field(None, max_length=5000)
    
    @validator('company_name', 'role_title', 'notes', pre=True)
    def sanitize_strings(cls, v):
        if v is None:
            return v
        # Strip HTML tags
        return bleach.clean(v.strip(), tags=[], strip=True)
    
    @validator('salary_max')
    def validate_salary_range(cls, v, values):
        if v and values.get('salary_min') and v < values['salary_min']:
            raise ValueError('salary_max must be >= salary_min')
        return v
```

### Frontend Validation (Zod)

```typescript
// frontend/src/schemas/application.ts
import { z } from 'zod';

export const applicationSchema = z.object({
  companyName: z.string()
    .min(1, 'Company name is required')
    .max(255)
    .transform(v => v.trim()),
  
  roleTitle: z.string()
    .min(1, 'Role is required')
    .max(255)
    .transform(v => v.trim()),
  
  jobUrl: z.string()
    .url('Invalid URL')
    .optional()
    .or(z.literal('')),
  
  salaryMin: z.number()
    .min(0)
    .max(10_000_000)
    .optional(),
  
  salaryMax: z.number()
    .min(0)
    .max(10_000_000)
    .optional(),
  
  notes: z.string()
    .max(5000)
    .optional(),
}).refine(
  data => !data.salaryMax || !data.salaryMin || data.salaryMax >= data.salaryMin,
  { message: 'Max salary must be >= min salary', path: ['salaryMax'] }
);
```

---

## 🔒 Data Protection

### Encryption at Rest

```python
# backend/app/utils/encryption.py
from cryptography.fernet import Fernet
import base64
import os

class EncryptionService:
    def __init__(self):
        key = settings.ENCRYPTION_KEY
        if not key:
            raise ValueError("ENCRYPTION_KEY not set")
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher.decrypt(ciphertext.encode()).decode()

encryption = EncryptionService()

# Usage: Store encrypted email bodies
async def store_email(email_data: dict):
    encrypted_body = encryption.encrypt(email_data['body_html'])
    await repo.create(
        ...
        body_html=encrypted_body,  # Stored encrypted
        ...
    )
```

### Sensitive Fields to Encrypt

| Table | Field | Reason |
|-------|-------|--------|
| `emails` | `body_html` | Contains email content |
| `users` | `gmail_refresh_token` | OAuth credential |
| `applications` | `notes` (optional) | May contain salary info |

### PII Handling

```python
# Never log PII
logger.info(f"User {user.id} logged in")  # Good: ID only
logger.info(f"User {user.email} logged in")  # Bad: PII

# Mask in error messages
def mask_email(email: str) -> str:
    """Mask email for logging."""
    parts = email.split('@')
    if len(parts) == 2:
        username = parts[0][:2] + '***'
        return f"{username}@{parts[1]}"
    return '***'
```

---

## 🛡️ HTTP Security Headers

### Backend Headers (FastAPI)

```python
# backend/app/middleware/security.py
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS (enable after confirming HTTPS works)
        if settings.ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### Content Security Policy (Frontend)

```html
<!-- frontend/index.html -->
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data: https: blob:;
  connect-src 'self' http://localhost:8000 https://api.orbitapp.io https://accounts.google.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
">
```

---

## ⚡ Rate Limiting

### Per-User Rate Limits

```python
# backend/app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to app
app.state.limiter = limiter

# Rate limit decorators
@router.post("/applications")
@limiter.limit("30/minute")  # 30 requests per minute
async def create_application(...):
    ...

@router.get("/applications")
@limiter.limit("60/minute")  # 60 requests per minute
async def list_applications(...):
    ...

@router.post("/auth/login")
@limiter.limit("10/minute")  # Strict on auth endpoints
async def login(...):
    ...
```

### Rate Limit Response

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Please try again in 60 seconds.",
    "retry_after": 60
  }
}
```

---

## 🛡️ CORS Configuration

```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "http://localhost:3000",      # Local dev
    "http://localhost:5173",      # Vite dev
    "https://orbitapp.io",        # Production
    "https://www.orbitapp.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if settings.ENV != "development" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-Id"],
    max_age=600,  # Cache preflight for 10 minutes
)
```

---

## 📧 Gmail OAuth Security

### Minimal Scopes

```python
# Only request what we need
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",  # Read-only access
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
```

### Token Storage

```python
# Store encrypted refresh tokens
async def store_gmail_tokens(user_id: UUID, tokens: dict):
    encrypted_refresh = encryption.encrypt(tokens['refresh_token'])
    
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(gmail_refresh_token=encrypted_refresh)
    )
```

### Access Token Rotation

```python
# Always use fresh access tokens
async def get_gmail_access_token(user: User) -> str:
    """Get fresh Gmail access token using refresh token."""
    
    encrypted_refresh = user.gmail_refresh_token
    if not encrypted_refresh:
        raise AuthError("Gmail not connected")
    
    refresh_token = encryption.decrypt(encrypted_refresh)
    
    # Exchange refresh token for access token
    response = await oauth_client.refresh_token(refresh_token)
    
    return response['access_token']
```

---

## 🔍 Security Logging & Monitoring

### Audit Log Events

```python
# backend/app/utils/audit.py
import logging
from datetime import datetime

audit_logger = logging.getLogger('audit')

def log_security_event(
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    details: dict = None
):
    """Log security-relevant events."""
    
    audit_logger.info({
        "event": event_type,
        "user_id": user_id,
        "ip": ip_address,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details
    })

# Events to log
# - login_success
# - login_failed
# - logout
# - token_refresh
# - password_reset
# - data_export
# - account_deleted
# - suspicious_activity
```

### Security Alerts

| Event | Action |
|-------|--------|
| 5 failed logins | Lock account temporarily |
| Token from new IP | Email notification |
| Data export request | Email confirmation |
| Account deletion | 24h grace period |

---

## 📋 Security Checklist

### Authentication
- [ ] OAuth 2.0 with PKCE
- [ ] JWT stored in memory only
- [ ] Refresh tokens in HttpOnly cookies
- [ ] Token rotation on refresh
- [ ] Secure logout clears all tokens

### Authorization
- [ ] All routes protected by default
- [ ] Resource ownership verified
- [ ] No horizontal privilege escalation
- [ ] No vertical privilege escalation

### Input Security
- [ ] All inputs validated
- [ ] SQL injection prevented (ORM)
- [ ] XSS prevented (sanitization)
- [ ] CSRF tokens required

### Data Protection
- [ ] TLS 1.3 in transit
- [ ] AES-256 at rest (sensitive fields)
- [ ] PII minimization
- [ ] Secure credential storage

### Infrastructure
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Security headers set
- [ ] DDoS protection (Cloudflare)

### Monitoring
- [ ] Security events logged
- [ ] Alerts configured
- [ ] Regular security scans

---

## 🗓️ Milestones

### Week 1: Auth Foundation
- [ ] Google OAuth implementation
- [ ] JWT creation/validation
- [ ] Token refresh flow
- [ ] Secure cookie handling

### Week 2: Authorization
- [ ] Route protection middleware
- [ ] Resource ownership checks
- [ ] Input validation setup
- [ ] CORS configuration

### Week 3: Data Protection
- [ ] Encryption service
- [ ] Sensitive field encryption
- [ ] Security headers
- [ ] Rate limiting

### Week 4: Hardening
- [ ] Security audit
- [ ] Penetration testing (basic)
- [ ] Logging/monitoring
- [ ] Documentation

---

## 📋 Definition of Done

Before marking any security feature complete:

- [ ] No secrets in code/logs
- [ ] Input validation on all user data
- [ ] Auth check on all protected routes
- [ ] Encryption for sensitive data
- [ ] Rate limiting applied
- [ ] Security headers set
- [ ] Audit logging implemented
- [ ] Tested for OWASP Top 10

---

*Cybersecurity Engineer — Orbit v1.0*
