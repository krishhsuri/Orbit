"""Agent outcome and value metrics for the dashboard."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.application import Application
from app.models.event import Event
from app.models.llm_call import LLMCall
from app.models.outcome import Outcome
from app.models.outreach_action import OutreachAction


async def build_outcomes_dashboard(db: AsyncSession, user_id: UUID) -> dict:
    sent_count = await db.scalar(
        select(func.count())
        .select_from(OutreachAction)
        .where(OutreachAction.user_id == user_id, OutreachAction.status == "sent")
    ) or 0

    reply_count = await db.scalar(
        select(func.count())
        .select_from(Outcome)
        .where(Outcome.user_id == user_id)
    ) or 0

    positive_replies = await db.scalar(
        select(func.count())
        .select_from(Outcome)
        .where(
            Outcome.user_id == user_id,
            Outcome.reply_classification == "positive",
        )
    ) or 0

    failed_sends = await db.scalar(
        select(func.count())
        .select_from(OutreachAction)
        .where(OutreachAction.user_id == user_id, OutreachAction.status == "failed")
    ) or 0

    vetoed = await db.scalar(
        select(func.count())
        .select_from(OutreachAction)
        .where(OutreachAction.user_id == user_id, OutreachAction.status == "vetoed")
    ) or 0

    total_runs = await db.scalar(
        select(func.count()).select_from(AgentRun).where(AgentRun.user_id == user_id)
    ) or 0

    degraded_runs = await db.scalar(
        select(func.count())
        .select_from(AgentRun)
        .where(AgentRun.user_id == user_id, AgentRun.status == "degraded")
    ) or 0

    runs_with_vetoes = await db.scalar(
        select(func.count())
        .select_from(AgentRun)
        .where(
            AgentRun.user_id == user_id,
            func.jsonb_array_length(AgentRun.policy_vetoes) > 0,
        )
    ) or 0

    escalations = await db.scalar(
        select(func.count())
        .select_from(AgentRun)
        .where(
            AgentRun.user_id == user_id,
            AgentRun.final_decision["action"].astext == "escalate",
        )
    ) or 0

    deadlines_caught = await db.scalar(
        select(func.count())
        .select_from(Event)
        .join(Application, Event.application_id == Application.id)
        .where(
            Application.user_id == user_id,
            Event.event_type == "action_required",
        )
    ) or 0

    ghost_recovered = await db.scalar(
        select(func.count())
        .select_from(Outcome)
        .join(Application, Outcome.application_id == Application.id)
        .where(
            Outcome.user_id == user_id,
            Application.status.in_(["interview", "screening", "oa", "offer"]),
        )
    ) or 0

    llm_cost = await db.scalar(
        select(func.coalesce(func.sum(LLMCall.estimated_cost_usd), 0)).where(
            LLMCall.run_id.in_(
                select(AgentRun.id).where(AgentRun.user_id == user_id)
            )
        )
    )
    llm_cost = float(llm_cost or 0)

    app_count = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.user_id == user_id, Application.deleted_at.is_(None))
    ) or 1

    reply_rate = round(reply_count / sent_count, 3) if sent_count else None
    policy_veto_rate = round(runs_with_vetoes / total_runs, 3) if total_runs else 0
    escalation_rate = round(escalations / total_runs, 3) if total_runs else 0
    degraded_rate = round(degraded_runs / total_runs, 3) if total_runs else 0

    return {
        "follow_ups_sent": sent_count,
        "replies_received": reply_count,
        "positive_replies": positive_replies,
        "reply_rate": reply_rate,
        "ghost_recovered": ghost_recovered,
        "deadlines_caught": deadlines_caught,
        "failed_sends": failed_sends,
        "policy_vetoes": vetoed,
        "policy_veto_rate": policy_veto_rate,
        "escalation_rate": escalation_rate,
        "agent_runs_total": total_runs,
        "agent_runs_degraded": degraded_runs,
        "degraded_rate": degraded_rate,
        "estimated_llm_cost_usd": round(llm_cost, 4),
        "cost_per_application_usd": round(llm_cost / app_count, 6),
    }
