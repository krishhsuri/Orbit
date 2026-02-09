"""Request Timeout Middleware"""
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request timeout limits."""
    
    def __init__(self, app, timeout_seconds: int = 30):
        super().__init__(app)
        self.timeout = timeout_seconds

    async def dispatch(self, request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request), 
                timeout=float(self.timeout)
            )
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {request.url.path}")
            return JSONResponse(
                {"error": "Request timeout", "detail": "The request took too long to process"}, 
                status_code=504
            )
