"""
Authentication Router
OAuth2 with Google, JWT tokens, login/logout
"""

from datetime import datetime
from typing import Optional
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Response, status, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import get_settings
from app.database import get_db
from app.utils.encryption import TokenEncryption
from app.models import User
from app.utils.jwt import create_token_pair, decode_token, create_access_token
from app.middleware.auth import get_current_user

settings = get_settings()
router = APIRouter()


# Response schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login")
async def login():
    """
    Initiate Google OAuth login.
    Redirects to Google's consent screen.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    
    # helper for scope string
    scope_str = " ".join(settings.google_scopes) or "openid email profile"

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": scope_str,
        "access_type": "offline",
        "prompt": "consent",
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Google OAuth callback.
    Exchanges code for tokens and creates/updates user.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}",
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for tokens",
            )
        
        tokens = token_response.json()
        google_access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")  # Capture refresh token
        
        # Get user info from Google
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google",
            )
        
        google_user = userinfo_response.json()
    
    # Find or create user
    email = google_user.get("email")
    google_id = google_user.get("id")
    name = google_user.get("name")
    avatar_url = google_user.get("picture")
    
    result = await db.execute(
        select(User).where(User.google_id == google_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Check if email exists (user signed up differently)
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Link Google account
            user.google_id = google_id
            user.avatar_url = avatar_url or user.avatar_url
        else:
            # Create new user
            user = User(
                email=email,
                google_id=google_id,
                name=name,
                avatar_url=avatar_url,
            )
            db.add(user)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    if name and not user.name:
        user.name = name
        
    # Handle Gmail Refresh Token
    if refresh_token:
        try:
            encryptor = TokenEncryption(settings.encryption_key)
            encrypted_token = encryptor.encrypt_token(refresh_token)
            user.gmail_refresh_token_encrypted = encrypted_token
            user.gmail_sync_enabled = True
            logger.info(f"Saved Gmail refresh token for user {user.email}")
        except Exception as e:
            # Don't fail login if encryption fails, but log it
            logger.error(f"Failed to encrypt refresh token: {e}")
            
    await db.commit()
    await db.refresh(user)
    
    # Auto-trigger email sync on login if Gmail is enabled
    if user.gmail_sync_enabled and background_tasks:
        from app.routers.gmail import sync_emails_task
        background_tasks.add_task(sync_emails_task, user.id, None)
        logger.info(f"Auto-triggered email sync for user {user.email}")
    
    # Create JWT tokens
    token_pair = create_token_pair(user.id, user.email)
    
    # Redirect to frontend with token
    frontend_url = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    redirect_url = f"{frontend_url}/auth/callback?access_token={token_pair.access_token}"
    
    response = RedirectResponse(url=redirect_url)
    
    # Set refresh token as HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=token_pair.refresh_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )
    
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    response: Response,
    refresh_token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    Refresh token can be in cookie or request body.
    """
    # TODO: Get from cookie if not in body
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    from uuid import UUID
    try:
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Get user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Create new access token
    access_token = create_access_token(user.id, user.email)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Logout - clear refresh token cookie.
    """
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """
    Get current authenticated user.
    """
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
    )


@router.delete("/me")
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user account and all associated data (GDPR compliance).
    Performs soft delete by setting deleted_at timestamp.
    """
    from app.models import PendingApplication, Application
    from sqlalchemy import update
    
    # Soft delete user
    user.deleted_at = datetime.utcnow()
    
    # Mark pending applications as deleted
    await db.execute(
        update(PendingApplication)
        .where(PendingApplication.user_id == user.id)
        .values(status="deleted")
    )
    
    # Soft delete applications
    await db.execute(
        update(Application)
        .where(Application.user_id == user.id)
        .values(deleted_at=datetime.utcnow())
    )
    
    await db.commit()
    logger.info(f"Account deleted for user {user.id}")
    return {"message": "Account scheduled for deletion"}


# Development-only router (conditionally included in main.py)
dev_router = APIRouter()


class DevLoginRequest(BaseModel):
    email: str


@dev_router.post("/dev-login", response_model=AuthResponse)
async def dev_login(
    data: DevLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Development-only login endpoint.
    Logs in or creates user by email without OAuth.
    This router is only included when DEBUG=true.
    """
    # Find or create user
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            email=data.email,
            name=data.email.split("@")[0],
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create tokens
    token_pair = create_token_pair(user.id, user.email)
    
    return AuthResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
        ),
        access_token=token_pair.access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
