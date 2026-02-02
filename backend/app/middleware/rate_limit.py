"""
Rate Limiting Middleware
Request rate limiting using slowapi with Redis backend support.
"""

import logging
from typing import Callable, Optional

from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting.
    Uses user ID if authenticated, otherwise falls back to IP address.
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance
# In production, use Redis: Limiter(key_func=get_user_identifier, storage_uri="redis://localhost:6379")
limiter = Limiter(key_func=get_user_identifier)


# Rate limit decorators for different endpoint types
def rate_limit_auth(limit: str = "5/minute"):
    """Rate limit for auth endpoints (login, register)."""
    return limiter.limit(limit)


def rate_limit_api(limit: str = "60/minute"):
    """Rate limit for general API endpoints."""
    return limiter.limit(limit)


def rate_limit_heavy(limit: str = "10/minute"):
    """Rate limit for heavy operations (file uploads, exports)."""
    return limiter.limit(limit)


def setup_rate_limiting(app):
    """Configure rate limiting for the FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info("Rate limiting configured")


# Common rate limits
RATE_LIMITS = {
    "auth": "5/minute",       # Login, register
    "api": "60/minute",       # General API calls
    "search": "30/minute",    # Search operations
    "sync": "5/minute",       # Email sync
    "export": "10/minute",    # Data exports
    "ai": "20/minute",        # AI operations
}
