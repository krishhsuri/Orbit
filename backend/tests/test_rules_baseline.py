"""Tests for rules-only baseline used in ablation eval."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.rules_baseline import (
    days_since_last_contact,
    rules_baseline_decision,
)


def _app(*, status="applied", days_ago=20, events=None):
    now = datetime.now(timezone.utc)
    app = MagicMock()
    app.id = uuid4()
    app.status = status
    app.company_name = "Ghost Inc"
    app.applied_date = (now - timedelta(days=days_ago)).date()
    app.status_updated_at = now - timedelta(days=days_ago)
    app.events = events or []
    return app


def test_days_since_last_contact_uses_older_anchor():
    app = _app(days_ago=45)
    assert days_since_last_contact(app) >= 45


@pytest.mark.asyncio
async def test_rules_rejects_terminal_status():
    app = _app(status="rejected", days_ago=30)
    db = AsyncMock()
    outcome = await rules_baseline_decision(db, uuid4(), app)
    assert outcome["action"] == "no_action"
    assert not outcome["should_follow_up"]


@pytest.mark.asyncio
async def test_rules_rejects_recent_contact():
    app = _app(days_ago=3)
    db = AsyncMock()
    outcome = await rules_baseline_decision(db, uuid4(), app)
    assert outcome["action"] == "no_action"


@pytest.mark.asyncio
async def test_rules_rejects_pending_action():
    future = datetime.now(timezone.utc) + timedelta(days=5)
    event = MagicMock()
    event.event_type = "action_required"
    event.scheduled_at = future
    event.data = {}
    app = _app(days_ago=20, events=[event])
    db = AsyncMock()
    outcome = await rules_baseline_decision(db, uuid4(), app)
    assert outcome["action"] == "no_action"
    assert "pending" in outcome["reason"].lower()


@pytest.mark.asyncio
async def test_rules_allows_stale_applied():
    app = _app(days_ago=20)
    db = AsyncMock()
    outcome = await rules_baseline_decision(db, uuid4(), app)
    assert outcome["action"] == "follow_up"
    assert outcome["should_follow_up"]
