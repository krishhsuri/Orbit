"""Execute outreach sends with idempotency and safety checks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session_maker
from app.models.application import Application
from app.models.event import Event
from app.models.outreach_action import OutreachAction
from app.models.user import User
from app.services.gmail_service import GmailService
from app.services.kill_switch import is_kill_switch_active

logger = logging.getLogger(__name__)

SENDABLE_STATUSES = frozenset({"pending_undo", "approved"})


class OutreachExecutor:
    async def execute(self, outreach_action_id: UUID) -> dict:
        settings = get_settings()
        async with async_session_maker() as db:
            action = await db.get(OutreachAction, outreach_action_id)
            if not action:
                return {"status": "not_found"}

            if action.status == "sent":
                return {"status": "already_sent", "idempotent": True}

            if action.status not in SENDABLE_STATUSES:
                return {"status": "skipped", "reason": f"status={action.status}"}

            if action.undo_until and datetime.now(timezone.utc) < action.undo_until:
                # Re-enqueue for when the undo window ends so the send is not stranded.
                remaining = (
                    action.undo_until - datetime.now(timezone.utc)
                ).total_seconds()
                defer = max(1, int(remaining) + 1)
                try:
                    from app.services.outreach_queue import OutreachQueueService

                    await OutreachQueueService()._enqueue(action.id, defer_seconds=defer)
                except Exception as exc:
                    logger.warning(
                        "Failed to re-enqueue during undo window for %s: %s",
                        outreach_action_id,
                        exc,
                    )
                return {"status": "skipped", "reason": "undo_window_active", "requeued_in": defer}

            user = await db.get(User, action.user_id)
            app = await db.get(Application, action.application_id)
            if not user or not app:
                action.status = "failed"
                action.error_message = "User or application missing"
                await db.commit()
                return {"status": "failed"}

            blocked, reason = is_kill_switch_active(settings, user)
            if blocked:
                action.status = "cancelled"
                action.error_message = reason
                await db.commit()
                return {"status": "cancelled", "reason": reason}

            if not settings.agent_send_enabled:
                action.status = "failed"
                action.error_message = "agent_send_enabled=false"
                await db.commit()
                return {"status": "failed", "reason": "sends disabled"}

            if not settings.agent_send_test_inbox.strip():
                action.status = "failed"
                action.error_message = "agent_send_test_inbox required when sends enabled"
                await db.commit()
                return {"status": "failed", "reason": "test_inbox_required"}

            to_address = self._resolve_recipient(app, settings.agent_send_test_inbox)
            subject = action.subject or f"Following up — {app.role_title} at {app.company_name}"
            body = action.draft or ""

            try:
                gmail = GmailService(user, db)
                thread_id = action.thread_id
                in_reply_to = None
                if thread_id:
                    messages = gmail.fetch_thread_messages(thread_id)
                    if messages:
                        in_reply_to = messages[-1].get("id")

                response = gmail.send_message(
                    to_address,
                    subject,
                    body,
                    thread_id=thread_id,
                    in_reply_to=in_reply_to,
                )
            except Exception as exc:
                logger.exception("Outreach send failed for %s", outreach_action_id)
                action.status = "failed"
                action.error_message = str(exc)
                await db.commit()
                return {"status": "failed", "error": str(exc)}

            now = datetime.now(timezone.utc)
            action.status = "sent"
            action.sent_at = now
            action.gmail_message_id = response.get("id")
            action.thread_id = response.get("threadId") or action.thread_id
            action.to_address = to_address
            action.subject = subject

            db.add(
                Event(
                    application_id=app.id,
                    event_type="follow_up",
                    title=f"Follow-up sent to {app.company_name}",
                    description=body[:500],
                    data={
                        "outreach_action_id": str(action.id),
                        "gmail_message_id": action.gmail_message_id,
                        "thread_id": action.thread_id,
                        "to": to_address,
                    },
                    created_at=now,
                )
            )
            await db.commit()
            return {
                "status": "sent",
                "gmail_message_id": action.gmail_message_id,
                "thread_id": action.thread_id,
            }

    @staticmethod
    def _resolve_recipient(app: Application, test_inbox: str) -> str:
        # Always prefer the controlled test inbox when set (required when sends enabled).
        if test_inbox and test_inbox.strip():
            return test_inbox.strip()
        raise ValueError(
            "AGENT_SEND_TEST_INBOX is required — refusing to send to a real recipient"
        )
