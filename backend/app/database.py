"""
Database connection and session management
Uses SQLAlchemy 2.0 async engine
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()


def _build_engine_args(database_url: str):
    """
    asyncpg does not support libpq-only query parameters like 'sslmode',
    'channel_binding', 'connect_timeout', etc. Strip them all and translate
    ssl requirements into connect_args instead.
    """
    # These are libpq/psycopg2 params that asyncpg does NOT accept
    LIBPQ_ONLY_PARAMS = {
        "sslmode", "channel_binding", "connect_timeout",
        "application_name", "options", "gssencmode",
    }

    parsed = urlparse(database_url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    ssl_required = params.get("sslmode", ["disable"])[0] in (
        "require", "verify-ca", "verify-full", "prefer"
    )

    # Remove all unsupported params
    for key in LIBPQ_ONLY_PARAMS:
        params.pop(key, None)

    # Rebuild URL without the stripped params
    clean_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))

    connect_args = {"ssl": True} if ssl_required else {}
    return clean_url, connect_args


_db_url, _connect_args = _build_engine_args(settings.database_url)

# Create async engine
engine = create_async_engine(
    _db_url,
    echo=settings.database_echo,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True,  # Health check connections before use
    connect_args=_connect_args,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Automatically commits on success, rollbacks on error.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager version for use outside of FastAPI dependencies"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables (for development)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()
