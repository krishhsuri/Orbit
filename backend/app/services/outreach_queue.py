"""Enqueue outreach sends via ARQ with undo window."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.outreach_action import OutreachAction

logger = logging.getLogger(__name__)


class OutreachQueueService:
    async def schedule_send(
        self,
        db: AsyncSession,
        action: OutreachAction,
        *,
        requires_approval: bool = False,
    ) -> OutreachAction:
        settings = get_settings()
        now = datetime.now(timezone.utc)

        if requires_approval or action.approval_mode == "manual":
            action.status = "pending_approval"
            await db.flush()
            return action

        action.status = "pending_undo"
        action.undo_until = now + timedelta(seconds=settings.agent_undo_window_seconds)
        await db.flush()

        await self._enqueue(action.id, defer_seconds=settings.agent_undo_window_seconds)
        return action

    async def approve_and_schedule(
        self,
        db: AsyncSession,
        action: OutreachAction,
    ) -> OutreachAction:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        action.status = "pending_undo"
        action.undo_until = now + timedelta(seconds=settings.agent_undo_window_seconds)
        await db.flush()
        await self._enqueue(action.id, defer_seconds=settings.agent_undo_window_seconds)
        return action

    async def cancel(self, db: AsyncSession, action: OutreachAction) -> OutreachAction:
        if action.status in ("sent", "cancelled", "vetoed"):
            return action
        action.status = "cancelled"
        await db.flush()
        return action

    async def reenqueue_ready(self, action_id: UUID) -> None:
        """Enqueue an immediate send for a row whose undo window has elapsed."""
        await self._enqueue(action_id, defer_seconds=0)

    async def _enqueue(self, action_id: UUID, *, defer_seconds: int) -> None:
        settings = get_settings()
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
            kwargs = {}
            if defer_seconds > 0:
                kwargs["_defer_by"] = timedelta(seconds=defer_seconds)
            await pool.enqueue_job(
                "execute_outreach_send",
                str(action_id),
                **kwargs,
            )
            await pool.close()
            logger.info("Enqueued outreach send %s (defer %ss)", action_id, defer_seconds)
        except Exception as exc:
            logger.warning(
                "ARQ enqueue failed for %s: %s — action stays pending_undo",
                action_id,
                exc,
            )
