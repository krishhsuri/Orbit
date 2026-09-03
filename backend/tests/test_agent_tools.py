"""Tests for agent tool registry."""

import pytest

from app.agents.tools.registry import build_registry


def test_registry_has_all_planned_tools():
    registry = build_registry()
    names = {t.name for t in registry.all_tools()}
    expected = {
        "get_application_state",
        "get_thread_history",
        "get_pending_actions",
        "get_outreach_history",
        "get_reply_priors",
        "get_policy_budget",
        "draft_followup",
        "schedule_send",
        "create_calendar_event",
        "escalate_to_human",
        "mark_no_action",
    }
    assert expected == names


def test_openai_specs_are_valid():
    registry = build_registry()
    for spec in registry.openai_specs():
        assert spec["type"] == "function"
        fn = spec["function"]
        assert fn["name"]
        assert fn["description"]
        assert "parameters" in fn


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from app.agents.tools.context import ToolContext

    registry = build_registry()
    ctx = ToolContext(
        db=AsyncMock(),
        user_id=uuid4(),
        application_id=uuid4(),
        run_id=uuid4(),
    )
    result = await registry.execute(ctx, "nonexistent_tool", {})
    assert "error" in result
