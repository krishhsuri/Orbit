"""
Error Handler Middleware
Global exception handling with standardized error responses.
"""

import logging
import traceback
from typing import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global exception handler middleware.
    
    Catches all unhandled exceptions and returns standardized error responses.
    Logs errors with full context for debugging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
            
        except Exception as exc:
            # Log the error with full traceback
            logger.error(
                f"Unhandled exception on {request.method} {request.url.path}",
                exc_info=exc,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )
            
            # Return standardized error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred. Please try again later.",
                        "details": str(exc) if logger.level <= logging.DEBUG else None,
                    }
                }
            )


def register_exception_handlers(app):
    """Register FastAPI exception handlers for common exceptions."""
    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import IntegrityError
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": errors,
                }
            }
        )
    
    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        """Handle database integrity errors (duplicate keys, foreign key violations)."""
        logger.warning(f"Database integrity error: {exc}")
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "error": {
                    "code": "CONFLICT",
                    "message": "A database conflict occurred. The resource may already exist.",
                }
            }
        )
