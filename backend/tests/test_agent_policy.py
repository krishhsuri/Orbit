"""Unit tests for the agent policy envelope."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.policy import PolicyEngine
from app.config import Settings


@pytest.fixture
def policy() -> PolicyEngine:
    settings = Settings(
        agent_min_days_between_contacts=7,
        agent_max_follow_ups_per_app=3,
        agent_daily_send_cap=10,
        agent_per_company_cap=3,
        agent_quiet_hours_start=12,
        agent_quiet_hours_end=12,
        agent_timezone="UTC",
    )
    return PolicyEngine(settings)


def _app(*, status="applied", days_ago=20):
    now = datetime.now(timezone.utc)
    app = MagicMock()
    app.id = uuid4()
    app.status = status
    app.company_name = "Acme Corp"
    app.email_from = "hr@acme.com"
    app.applied_date = (now - timedelta(days=days_ago)).date()
    app.status_updated_at = now - timedelta(days=days_ago)
    app.events = []
    return app


def _mock_db(*, scalar_return=0, events=None):
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=scalar_return)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = events or []
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.mark.asyncio
async def test_terminal_status_vetoed(policy):
    app = _app(status="rejected", days_ago=30)
    db = _mock_db()
    verdict = await policy.check_follow_up_eligibility(db, uuid4(), app)
    assert not verdict.allowed
    assert any("terminal_status" in v for v in verdict.vetoes)


@pytest.mark.asyncio
async def test_min_days_vetoed(policy):
    app = _app(days_ago=3)
    db = _mock_db()
    verdict = await policy.check_follow_up_eligibility(db, uuid4(), app)
    assert not verdict.allowed
    assert any(v.startswith("min_days") for v in verdict.vetoes)


@pytest.mark.asyncio
async def test_eligible_application(policy):
    app = _app(days_ago=20)
    db = _mock_db()
    verdict = await policy.check_follow_up_eligibility(db, uuid4(), app)
    assert verdict.allowed
    assert verdict.vetoes == []
