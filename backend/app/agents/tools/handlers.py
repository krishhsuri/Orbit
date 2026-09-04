"""Tool parameter schemas and handlers for the follow-up agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.agents.safety import detect_prompt_injection
from app.agents.tools.context import ToolContext
from app.agents.tools.registry import RegisteredTool
from app.models.application import Application
from app.models.email import Email, application_emails
from app.models.event import Event
from app.models.outcome import Outcome
from app.models.outreach_action import OutreachAction
from app.models.user import User
from app.services.outreach_queue import OutreachQueueService
from app.utils.email_utils import smart_truncate, strip_email_thread

# ── Parameter schemas ──────────────────────────────────────────────────────


class AppIdArgs(BaseModel):
    app_id: str = Field(description="Application UUID")


class CompanyDomainArgs(BaseModel):
    company_domain: str = Field(description="Company email domain, e.g. stripe.com")


class UserIdArgs(BaseModel):
    user_id: str = Field(description="User UUID")


class DraftFollowupArgs(BaseModel):
    app_id: str
    strategy: str = Field(default="polite_check_in", description="Tone/strategy hint")
    tone: str = Field(default="professional", description="professional | warm | concise")


class ScheduleSendArgs(BaseModel):
    app_id: str
    draft: str
    send_at: str | None = Field(default=None, description="ISO-8601 datetime or null for ASAP")
    risk_tier: str = Field(default="low", description="low | high")


class CalendarEventArgs(BaseModel):
    app_id: str
    title: str
    deadline: str = Field(description="ISO-8601 deadline")


class ReasonArgs(BaseModel):
    app_id: str
    reason: str


# ── Helpers ────────────────────────────────────────────────────────────────


def _parse_uuid(value: str) -> UUID:
    return UUID(value)


def _days_since_last_contact(app: Application) -> int:
    now = datetime.now(timezone.utc)
    last = app.status_updated_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    applied_dt = datetime.combine(app.applied_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    anchor = min(last, applied_dt)
    return (now - anchor).days


# ── Read tools ─────────────────────────────────────────────────────────────


async def get_application_state(ctx: ToolContext, args: AppIdArgs) -> dict[str, Any]:
    app_id = _parse_uuid(args.app_id)
    app = await ctx.db.get(
        Application,
        app_id,
        options=[selectinload(Application.events), selectinload(Application.notes)],
    )
    if not app or app.user_id != ctx.user_id:
        return {"error": "Application not found"}
    return {
        "application_id": str(app.id),
        "company": app.company_name,
        "role": app.role_title,
        "status": app.status,
        "source": app.source,
        "applied_date": str(app.applied_date),
        "days_since_last_contact": _days_since_last_contact(app),
        "status_updated_at": app.status_updated_at.isoformat(),
        "note_snippet": app.notes[0].content[:200] if app.notes else None,
    }


async def get_thread_history(ctx: ToolContext, args: AppIdArgs) -> dict[str, Any]:
    app_id = _parse_uuid(args.app_id)
    user = await ctx.db.get(User, ctx.user_id)
    user_email = (user.email or "").lower() if user else ""

    stmt = (
        select(Email)
        .join(application_emails, application_emails.c.email_id == Email.id)
        .where(
            application_emails.c.application_id == app_id,
            Email.user_id == ctx.user_id,
        )
        .order_by(Email.received_at.asc())
    )
    result = await ctx.db.execute(stmt)
    emails = result.scalars().all()
    messages = []
    for e in emails:
        from_addr = (e.from_address or "").lower()
        direction = "outbound" if user_email and user_email in from_addr else "inbound"
        messages.append(
            {
                "from": e.from_address,
                "subject": e.subject,
                "received_at": e.received_at.isoformat(),
                "body": smart_truncate(strip_email_thread(e.body_preview or ""), 500),
                "direction": direction,
            }
        )
    return {"application_id": args.app_id, "message_count": len(messages), "messages": messages}


async def get_pending_actions(ctx: ToolContext, args: AppIdArgs) -> dict[str, Any]:
    app_id = _parse_uuid(args.app_id)
    now = datetime.now(timezone.utc)
    stmt = select(Event).where(
        Event.application_id == app_id,
        Event.event_type == "action_required",
    )
    result = await ctx.db.execute(stmt)
    pending = []
    for event in result.scalars().all():
        data = event.data or {}
        deadline_raw = data.get("deadline") or event.scheduled_at
        deadline = None
        if deadline_raw:
            if isinstance(deadline_raw, str):
                deadline = datetime.fromisoformat(deadline_raw.replace("Z", "+00:00"))
            else:
                deadline = deadline_raw
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline and deadline > now:
            pending.append(
                {
                    "action_type": data.get("action_type"),
                    "title": event.title,
                    "deadline": deadline.isoformat(),
                    "urgency": data.get("urgency", "medium"),
                }
            )
    return {"application_id": args.app_id, "pending_actions": pending}


async def get_outreach_history(ctx: ToolContext, args: AppIdArgs) -> dict[str, Any]:
    app_id = _parse_uuid(args.app_id)
    stmt = (
        select(OutreachAction)
        .where(
            OutreachAction.application_id == app_id,
            OutreachAction.user_id == ctx.user_id,
        )
        .order_by(OutreachAction.created_at.desc())
    )
    actions = (await ctx.db.execute(stmt)).scalars().all()

    outcome_map: dict[UUID, Outcome] = {}
    if actions:
        o_stmt = select(Outcome).where(
            Outcome.outreach_action_id.in_([a.id for a in actions])
        )
        for outcome in (await ctx.db.execute(o_stmt)).scalars().all():
            outcome_map[outcome.outreach_action_id] = outcome

    now = datetime.now(timezone.utc)
    events_stmt = select(Event).where(
        Event.application_id == app_id,
        Event.event_type == "follow_up",
    )
    events = (await ctx.db.execute(events_stmt)).scalars().all()
    return {
        "application_id": args.app_id,
        "outreach_actions": [
            {
                "status": a.status,
                "draft_preview": (a.draft or "")[:120],
                "created_at": a.created_at.isoformat(),
                "sent_at": a.sent_at.isoformat() if a.sent_at else None,
                "risk_tier": a.risk_tier,
                "days_since_send": (now - a.sent_at).days if a.sent_at else None,
                "reply_classification": outcome_map[a.id].reply_classification
                if a.id in outcome_map
                else None,
                "got_reply": a.id in outcome_map,
            }
            for a in actions
        ],
        "follow_up_events": len(events),
    }


MIN_PRIOR_SAMPLE = 5
HARDCODED_PRIORS = {
    "cold_email": 0.15,
    "recruiter_initiated": 0.35,
}


async def get_reply_priors(ctx: ToolContext, args: CompanyDomainArgs) -> dict[str, Any]:
    domain = args.company_domain.lower().strip()
    prefix = domain.split(".")[0]

    apps_stmt = select(Application).where(
        Application.user_id == ctx.user_id,
        Application.deleted_at.is_(None),
        func.lower(Application.company_name).contains(prefix),
    )
    apps = (await ctx.db.execute(apps_stmt)).scalars().all()
    app_ids = [a.id for a in apps]

    def _fallback(*, reason: str, sample_size: int = 0) -> dict[str, Any]:
        return {
            "company_domain": domain,
            "sample_size": sample_size,
            "reply_rate": HARDCODED_PRIORS["cold_email"],
            "priors": HARDCODED_PRIORS,
            "reliable": False,
            "note": (
                f"{reason} Sample size below {MIN_PRIOR_SAMPLE}; "
                "using hardcoded priors (0.15 cold / 0.35 recruiter-initiated). "
                "Treat as unreliable."
            ),
            "source": "hardcoded_fallback",
        }

    if not app_ids:
        return _fallback(reason="No historical applications for this domain.")

    sent_stmt = select(OutreachAction).where(
        OutreachAction.user_id == ctx.user_id,
        OutreachAction.application_id.in_(app_ids),
        OutreachAction.status == "sent",
    )
    sent_actions = (await ctx.db.execute(sent_stmt)).scalars().all()
    if sent_actions:
        o_stmt = select(Outcome).where(
            Outcome.outreach_action_id.in_([a.id for a in sent_actions])
        )
        outcomes = (await ctx.db.execute(o_stmt)).scalars().all()
        n = len(sent_actions)
        reply_rate = round(len(outcomes) / n, 2) if n else None
        positive = sum(1 for o in outcomes if o.reply_classification == "positive")
        if n < MIN_PRIOR_SAMPLE:
            return {
                **_fallback(
                    reason=f"Only {n} sent outreach rows for this domain.",
                    sample_size=n,
                ),
                "observed_reply_rate": reply_rate,
                "observed_positive_reply_rate": round(positive / n, 2) if n else None,
            }
        return {
            "company_domain": domain,
            "sample_size": n,
            "reply_rate": reply_rate,
            "positive_reply_rate": round(positive / n, 2) if n else None,
            "reliable": True,
            "source": "outreach_outcomes",
        }

    if len(apps) < MIN_PRIOR_SAMPLE:
        return _fallback(
            reason="Sparse application-status history for this domain.",
            sample_size=len(apps),
        )

    responded = sum(1 for a in apps if a.status not in ("applied", "ghosted"))
    return {
        "company_domain": domain,
        "sample_size": len(apps),
        "reply_rate": round(responded / len(apps), 2),
        "reliable": True,
        "source": "application_status_fallback",
        "status_breakdown": {
            s: sum(1 for a in apps if a.status == s)
            for s in sorted({a.status for a in apps})
        },
    }


async def get_policy_budget(ctx: ToolContext, args: UserIdArgs) -> dict[str, Any]:
    if not ctx.policy:
        return {"error": "Policy engine not configured"}
    budget = await ctx.policy.get_budget(ctx.db, ctx.user_id)
    return budget


# ── Write / terminal tools ─────────────────────────────────────────────────


async def draft_followup(ctx: ToolContext, args: DraftFollowupArgs) -> dict[str, Any]:
    app_id = _parse_uuid(args.app_id)
    app = await ctx.db.get(
        Application, app_id, options=[selectinload(Application.notes)]
    )
    if not app or app.user_id != ctx.user_id:
        return {"error": "Application not found"}
    if not ctx.groq:
        return {"error": "LLM not configured"}

    # Refuse draft spend when policy already blocks a follow-up send.
    if ctx.policy:
        verdict = await ctx.policy.check_follow_up_eligibility(
            ctx.db, ctx.user_id, app
        )
        if not verdict.allowed:
            return {
                "error": "follow_up_blocked",
                "policy_vetoes": verdict.vetoes,
                "hint": "Call escalate_to_human or mark_no_action instead.",
            }

    context = f"Strategy: {args.strategy}. Tone: {args.tone}."
    if app.notes:
        context += f" Notes: {app.notes[0].content[:200]}"
    draft = await ctx.groq.generate_follow_up_draft(
        company=app.company_name,
        role=app.role_title,
        last_interaction_days=_days_since_last_contact(app),
        context=context,
        source=app.source,
    )
    ctx.draft_cache[str(app_id)] = draft
    return {"application_id": args.app_id, "draft": draft}


async def schedule_send(
    ctx: ToolContext,
    args: ScheduleSendArgs,
    *,
    requires_approval: bool | None = None,
) -> dict[str, Any]:
    app_id = _parse_uuid(args.app_id)
    app = await ctx.db.get(Application, app_id)
    if not app or app.user_id != ctx.user_id:
        return {"error": "Application not found"}

    send_at = None
    if args.send_at:
        send_at = datetime.fromisoformat(args.send_at.replace("Z", "+00:00"))

    risk = args.risk_tier if args.risk_tier in ("low", "high") else "low"
    force_approval = bool(requires_approval)
    approval_mode = "manual" if (force_approval or risk == "high") else "auto"
    idempotency_key = f"{ctx.run_id}:{app_id}:follow_up"

    action = OutreachAction(
        user_id=ctx.user_id,
        application_id=app_id,
        agent_run_id=ctx.run_id,
        action_type="follow_up",
        draft=args.draft,
        risk_tier=risk,
        approval_mode=approval_mode,
        status="queued",
        idempotency_key=idempotency_key,
        scheduled_at=send_at,
    )
    ctx.db.add(action)
    await ctx.db.flush()

    vetoes: list[str] = []
    # Block drafts / context that look like prompt injection.
    if detect_prompt_injection(args.draft) or detect_prompt_injection(app.email_snippet):
        vetoes.append("prompt_injection")
        action.status = "vetoed"
        await ctx.db.flush()
    elif ctx.policy:
        vetoes = await ctx.policy.veto_outreach(ctx.db, ctx.user_id, app, action)
        if vetoes:
            action.status = "vetoed"
            await ctx.db.flush()

    if action.status != "vetoed":
        queue = ctx.queue or OutreachQueueService()
        await queue.schedule_send(
            ctx.db,
            action,
            requires_approval=force_approval or approval_mode == "manual",
        )

    return {
        "terminal": True,
        "decision": "follow_up",
        "outreach_action_id": str(action.id),
        "status": action.status,
        "policy_vetoes": vetoes,
        "draft": args.draft,
        "risk_tier": risk,
        "needs_approval": approval_mode == "manual" or bool(vetoes),
    }


async def create_calendar_event(ctx: ToolContext, args: CalendarEventArgs) -> dict[str, Any]:
    app_id = _parse_uuid(args.app_id)
    deadline = datetime.fromisoformat(args.deadline.replace("Z", "+00:00"))
    event = Event(
        application_id=app_id,
        event_type="reminder",
        title=args.title,
        description=f"Agent-created reminder: {args.title}",
        scheduled_at=deadline,
        data={"source": "agent", "run_id": str(ctx.run_id)},
    )
    ctx.db.add(event)
    await ctx.db.flush()
    return {"event_id": str(event.id), "scheduled_at": deadline.isoformat()}


async def escalate_to_human(ctx: ToolContext, args: ReasonArgs) -> dict[str, Any]:
    draft = ctx.draft_cache.get(args.app_id)
    return {
        "terminal": True,
        "decision": "escalate",
        "reason": args.reason,
        "draft": draft,
    }


async def mark_no_action(ctx: ToolContext, args: ReasonArgs) -> dict[str, Any]:
    return {
        "terminal": True,
        "decision": "no_action",
        "reason": args.reason,
    }


ALL_TOOLS: list[RegisteredTool] = [
    RegisteredTool(
        "get_application_state",
        "Current application status, dates, and context.",
        AppIdArgs,
        get_application_state,
    ),
    RegisteredTool(
        "get_thread_history",
        "Email thread linked to this application, thread-stripped.",
        AppIdArgs,
        get_thread_history,
    ),
    RegisteredTool(
        "get_pending_actions",
        "Outstanding action_required items with future deadlines.",
        AppIdArgs,
        get_pending_actions,
    ),
    RegisteredTool(
        "get_outreach_history",
        "Prior follow-ups sent or queued for this application.",
        AppIdArgs,
        get_outreach_history,
    ),
    RegisteredTool(
        "get_reply_priors",
        "Historical reply rate for applications at this company domain.",
        CompanyDomainArgs,
        get_reply_priors,
    ),
    RegisteredTool(
        "get_policy_budget",
        "Remaining send budget and per-company cap status.",
        UserIdArgs,
        get_policy_budget,
    ),
    RegisteredTool(
        "draft_followup",
        "Generate a follow-up email draft.",
        DraftFollowupArgs,
        draft_followup,
    ),
    RegisteredTool(
        "schedule_send",
        "Queue a follow-up send. Terminal decision tool.",
        ScheduleSendArgs,
        schedule_send,
        is_terminal=True,
    ),
    RegisteredTool(
        "create_calendar_event",
        "Create a reminder/calendar event on the application timeline.",
        CalendarEventArgs,
        create_calendar_event,
    ),
    RegisteredTool(
        "escalate_to_human",
        "Route to human review when uncertain. Terminal decision tool.",
        ReasonArgs,
        escalate_to_human,
        is_terminal=True,
    ),
    RegisteredTool(
        "mark_no_action",
        "Explicit no-op with reason. Terminal decision tool.",
        ReasonArgs,
        mark_no_action,
        is_terminal=True,
    ),
]
