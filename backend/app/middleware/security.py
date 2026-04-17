"""
Security Headers Middleware
Adds security headers to all responses for protection against common attacks.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.
    
    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: XSS filter (legacy browsers)
    - Strict-Transport-Security: Forces HTTPS
    - Content-Security-Policy: Controls resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Restricts browser features
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        # HSTS - only in production with HTTPS
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = build_csp_header(settings.debug)
        
        return response


def build_csp_header(is_dev: bool = False) -> str:
    """
    Build Content-Security-Policy header.
    
    More permissive in development for hot reload and debugging.
    """
    if is_dev:
        # Development: Allow inline scripts for hot reload
        return "; ".join([
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data: https://fonts.gstatic.com",
            "connect-src 'self' ws: wss: http://localhost:* https://api.groq.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ])
    else:
        # Production: Strict CSP — allow Vercel frontend and Google OAuth
        frontend_origins = " ".join(settings.cors_origins)
        return "; ".join([
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' https://fonts.gstatic.com",
            f"connect-src 'self' {frontend_origins} https://api.groq.com https://accounts.google.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests",
        ])


def get_cors_origins(is_dev: bool = False) -> list:
    """
    Get CORS allowed origins based on environment.
    Always reads from settings.cors_origins (set via ALLOWED_ORIGINS env var).
    """
    if is_dev:
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
        ] + settings.cors_origins
    return settings.cors_origins
