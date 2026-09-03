"""Follow-up agent queues a send when the orchestrator decides follow_up without schedule_send."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.agents.schemas import AgentDecision, AgentRunResult
from app.services.follow_up_agent import FollowUpAgent, default_follow_up_draft


@pytest.mark.asyncio
async def test_evaluate_queues_follow_up_when_orchestrator_skips_schedule_send():
    app_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()
    outreach_id = uuid4()

    app = MagicMock()
    app.id = app_id
    app.user_id = user_id
    app.company_name = "Stripe"
    app.role_title = "Backend Engineer"

    db = AsyncMock()
    db.get = AsyncMock(side_effect=[app, None])
    db.commit = AsyncMock()
    db.flush = AsyncMock()

    orchestrator = MagicMock()
    orchestrator.groq = None
    orchestrator.policy = None
    orchestrator.queue = None
    orchestrator.run = AsyncMock(
        return_value=AgentRunResult(
            run_id=run_id,
            application_id=app_id,
            status="degraded",
            decision=AgentDecision(
                action="follow_up",
                reason="No response since last interaction.",
                email_draft=None,
            ),
        )
    )

    agent = FollowUpAgent(orchestrator=orchestrator)

    with patch(
        "app.agents.tools.handlers.schedule_send",
        new_callable=AsyncMock,
        return_value={
            "terminal": True,
            "decision": "follow_up",
            "outreach_action_id": str(outreach_id),
            "status": "pending_approval",
            "policy_vetoes": [],
            "draft": "hi",
        },
    ) as queued:
        response = await agent.evaluate_application(db, app_id)

    queued.assert_awaited_once()
    assert queued.await_args.kwargs.get("requires_approval") is True
    assert response["should_follow_up"] is True
    assert response["email_draft"]
    assert response["agent_run_id"] == str(run_id)
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_evaluate_does_not_queue_no_action():
    app_id = uuid4()
    app = MagicMock()
    app.id = app_id
    app.user_id = uuid4()

    db = AsyncMock()
    db.get = AsyncMock(return_value=app)
    db.commit = AsyncMock()

    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(
        return_value=AgentRunResult(
            run_id=uuid4(),
            application_id=app_id,
            status="completed",
            decision=AgentDecision(action="no_action", reason="Too recent."),
        )
    )
    agent = FollowUpAgent(orchestrator=orchestrator)

    with patch("app.agents.tools.handlers.schedule_send", new_callable=AsyncMock) as queued:
        response = await agent.evaluate_application(db, app_id)

    queued.assert_not_called()
    assert response["should_follow_up"] is False


def test_default_draft_includes_company_and_role():
    app = MagicMock()
    app.company_name = "Stripe"
    app.role_title = "Backend Engineer"
    draft = default_follow_up_draft(app)
    assert "Stripe" in draft
    assert "Backend Engineer" in draft
