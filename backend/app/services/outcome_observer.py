"""Outcome observation for sent outreach — reply detection and classification."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.outcome import Outcome
from app.models.outreach_action import OutreachAction
from app.models.user import User
from app.services.gmail_service import GmailService, parse_bare_email
from app.services.reply_classifier import classify_reply


class OutcomeObserver:
    async def observe_replies_for_user(self, db: AsyncSession, user_id: UUID) -> int:
        user = await db.get(User, user_id)
        if not user or not user.gmail_refresh_token_encrypted:
            return 0

        stmt = (
            select(OutreachAction)
            .where(
                OutreachAction.user_id == user_id,
                OutreachAction.status == "sent",
                OutreachAction.thread_id.isnot(None),
            )
            .options(selectinload(OutreachAction.application))
        )
        actions = (await db.execute(stmt)).scalars().all()

        existing_stmt = select(Outcome.outreach_action_id)
        existing_ids = set((await db.execute(existing_stmt)).scalars().all())

        gmail = GmailService(user, db)
        observed = 0

        for action in actions:
            if action.id in existing_ids:
                continue
            if not action.thread_id or not action.sent_at:
                continue

            messages = gmail.fetch_thread_messages(action.thread_id)
            user_email = user.email.lower()

            for msg in messages:
                if msg["id"] == action.gmail_message_id:
                    continue
                sender = parse_bare_email(msg.get("from_address", "")).lower()
                if sender == user_email:
                    continue

                msg_date = _parse_date(msg.get("date", ""))
                if msg_date and action.sent_at and msg_date <= action.sent_at:
                    continue

                classification = classify_reply(
                    msg.get("body_preview", ""),
                    msg.get("subject", ""),
                )
                days_to_reply = None
                if msg_date and action.sent_at:
                    days_to_reply = max(0, (msg_date - action.sent_at).days)

                outcome = Outcome(
                    user_id=user_id,
                    application_id=action.application_id,
                    outreach_action_id=action.id,
                    reply_gmail_message_id=msg["id"],
                    reply_classification=classification,
                    days_to_reply=days_to_reply,
                    observed_at=datetime.now(timezone.utc),
                )
                db.add(outcome)
                observed += 1
                break

        if observed:
            await db.flush()
        return observed


def _parse_date(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None
