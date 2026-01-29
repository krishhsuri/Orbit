"""
Routers Package
Export all API routers
"""

from app.routers import health, applications, tags, analytics, auth

__all__ = ["health", "applications", "tags", "analytics", "auth"]
