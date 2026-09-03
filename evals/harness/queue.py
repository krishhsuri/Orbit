"""No-op outreach queue so eval runs never touch Redis or Gmail."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.outreach_action import OutreachAction


class NoOpOutreachQueue:
    """Mirrors OutreachQueueService.schedule_send without ARQ enqueue."""

    def __init__(self) -> None:
        self.schedule_calls: list[UUID] = []
        self.enqueue_calls: list[UUID] = []

    async def schedule_send(
        self,
        db: AsyncSession,
        action: OutreachAction,
        *,
        requires_approval: bool = False,
    ) -> OutreachAction:
        self.schedule_calls.append(action.id)
        now = datetime.now(timezone.utc)
        if requires_approval or action.approval_mode == "manual":
            action.status = "pending_approval"
            await db.flush()
            return action

        settings = get_settings()
        action.status = "pending_undo"
        action.undo_until = now + timedelta(seconds=settings.agent_undo_window_seconds)
        await db.flush()
        # Deliberately do not enqueue to Redis.
        return action

    async def approve_and_schedule(
        self,
        db: AsyncSession,
        action: OutreachAction,
    ) -> OutreachAction:
        return await self.schedule_send(db, action, requires_approval=False)

    async def cancel(self, db: AsyncSession, action: OutreachAction) -> OutreachAction:
        if action.status in ("sent", "cancelled", "vetoed"):
            return action
        action.status = "cancelled"
        await db.flush()
        return action
