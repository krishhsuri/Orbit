"""
Rules-only baseline — mirrors pre-agent FollowUpAgent deterministic gates.

Used for ablation in eval_decision.py to answer "could this be if/else?"
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.policy import PolicyEngine
from app.models.application import Application

TERMINAL_STATUSES = frozenset({"rejected", "offer", "accepted", "withdrawn"})


def days_since_last_contact(app: Application) -> int:
    now = datetime.now(timezone.utc)
    last = app.status_updated_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    applied_dt = datetime.combine(app.applied_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    return (now - min(last, applied_dt)).days


async def has_pending_actions(app: Application) -> bool:
    now = datetime.now(timezone.utc)
    for event in app.events:
        if event.event_type != "action_required":
            continue
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


async def rules_baseline_decision(
    db: AsyncSession,
    user_id: UUID,
    app: Application,
    policy: PolicyEngine | None = None,
) -> dict[str, Any]:
    """Return {action, reason, should_follow_up, days_since_last_contact, email_draft?}."""
    days = days_since_last_contact(app)

    if app.status in TERMINAL_STATUSES:
        return {
            "action": "no_action",
            "should_follow_up": False,
            "days_since_last_contact": days,
            "reason": f"Application is in '{app.status}' stage.",
        }

    min_days = (policy.settings.agent_min_days_between_contacts if policy else 7)
    if days < min_days:
        return {
            "action": "no_action",
            "should_follow_up": False,
            "days_since_last_contact": days,
            "reason": f"Only {days} days since last interaction (threshold: {min_days}).",
        }

    if await has_pending_actions(app):
        return {
            "action": "no_action",
            "should_follow_up": False,
            "days_since_last_contact": days,
            "reason": "An action is still pending and its deadline has not passed.",
        }

    if policy:
        verdict = await policy.check_follow_up_eligibility(db, user_id, app)
        if not verdict.allowed:
            return {
                "action": "no_action",
                "should_follow_up": False,
                "days_since_last_contact": days,
                "reason": f"Policy blocked: {', '.join(verdict.vetoes)}",
            }

    return {
        "action": "follow_up",
        "should_follow_up": True,
        "days_since_last_contact": days,
        "reason": "No response since last interaction and no pending actions.",
        "email_draft": None,
    }
