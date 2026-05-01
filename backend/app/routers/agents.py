"""
Agents Router
Endpoints for the /agents page — serves pre-computed Agent A and Agent B results.
No on-the-fly LLM calls. Everything is read from the database.
"""

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
    Agent A output: All extracted actions across all user applications.
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
    Agent B output: Pre-computed follow-up evaluations.
    Only returns applications where should_follow_up=True and not dismissed.
    Results are populated by the scheduled Celery Beat task.
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

    follow_ups = []
    for fur, company, role, app_status, applied_date, source in rows:
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


@router.post("/scan-now")
async def trigger_scan_now(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Manually trigger Agent B scan for the current user's applications.
    Used for the initial demo or when user wants fresh results.
    This runs inline (not via Celery) for immediate results.
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

            existing_stmt = select(FollowUpResult).where(
                FollowUpResult.application_id == app.id
            )
            existing = (await db.execute(existing_stmt)).scalar_one_or_none()

            if existing:
                existing.should_follow_up = evaluation.get("should_follow_up", False)
                existing.days_since_last_contact = evaluation.get("days_since_last_contact", 0)
                existing.decision_reason = evaluation.get("decision_reason", "")
                existing.email_draft = evaluation.get("email_draft")
                existing.evaluated_at = now
            else:
                new_result = FollowUpResult(
                    application_id=app.id,
                    user_id=app.user_id,
                    should_follow_up=evaluation.get("should_follow_up", False),
                    days_since_last_contact=evaluation.get("days_since_last_contact", 0),
                    decision_reason=evaluation.get("decision_reason", ""),
                    email_draft=evaluation.get("email_draft"),
                    evaluated_at=now,
                    dismissed=False,
                )
                db.add(new_result)

            if evaluation.get("should_follow_up"):
                follow_ups_needed += 1
            evaluated += 1

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[SCAN-NOW] Error: {e}")

    await db.commit()
    return {"evaluated": evaluated, "follow_ups_needed": follow_ups_needed}
