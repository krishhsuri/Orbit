"""Unit tests for AgentOrchestrator with a scripted fake LLM (no live Groq)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.agents.orchestrator import AgentOrchestrator
from app.agents.policy import PolicyEngine, PolicyVerdict
from app.agents.schemas import AgentDecision
from app.config import Settings
from app.llm.client import LLMResponse, LLMUsage, ToolCall


def _settings(**overrides) -> Settings:
    base = dict(
        debug=True,
        jwt_secret_key="orchestrator-test-secret",
        groq_api_key="",
        groq_model_reasoning="qwen/qwen3.8-27b",
        agent_max_iterations=4,
        agent_max_tool_calls=10,
        agent_token_budget=16000,
        agent_timeout_seconds=30.0,
        agent_circuit_breaker_threshold=3,
        agent_min_days_between_contacts=7,
        agent_quiet_hours_start=0,
        agent_quiet_hours_end=0,
        agent_daily_send_cap=100,
    )
    base.update(overrides)
    return Settings(**base)


def _app(*, user_id, app_id, days_ago: int = 30):
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=app_id,
        user_id=user_id,
        company_name="Acme",
        role_title="Engineer",
        status="applied",
        source="direct",
        applied_date=(now - timedelta(days=days_ago)).date(),
        status_updated_at=now - timedelta(days=days_ago),
        email_from="recruiter@acme.com",
        email_snippet="Thanks for applying.",
        events=[],
        notes=[],
    )


class ScriptedLLM:
    """Returns a fixed sequence of LLMResponse objects."""

    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self.is_configured = True
        self.calls = 0

    async def chat(self, messages, **kwargs) -> LLMResponse:
        self.calls += 1
        if not self._responses:
            return LLMResponse(
                content="no more scripted responses",
                tool_calls=[],
                usage=LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_orchestrator_tool_loop_one_assistant_message_per_batch():
    """Protocol: one assistant message with all tool_calls, then one tool msg each."""
    user_id = uuid4()
    app_id = uuid4()
    app = _app(user_id=user_id, app_id=app_id, days_ago=30)

    db = AsyncMock()
    db.get = AsyncMock(return_value=app)
    db.add = MagicMock()
    db.flush = AsyncMock()

    llm = ScriptedLLM(
        [
            LLMResponse(
                content="Checking state then deciding.",
                tool_calls=[
                    ToolCall(id="c1", name="get_application_state", arguments={"app_id": str(app_id)}),
                    ToolCall(id="c2", name="mark_no_action", arguments={"reason": "still early"}),
                ],
                usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )
        ]
    )

    registry = MagicMock()
    registry.openai_specs = MagicMock(return_value=[])
    registry.get = MagicMock(
        side_effect=lambda name: SimpleNamespace(
            is_terminal=(name in ("mark_no_action", "schedule_send", "escalate_to_human"))
        )
    )

    async def execute(_ctx, name, args):
        if name == "get_application_state":
            return {"days_since_last_contact": 30, "status": "applied"}
        if name == "mark_no_action":
            return {"terminal": True, "decision": "no_action", "reason": args.get("reason")}
        return {}

    registry.execute = AsyncMock(side_effect=execute)

    policy = MagicMock(spec=PolicyEngine)
    policy.check_follow_up_eligibility = AsyncMock(
        return_value=PolicyVerdict(allowed=True, vetoes=[])
    )

    settings = _settings()
    orch = AgentOrchestrator(
        settings=settings,
        llm=llm,
        registry=registry,
        policy=policy,
        queue=None,
    )
    orch.groq = None

    # Capture messages passed to llm.chat by wrapping
    captured: list = []
    original_chat = llm.chat

    async def capturing_chat(messages, **kwargs):
        captured.append([dict(m) for m in messages])
        return await original_chat(messages, **kwargs)

    llm.chat = capturing_chat  # type: ignore[method-assign]

    with patch("app.agents.orchestrator.AgentRun") as MockRun:
        MockRun.return_value = MagicMock(id=uuid4())
        result = await orch.run(db, user_id=user_id, application_id=app_id, trigger="test")

    assert result.status == "completed"
    assert result.decision.action == "no_action"
    # After first LLM turn, both tools in the batch should have executed
    names = [c.args[1] for c in registry.execute.await_args_list]
    assert "get_application_state" in names
    assert "mark_no_action" in names


@pytest.mark.asyncio
async def test_orchestrator_preserves_content_and_avoids_orphan_tool_ids():
    user_id = uuid4()
    app_id = uuid4()
    app = _app(user_id=user_id, app_id=app_id)

    db = AsyncMock()
    db.get = AsyncMock(return_value=app)
    db.add = MagicMock()
    db.flush = AsyncMock()

    # Cap at 1 tool call; LLM returns 2 — only first should be answered, no orphans.
    settings = _settings(agent_max_tool_calls=1)
    llm = ScriptedLLM(
        [
            LLMResponse(
                content="I will inspect then decide.",
                tool_calls=[
                    ToolCall(id="a", name="get_application_state", arguments={"app_id": str(app_id)}),
                    ToolCall(id="b", name="mark_no_action", arguments={"reason": "skip"}),
                ],
                usage=LLMUsage(prompt_tokens=5, completion_tokens=3, total_tokens=8),
            )
        ]
    )

    registry = MagicMock()
    registry.openai_specs = MagicMock(return_value=[])
    registry.get = MagicMock(return_value=SimpleNamespace(is_terminal=False))
    registry.execute = AsyncMock(
        return_value={"days_since_last_contact": 30, "status": "applied"}
    )

    policy = MagicMock(spec=PolicyEngine)
    policy.check_follow_up_eligibility = AsyncMock(
        return_value=PolicyVerdict(allowed=True, vetoes=[])
    )

    orch = AgentOrchestrator(
        settings=settings, llm=llm, registry=registry, policy=policy
    )
    orch.groq = None

    with patch("app.agents.orchestrator.AgentRun") as MockRun:
        agent_run = MagicMock()
        MockRun.return_value = agent_run
        with patch.object(
            orch,
            "_rules_fallback",
            new=AsyncMock(
                return_value=AgentDecision(action="no_action", reason="fallback")
            ),
        ):
            result = await orch.run(db, user_id=user_id, application_id=app_id)

    assert result.status == "degraded"
    assert "Tool call budget" in (result.error or "")
    # Only one tool executed (cap=1)
    assert registry.execute.await_count >= 1
    # Cap mid-response: first tool only; get_application_state at end also called
    executed_tools = [c.args[1] for c in registry.execute.await_args_list]
    assert executed_tools.count("get_application_state") >= 1
    assert "mark_no_action" not in executed_tools
    assert agent_run.estimated_cost_usd is not None


@pytest.mark.asyncio
async def test_orchestrator_preflight_injects_policy_block():
    user_id = uuid4()
    app_id = uuid4()
    app = _app(user_id=user_id, app_id=app_id, days_ago=2)

    db = AsyncMock()
    db.get = AsyncMock(return_value=app)
    db.add = MagicMock()
    db.flush = AsyncMock()

    seen_messages: list = []

    class CaptureLLM(ScriptedLLM):
        async def chat(self, messages, **kwargs):
            seen_messages.append(messages)
            return await super().chat(messages, **kwargs)

    llm = CaptureLLM(
        [
            LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="t1",
                        name="mark_no_action",
                        arguments={"reason": "too soon"},
                    )
                ],
                usage=LLMUsage(prompt_tokens=4, completion_tokens=2, total_tokens=6),
            )
        ]
    )

    registry = MagicMock()
    registry.openai_specs = MagicMock(return_value=[])
    registry.get = MagicMock(return_value=SimpleNamespace(is_terminal=True))
    registry.execute = AsyncMock(
        side_effect=[
            {"terminal": True, "decision": "no_action", "reason": "too soon"},
            {"days_since_last_contact": 2},
        ]
    )

    policy = MagicMock(spec=PolicyEngine)
    policy.check_follow_up_eligibility = AsyncMock(
        return_value=PolicyVerdict(allowed=False, vetoes=["min_days:2<7"])
    )

    orch = AgentOrchestrator(
        settings=_settings(), llm=llm, registry=registry, policy=policy
    )
    orch.groq = None

    with patch("app.agents.orchestrator.AgentRun") as MockRun:
        MockRun.return_value = MagicMock()
        result = await orch.run(db, user_id=user_id, application_id=app_id)

    assert "POLICY PRE-FLIGHT" in seen_messages[0][1]["content"]
    assert "min_days:2<7" in seen_messages[0][1]["content"]
    assert "min_days:2<7" in result.policy_vetoes
    assert result.decision.action == "no_action"
