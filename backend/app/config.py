"""
Orbit Backend Configuration
Uses pydantic-settings for type-safe configuration management
"""

import os
from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Environment
    debug: bool = False
    environment: str = "development"
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/orbit"
    database_echo: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = Field(
        default_factory=lambda: os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/auth/callback"
        )
    )
    
    @property
    def google_scopes(self) -> List[str]:
        return [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.readonly",
        ]
        
    # AI & Encryption
    groq_api_key: str = Field(default="", description="Groq API key for LLM")
    encryption_key: str = Field(default="", description="32-byte base64 Fernet key")
    
    @field_validator('encryption_key')
    @classmethod
    def validate_encryption_key(cls, v):
        if v and len(v) < 32:
            raise ValueError("Encryption key must be at least 32 characters")
        return v

    # Monitoring
    sentry_dsn: str = ""

    # CORS
    allowed_origins: str = "http://localhost:3000"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated origins into list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()
