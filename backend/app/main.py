"""
Orbit Backend - FastAPI Application
Main entry point for the API
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db
from app.routers import health, applications, tags, analytics, auth, gmail

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan context manager for startup/shutdown events
    """
    # Startup
    if settings.debug:
        await init_db()  # Create tables in dev
    
    yield
    
    # Shutdown
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Orbit API",
    description="Job Application Tracker API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)
app.include_router(
    applications.router,
    prefix="/api/v1/applications",
    tags=["Applications"],
)
app.include_router(
    tags.router,
    prefix="/api/v1/tags",
    tags=["Tags"],
)
app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["Analytics"],
)
app.include_router(
    gmail.router,
    prefix="/api/v1/gmail",
    tags=["Gmail Integration"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Orbit API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else None,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
