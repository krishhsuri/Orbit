"""Kill switch helpers for agent outreach."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.user import User


def is_kill_switch_active(
    settings: Settings | None = None,
    user: User | None = None,
) -> tuple[bool, str | None]:
    settings = settings or get_settings()
    if settings.agent_kill_switch_global:
        return True, "global_kill_switch"
    if user:
        prefs = user.preferences or {}
        if prefs.get("agent_kill_switch"):
            return True, "user_kill_switch"
    return False, None


async def set_user_kill_switch(
    db: AsyncSession,
    user_id: UUID,
    enabled: bool,
) -> bool:
    user = await db.get(User, user_id)
    if not user:
        return False
    prefs = dict(user.preferences or {})
    prefs["agent_kill_switch"] = enabled
    user.preferences = prefs
    await db.flush()
    return True
