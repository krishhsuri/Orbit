"""
Declarative policy envelope — can veto queued actions, never decides alone.

The LLM decides; the policy engine constrains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select
from zoneinfo import ZoneInfo

from app.config import Settings, get_settings
from app.models.application import Application
from app.models.outreach_action import OutreachAction

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

TERMINAL_STATUSES = frozenset({"rejected", "offer", "accepted", "withdrawn"})


@dataclass
class PolicyVerdict:
    allowed: bool
    vetoes: list[str] = field(default_factory=list)


class PolicyEngine:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def blocked_domains(self) -> set[str]:
        raw = self.settings.agent_blocked_domains.strip()
        if not raw:
            return set()
        return {d.strip().lower() for d in raw.split(",") if d.strip()}

    async def get_budget(self, db: AsyncSession, user_id: UUID) -> dict:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sent_today = await db.scalar(
            select(func.count())
            .select_from(OutreachAction)
            .where(
                OutreachAction.user_id == user_id,
                OutreachAction.created_at >= today_start,
                OutreachAction.status.in_(("queued", "sent")),
            )
        )
        daily_cap = self.settings.agent_daily_send_cap
        return {
            "daily_send_cap": daily_cap,
            "sends_today": sent_today or 0,
            "remaining_daily": max(0, daily_cap - (sent_today or 0)),
            "per_company_cap": self.settings.agent_per_company_cap,
            "min_days_between_contacts": self.settings.agent_min_days_between_contacts,
            "max_follow_ups_per_app": self.settings.agent_max_follow_ups_per_app,
        }

    async def check_follow_up_eligibility(
        self,
        db: AsyncSession,
        user_id: UUID,
        app: Application,
    ) -> PolicyVerdict:
        vetoes: list[str] = []

        if app.status in TERMINAL_STATUSES:
            vetoes.append(f"terminal_status:{app.status}")

        days = self._days_since_last_contact(app)
        if days < self.settings.agent_min_days_between_contacts:
            vetoes.append(
                f"min_days:{days}<{self.settings.agent_min_days_between_contacts}"
            )

        if await self._has_pending_actions(db, app.id):
            vetoes.append("pending_action_deadline_not_passed")

        prior_count = await db.scalar(
            select(func.count())
            .select_from(OutreachAction)
            .where(
                OutreachAction.application_id == app.id,
                OutreachAction.status.in_(("queued", "sent")),
            )
        )
        if (prior_count or 0) >= self.settings.agent_max_follow_ups_per_app:
            vetoes.append("max_follow_ups_reached")

        company_count = await db.scalar(
            select(func.count())
            .select_from(OutreachAction)
            .join(Application, OutreachAction.application_id == Application.id)
            .where(
                OutreachAction.user_id == user_id,
                Application.company_name == app.company_name,
                OutreachAction.status.in_(("queued", "sent")),
            )
        )
        if (company_count or 0) >= self.settings.agent_per_company_cap:
            vetoes.append("per_company_cap_reached")

        budget = await self.get_budget(db, user_id)
        if budget["remaining_daily"] <= 0:
            vetoes.append("daily_send_cap_exhausted")

        if self._in_quiet_hours():
            vetoes.append("quiet_hours")

        domain = self._company_domain(app)
        if domain and domain in self.blocked_domains:
            vetoes.append(f"blocked_domain:{domain}")

        return PolicyVerdict(allowed=not vetoes, vetoes=vetoes)

    async def veto_outreach(
        self,
        db: AsyncSession,
        user_id: UUID,
        app: Application,
        action: OutreachAction,
    ) -> list[str]:
        verdict = await self.check_follow_up_eligibility(db, user_id, app)
        return verdict.vetoes

    async def _has_pending_actions(self, db: AsyncSession, app_id: UUID) -> bool:
        from app.models.event import Event

        now = datetime.now(timezone.utc)
        stmt = select(Event).where(
            Event.application_id == app_id,
            Event.event_type == "action_required",
        )
        for event in (await db.execute(stmt)).scalars().all():
            deadline = event.scheduled_at
            data = event.data or {}
            if data.get("deadline"):
                raw = data["deadline"]
                deadline = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if deadline:
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                if deadline > now:
                    return True
        return False

    def _days_since_last_contact(self, app: Application) -> int:
        now = datetime.now(timezone.utc)
        last = app.status_updated_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        applied_dt = datetime.combine(app.applied_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        return (now - min(last, applied_dt)).days

    def _in_quiet_hours(self) -> bool:
        tz = ZoneInfo(self.settings.agent_timezone)
        hour = datetime.now(tz).hour
        start = self.settings.agent_quiet_hours_start
        end = self.settings.agent_quiet_hours_end
        if start > end:
            return hour >= start or hour < end
        return start <= hour < end

    @staticmethod
    def _company_domain(app: Application) -> str | None:
        if app.email_from and "@" in app.email_from:
            return app.email_from.split("@")[-1].lower()
        name = app.company_name.lower().replace(" ", "")
        return f"{name}.com" if name else None
