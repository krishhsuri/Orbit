"""
Agents Router
Endpoints for the /agents page — action inbox, follow-up scan, send queue, and traces.
"""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.middleware.auth import get_current_user_id
from app.models import Application, Event
from app.models.follow_up_result import FollowUpResult

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("/actions")
async def get_agent_actions(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    All extracted actions across all user applications.
    Sorted by urgency (high → medium → low), then by date.
    No buttons, no computation — just reads from the events table.
    """
    urgency_order = {"high": 0, "medium": 1, "low": 2}

    # Get all action_required events for the user's applications
    stmt = (
        select(Event, Application.company_name, Application.role_title, Application.id.label("app_id"))
        .join(Application, Event.application_id == Application.id)
        .where(
            Application.user_id == user_id,
            Application.deleted_at.is_(None),
            Event.event_type == "action_required",
        )
        .order_by(Event.created_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    actions = []
    for event, company, role, app_id in rows:
        data = event.data or {}
        actions.append({
            "id": str(event.id),
            "application_id": str(app_id),
            "company": company,
            "role": role,
            "event_type": event.event_type,
            "title": event.title,
            "description": event.description,
            "action_type": data.get("action_type", "unknown"),
            "deadline": data.get("deadline"),
            "urgency": data.get("urgency", "low"),
            "confidence": data.get("confidence", 0),
            "source_text": data.get("source_text"),
            "needs_review": data.get("needs_review", False),
            "created_at": str(event.created_at),
            "scheduled_at": str(event.scheduled_at) if event.scheduled_at else None,
        })

    # ── Deduplicate ──
    # Email threads cause the same action to be extracted from multiple emails.
    # Keep only the highest-confidence version of each (app_id, action_type, source_text) combo.
    seen: dict[tuple, dict] = {}
    for a in actions:
        key = (a["application_id"], a["action_type"], (a["source_text"] or "").strip().lower()[:80])
        existing = seen.get(key)
        if existing is None or a["confidence"] > existing["confidence"]:
            seen[key] = a
    actions = list(seen.values())

    # Sort by urgency priority, then by date
    actions.sort(key=lambda a: (urgency_order.get(a["urgency"], 3), a["created_at"]))

    return {
        "actions": actions,
        "total": len(actions),
        "confirmed": len([a for a in actions if not a["needs_review"]]),
        "needs_review": len([a for a in actions if a["needs_review"]]),
    }


@router.get("/follow-ups")
async def get_follow_ups(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Pre-computed follow-up evaluations.
    Only returns applications where should_follow_up=True and not dismissed.
    Results are populated by Scan now (inline) or the ARQ cron follow-up job.
    """
    stmt = (
        select(
            FollowUpResult,
            Application.company_name,
            Application.role_title,
            Application.status,
            Application.applied_date,
            Application.source,
        )
        .join(Application, FollowUpResult.application_id == Application.id)
        .where(
            FollowUpResult.user_id == user_id,
            FollowUpResult.should_follow_up.is_(True),
            FollowUpResult.dismissed.is_(False),
            Application.deleted_at.is_(None),
        )
        .order_by(FollowUpResult.days_since_last_contact.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Append-only history: keep the newest row per application for the inbox UI.
    follow_ups = []
    seen_apps: set[str] = set()
    for fur, company, role, app_status, applied_date, source in sorted(
        rows,
        key=lambda r: r[0].evaluated_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    ):
        app_key = str(fur.application_id)
        if app_key in seen_apps:
            continue
        seen_apps.add(app_key)
        follow_ups.append({
            "id": str(fur.id),
            "application_id": str(fur.application_id),
            "company": company,
            "role": role,
            "status": app_status,
            "applied_date": str(applied_date),
            "source": source,
            "should_follow_up": fur.should_follow_up,
            "days_since_last_contact": fur.days_since_last_contact,
            "decision_reason": fur.decision_reason,
            "email_draft": fur.email_draft,
            "evaluated_at": str(fur.evaluated_at),
        })

    follow_ups.sort(key=lambda x: x["days_since_last_contact"], reverse=True)

    # Also get a count of total evaluated (for the "Last scan" indicator)
    total_stmt = select(FollowUpResult).where(FollowUpResult.user_id == user_id)
    total_result = await db.execute(total_stmt)
    all_results = total_result.scalars().all()
    last_scan = max((r.evaluated_at for r in all_results), default=None)

    return {
        "follow_ups": follow_ups,
        "total": len(follow_ups),
        "last_scan": str(last_scan) if last_scan else None,
    }


@router.post("/follow-ups/{result_id}/dismiss")
async def dismiss_follow_up(
    result_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Dismiss a follow-up recommendation (user doesn't want to act on it)."""
    stmt = select(FollowUpResult).where(
        FollowUpResult.id == result_id,
        FollowUpResult.user_id == user_id,
    )
    result = await db.execute(stmt)
    fur = result.scalar_one_or_none()

    if not fur:
        raise HTTPException(status_code=404, detail="Follow-up result not found")

    fur.dismissed = True
    await db.commit()

    return {"message": "Follow-up dismissed", "id": str(result_id)}


@router.get("/runs/{run_id}/trace")
async def get_agent_run_trace(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Reconstruct an agent run end-to-end for debugging and demos."""
    from app.models.agent_run import AgentRun

    stmt = select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    return {
        "run_id": str(run.id),
        "application_id": str(run.application_id),
        "trigger": run.trigger,
        "status": run.status,
        "iterations": run.iterations,
        "tool_call_count": run.tool_call_count,
        "prompt_tokens": run.prompt_tokens,
        "completion_tokens": run.completion_tokens,
        "latency_ms": float(run.latency_ms),
        "final_decision": run.final_decision,
        "policy_vetoes": run.policy_vetoes,
        "tool_trace": run.tool_trace,
        "error_message": run.error_message,
        "completed_at": str(run.completed_at) if run.completed_at else None,
    }


@router.post("/scan-now")
async def trigger_scan_now(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Manually trigger a follow-up scan for the current user's applications.
    Used for the initial demo or when user wants fresh results.
    This runs inline (not via the ARQ worker) for immediate results.
    """
    from app.models import Application
    from app.services.follow_up_agent import FollowUpAgent
    from datetime import datetime, timezone

    stmt = (
        select(Application)
        .where(
            Application.user_id == user_id,
            Application.deleted_at.is_(None),
            Application.status.notin_(["rejected", "offer", "accepted", "withdrawn"]),
        )
    )
    result = await db.execute(stmt)
    applications = result.scalars().all()

    agent = FollowUpAgent()
    evaluated = 0
    follow_ups_needed = 0

    for app in applications:
        try:
            evaluation = await agent.evaluate_application(db, app.id)
            if not evaluation:
                continue

            now = datetime.now(timezone.utc)

            # Append-only history (unique constraint dropped in Wave 2 hygiene).
            db.add(
                FollowUpResult(
                    application_id=app.id,
                    user_id=app.user_id,
                    should_follow_up=evaluation.get("should_follow_up", False),
                    days_since_last_contact=evaluation.get("days_since_last_contact", 0),
                    decision_reason=evaluation.get("decision_reason", ""),
                    email_draft=evaluation.get("email_draft"),
                    evaluated_at=now,
                    dismissed=False,
                )
            )

            if evaluation.get("should_follow_up"):
                follow_ups_needed += 1
            evaluated += 1

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[SCAN-NOW] Error: {e}")

    await db.commit()
    return {"evaluated": evaluated, "follow_ups_needed": follow_ups_needed}


@router.get("/outreach")
async def list_outreach_actions(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Approval inbox and pending undo sends."""
    from app.models.outreach_action import OutreachAction

    stmt = (
        select(OutreachAction, Application.company_name, Application.role_title)
        .join(Application, OutreachAction.application_id == Application.id)
        .where(OutreachAction.user_id == user_id)
        .order_by(OutreachAction.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return {
        "actions": [
            {
                "id": str(action.id),
                "application_id": str(action.application_id),
                "company": company,
                "role": role,
                "status": action.status,
                "risk_tier": action.risk_tier,
                "approval_mode": action.approval_mode,
                "draft_preview": (action.draft or "")[:200],
                "agent_run_id": str(action.agent_run_id) if action.agent_run_id else None,
                "undo_until": str(action.undo_until) if action.undo_until else None,
                "sent_at": str(action.sent_at) if action.sent_at else None,
                "created_at": str(action.created_at),
            }
            for action, company, role in rows
        ],
        "pending_approval": sum(1 for a, _, _ in rows if a.status == "pending_approval"),
        "pending_undo": sum(1 for a, _, _ in rows if a.status == "pending_undo"),
    }


@router.post("/outreach/{action_id}/approve")
async def approve_outreach(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    from app.models.outreach_action import OutreachAction
    from app.services.outreach_queue import OutreachQueueService

    action = (
        await db.execute(
            select(OutreachAction).where(
                OutreachAction.id == action_id,
                OutreachAction.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Outreach action not found")
    if action.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Cannot approve status={action.status}")

    queue = OutreachQueueService()
    await queue.approve_and_schedule(db, action)
    await db.commit()
    return {"id": str(action_id), "status": action.status, "undo_until": str(action.undo_until)}


@router.post("/outreach/{action_id}/cancel")
async def cancel_outreach(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Undo/cancel a pending send during the undo window or before approval."""
    from app.models.outreach_action import OutreachAction
    from app.services.outreach_queue import OutreachQueueService

    action = (
        await db.execute(
            select(OutreachAction).where(
                OutreachAction.id == action_id,
                OutreachAction.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Outreach action not found")
    if action.status in ("sent", "cancelled", "vetoed"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel status={action.status}")

    queue = OutreachQueueService()
    await queue.cancel(db, action)
    await db.commit()
    return {"id": str(action_id), "status": action.status}


@router.get("/kill-switch")
async def get_kill_switch(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    from app.config import get_settings
    from app.models.user import User
    from app.services.kill_switch import is_kill_switch_active

    user = await db.get(User, user_id)
    settings = get_settings()
    active, reason = is_kill_switch_active(settings, user)
    return {
        "active": active,
        "reason": reason,
        "global": settings.agent_kill_switch_global,
        "user": bool((user.preferences or {}).get("agent_kill_switch")) if user else False,
    }


@router.post("/kill-switch")
async def set_kill_switch(
    enabled: bool,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    from app.services.kill_switch import set_user_kill_switch

    ok = await set_user_kill_switch(db, user_id, enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()
    return {"user_kill_switch": enabled}


@router.get("/runs")
async def list_agent_runs(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    limit: int = 20,
):
    """Recent agent runs for trace UI."""
    from app.models.agent_run import AgentRun

    stmt = (
        select(AgentRun, Application.company_name, Application.role_title)
        .join(Application, AgentRun.application_id == Application.id)
        .where(AgentRun.user_id == user_id)
        .order_by(AgentRun.created_at.desc())
        .limit(min(limit, 50))
    )
    rows = (await db.execute(stmt)).all()
    return {
        "runs": [
            {
                "run_id": str(run.id),
                "application_id": str(run.application_id),
                "company": company,
                "role": role,
                "trigger": run.trigger,
                "status": run.status,
                "iterations": run.iterations,
                "tool_call_count": run.tool_call_count,
                "final_decision": run.final_decision,
                "policy_vetoes": run.policy_vetoes,
                "completed_at": str(run.completed_at) if run.completed_at else None,
                "created_at": str(run.created_at),
            }
            for run, company, role in rows
        ],
        "total": len(rows),
    }


@router.get("/outcomes/dashboard")
async def outcomes_dashboard(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    from app.services.agent_metrics import build_outcomes_dashboard

    return await build_outcomes_dashboard(db, user_id)
