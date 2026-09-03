"""Execution context passed to every agent tool handler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.policy import PolicyEngine
from app.ml.llm.groq_client import GroqClient


@dataclass
class ToolContext:
    db: AsyncSession
    user_id: UUID
    application_id: UUID
    run_id: UUID
    groq: GroqClient | None = None
    policy: PolicyEngine | None = None
    draft_cache: dict[str, str] = field(default_factory=dict)
    queue: Any = None
