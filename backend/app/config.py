"""
Orbit Backend Configuration
Uses pydantic-settings for type-safe configuration management
"""

import os
from functools import lru_cache
from typing import List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
    access_token_expire_minutes: int = 43200
    refresh_token_expire_days: int = 30
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = Field(
        default_factory=lambda: os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/auth/callback"
        )
    )
    
    # Demo/Test Account — set via env for local dev only; no insecure defaults
    demo_email: str = ""
    demo_password: str = ""
    
    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        insecure_jwt = self.jwt_secret_key in ("", "change-me-in-production")
        if not self.debug and insecure_jwt:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value when DEBUG=false"
            )
        if self.agent_send_enabled and not self.agent_send_test_inbox.strip():
            raise ValueError(
                "AGENT_SEND_TEST_INBOX must be set when AGENT_SEND_ENABLED=true "
                "(route all sends to a controlled inbox during development)"
            )
        return self
    
    @property
    def google_scopes(self) -> List[str]:
        return [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar.events",
        ]
        
    # AI & Encryption
    groq_api_key: str = Field(default="", description="Groq API key for LLM")
    groq_model_fast: str = Field(
        default="openai/gpt-oss-20b",
        description="Primary Groq model for classification and extraction (higher RPD than compound-mini)",
    )
    groq_model_fast_fallbacks: str = Field(
        default="openai/gpt-oss-120b,groq/compound-mini",
        description="Comma-separated fallbacks for the fast tier (tried in order after the primary)",
    )
    groq_model_reasoning: str = Field(
        default="qwen/qwen3.8-27b",
        description="Primary Groq model for planning, drafting, and agent tool loops",
    )
    groq_model_reasoning_fallbacks: str = Field(
        default="qwen/qwen3.6-27b,openai/gpt-oss-120b",
        description="Comma-separated fallbacks for the reasoning tier",
    )
    llm_strict_startup: bool = Field(
        default=True,
        description="Refuse to boot when configured Groq models are unavailable",
    )
    llm_tool_calling_mode: str = Field(
        default="auto",
        description="Tool calling strategy: auto, native, or json_dispatch",
    )
    llm_audit_enabled: bool = Field(
        default=True,
        description="Persist every LLM completion to llm_calls",
    )
    llm_max_retries: int = Field(
        default=6,
        description="Max Groq API retries per call (use 1 for eval runs to fail fast on 429)",
    )

    # Agent orchestrator bounds
    agent_max_iterations: int = Field(default=6)
    agent_max_tool_calls: int = Field(default=10)
    agent_token_budget: int = Field(default=16000)
    agent_timeout_seconds: float = Field(default=60.0)
    agent_circuit_breaker_threshold: int = Field(default=3)
    agent_daily_send_cap: int = Field(default=10)
    agent_per_company_cap: int = Field(default=3)
    agent_min_days_between_contacts: int = Field(default=7)
    agent_max_follow_ups_per_app: int = Field(default=3)
    agent_quiet_hours_start: int = Field(default=21, description="Hour (local) when quiet hours begin")
    agent_quiet_hours_end: int = Field(default=8, description="Hour (local) when quiet hours end")
    agent_timezone: str = Field(default="UTC")
    agent_blocked_domains: str = Field(
        default="",
        description="Comma-separated domains the agent must never contact",
    )

    # Outreach execution (Phase 3)
    agent_send_enabled: bool = Field(
        default=False,
        description="Master switch for real Gmail sends (keep False in dev)",
    )
    agent_send_test_inbox: str = Field(
        default="",
        description="If set, redirect all sends to this address instead of real recipients",
    )
    agent_undo_window_seconds: int = Field(default=60)
    agent_kill_switch_global: bool = Field(
        default=False,
        description="System-wide emergency stop for all agent sends",
    )

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
