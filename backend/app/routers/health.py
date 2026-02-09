"""
Health Check Router
Simple health check endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import get_settings

settings = get_settings()
router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}


@router.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Health check with database connectivity"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/health/redis")
async def health_check_redis():
    """Health check for Redis connectivity"""
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": "disconnected", "error": str(e)}


@router.get("/health/full")
async def full_health_check(db: AsyncSession = Depends(get_db)):
    """Full health check - DB + Redis"""
    health = {"status": "healthy", "services": {}}
    
    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        health["services"]["database"] = "connected"
    except Exception:
        health["status"] = "unhealthy"
        health["services"]["database"] = "disconnected"
    
    # Check Redis
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        health["services"]["redis"] = "connected"
    except Exception:
        health["status"] = "unhealthy"
        health["services"]["redis"] = "disconnected"
    
    return health
