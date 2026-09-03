#!/usr/bin/env python3
"""
Date-relative demo seed — applications, events, outreach, and outcomes.

Usage:
  cd backend && python scripts/seed_demo.py
  cd backend && python scripts/seed_demo.py --user-email demo@orbit.com
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.database import async_session_maker
from app.models import Application, Event, Outcome, OutreachAction, User


DEMO_SCENARIOS = [
    {
        "company": "Stripe",
        "role": "Backend Engineer",
        "status": "applied",
        "days_ago": 45,
        "email_from": "noreply@stripe.com",
        "email_subject": "Thanks for applying to Stripe",
        "email_snippet": "We received your application. A recruiter will be in touch if there is a fit.",
        "events": [
            {"type": "email_linked", "title": "Application received", "days_ago": 45},
        ],
        # Prior unanswered follow-up — agent should see this via get_outreach_history
        "prior_outreach": [
            {"days_ago": 20, "got_reply": False},
        ],
    },
    {
        "company": "Anthropic",
        "role": "Research Engineer",
        "status": "screening",
        "days_ago": 14,
        "email_from": "alex@anthropic.com",
        "events": [
            {
                "type": "action_required",
                "title": "Complete take-home",
                "days_ago": 2,
                "deadline_days": 5,
                "data": {
                    "action_type": "coding_test",
                    "urgency": "high",
                    "confidence": 0.92,
                },
            },
        ],
    },
    {
        "company": "Google",
        "role": "SWE Intern",
        "status": "oa",
        "days_ago": 3,
        "email_from": "no-reply@google.com",
        "events": [
            {
                "type": "action_required",
                "title": "Online assessment",
                "days_ago": 1,
                "deadline_days": 3,
                "data": {
                    "action_type": "online_assessment",
                    "urgency": "high",
                    "confidence": 0.95,
                },
            },
        ],
    },
    {
        "company": "Meta",
        "role": "Product Manager",
        "status": "interview",
        "days_ago": 7,
        "email_from": "university@meta.com",
        "events": [
            {"type": "interview", "title": "Phone screen scheduled", "days_ago": 3},
        ],
        # Prior follow-up that got a neutral reply — status clock should respect this
        "prior_outreach": [
            {
                "days_ago": 4,
                "got_reply": True,
                "reply_classification": "neutral",
                "days_to_reply": 1,
            },
        ],
    },
    {
        "company": "Apple",
        "role": "iOS Engineer",
        "status": "rejected",
        "days_ago": 30,
        "email_from": "jobs@apple.com",
        "events": [
            {
                "type": "status_change",
                "title": "Rejected",
                "days_ago": 5,
                "data": {"from": "interview", "to": "rejected"},
            },
        ],
    },
]


async def seed_demo(user_email: str | None) -> None:
    now = datetime.now(timezone.utc)
    today = now.date()

    async with async_session_maker() as db:
        from sqlalchemy import select

        if user_email:
            user = (
                await db.execute(select(User).where(User.email == user_email))
            ).scalar_one_or_none()
        else:
            user = (await db.execute(select(User).limit(1))).scalar_one_or_none()

        if not user:
            print("No user found — create a user first (OAuth or dev login).")
            return

        created = 0
        outreach_count = 0
        outcome_count = 0
        for scenario in DEMO_SCENARIOS:
            applied = today - timedelta(days=scenario["days_ago"])
            app = Application(
                id=uuid4(),
                user_id=user.id,
                company_name=scenario["company"],
                role_title=scenario["role"],
                status=scenario["status"],
                applied_date=applied,
                status_updated_at=now - timedelta(days=scenario["days_ago"]),
                source="seed_demo",
                email_from=scenario.get("email_from"),
                email_subject=scenario.get("email_subject"),
                email_snippet=scenario.get("email_snippet"),
                email_thread_id=f"seed-thread-{scenario['company'].lower()}",
            )
            db.add(app)
            await db.flush()

            for ev in scenario.get("events", []):
                scheduled = None
                data = dict(ev.get("data", {}) or {})
                if "deadline_days" in ev:
                    deadline = now + timedelta(days=ev["deadline_days"])
                    scheduled = deadline
                    data = {**data, "deadline": deadline.isoformat()}
                db.add(
                    Event(
                        application_id=app.id,
                        event_type=ev["type"],
                        title=ev["title"],
                        scheduled_at=scheduled,
                        data=data,
                        created_at=now - timedelta(days=ev["days_ago"]),
                    )
                )

            for idx, item in enumerate(scenario.get("prior_outreach") or []):
                sent_at = now - timedelta(days=int(item["days_ago"]))
                action = OutreachAction(
                    user_id=user.id,
                    application_id=app.id,
                    action_type="follow_up",
                    draft=f"[seed] Prior follow-up to {scenario['company']}",
                    risk_tier="low",
                    approval_mode="auto",
                    status="sent",
                    thread_id=app.email_thread_id,
                    idempotency_key=f"seed:{app.id}:prior:{idx}",
                    sent_at=sent_at,
                    to_address=scenario.get("email_from"),
                    subject=f"Re: {scenario.get('email_subject') or scenario['company']}",
                )
                db.add(action)
                await db.flush()
                outreach_count += 1
                if item.get("got_reply"):
                    days_to_reply = int(item.get("days_to_reply") or 1)
                    db.add(
                        Outcome(
                            user_id=user.id,
                            application_id=app.id,
                            outreach_action_id=action.id,
                            reply_classification=item.get("reply_classification")
                            or "neutral",
                            days_to_reply=days_to_reply,
                            observed_at=sent_at + timedelta(days=days_to_reply),
                        )
                    )
                    outcome_count += 1

            created += 1

        await db.commit()
        print(
            f"Seeded {created} apps, {outreach_count} outreach actions, "
            f"{outcome_count} outcomes for {user.email}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed date-relative demo data")
    parser.add_argument("--user-email", default=None)
    args = parser.parse_args()
    asyncio.run(seed_demo(args.user_email))


if __name__ == "__main__":
    main()
