"""
JWT Utilities
Token generation and validation for authentication
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # User ID
    email: str
    exp: datetime
    iat: datetime


class TokenPair(BaseModel):
    """Access and refresh tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


def create_access_token(user_id: UUID, email: str) -> str:
    """Create a JWT access token"""
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: UUID) -> str:
    """Create a JWT refresh token"""
    now = datetime.utcnow()
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }
    
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_token_pair(user_id: UUID, email: str) -> TokenPair:
    """Create both access and refresh tokens"""
    return TokenPair(
        access_token=create_access_token(user_id, email),
        refresh_token=create_refresh_token(user_id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


def get_token_user_id(token: str) -> Optional[UUID]:
    """Extract user ID from token"""
    payload = decode_token(token)
    if payload and "sub" in payload:
        try:
            return UUID(payload["sub"])
        except (ValueError, TypeError):
            return None
    return None
