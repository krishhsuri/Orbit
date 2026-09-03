"""Tests for agent outcomes dashboard metrics."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.agent_metrics import build_outcomes_dashboard


@pytest.mark.asyncio
async def test_dashboard_returns_expected_keys():
    db = AsyncMock()
    # sent, reply, positive, failed, vetoed, total_runs, degraded,
    # runs_with_vetoes, escalations, deadlines, ghost, llm_cost, app_count
    db.scalar = AsyncMock(side_effect=[0, 0, 0, 0, 0, 10, 2, 0, 0, 0, 0, 0.0, 5])
    result = await build_outcomes_dashboard(db, uuid4())
    assert "follow_ups_sent" in result
    assert "reply_rate" in result
    assert "policy_veto_rate" in result
    assert "cost_per_application_usd" in result
    assert "degraded_rate" in result
    assert "agent_runs_degraded" in result
    assert result["follow_ups_sent"] == 0
    assert result["agent_runs_total"] == 10
    assert result["agent_runs_degraded"] == 2
    assert result["degraded_rate"] == 0.2
