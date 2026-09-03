"""Tests for llm_calls audit logging."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.llm.audit import estimate_cost_usd, hash_prompt, llm_run_id, log_llm_call
from app.llm.client import LLMUsage


def test_hash_prompt_is_stable():
    messages = [{"role": "user", "content": "hello"}]
    assert hash_prompt(messages) == hash_prompt(messages)
    assert hash_prompt(messages) != hash_prompt([{"role": "user", "content": "world"}])


def test_estimate_cost_usd_defaults():
    cost = estimate_cost_usd("unknown-model", 1000, 500)
    assert cost == Decimal("0.00015000")


def test_estimate_cost_usd_known_models_nonzero():
    cost = estimate_cost_usd("openai/gpt-oss-20b", 1_000_000, 1_000_000)
    assert cost == Decimal("0.37500000")
    qwen = estimate_cost_usd("qwen/qwen3.8-27b", 1_000_000, 0)
    assert qwen == Decimal("0.60000000")


@pytest.mark.asyncio
async def test_log_llm_call_persists_record():
    run_id = uuid4()
    token = llm_run_id.set(run_id)
    try:
        session = MagicMock()
        session.add = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.get_db_context") as mock_ctx:
            mock_ctx.return_value = session
            await log_llm_call(
                purpose="extract_actions_from_email",
                model="groq/compound-mini",
                messages=[{"role": "user", "content": "test"}],
                usage=LLMUsage(
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                    latency_ms=123.4,
                    model="groq/compound-mini",
                ),
                outcome="success",
            )

        added = session.add.call_args[0][0]
        assert added.purpose == "extract_actions_from_email"
        assert added.model == "groq/compound-mini"
        assert added.prompt_tokens == 10
        assert added.completion_tokens == 5
        assert added.total_tokens == 15
        assert added.outcome == "success"
        assert added.run_id == run_id
        assert len(added.prompt_hash) == 64
    finally:
        llm_run_id.reset(token)


@pytest.mark.asyncio
async def test_chat_logs_success_when_audit_enabled():
    from app.llm.client import LLMClient

    with patch("app.llm.client.get_settings") as mock_settings:
        mock_settings.return_value.groq_model_fast = "openai/gpt-oss-20b"
        mock_settings.return_value.groq_model_fast_fallbacks = (
            "openai/gpt-oss-120b,groq/compound-mini"
        )
        mock_settings.return_value.groq_model_reasoning = "qwen/qwen3.8-27b"
        mock_settings.return_value.groq_model_reasoning_fallbacks = (
            "qwen/qwen3.6-27b,openai/gpt-oss-120b"
        )
        mock_settings.return_value.llm_strict_startup = True
        mock_settings.return_value.llm_tool_calling_mode = "auto"
        mock_settings.return_value.llm_audit_enabled = True
        mock_settings.return_value.llm_max_retries = 6
        mock_settings.return_value.groq_api_key = "test-key"

        with patch("groq.AsyncGroq") as mock_groq_cls:
            mock_groq = MagicMock()
            mock_groq_cls.return_value = mock_groq
            client = LLMClient(api_key="test-key")
            client._client = mock_groq

            message = MagicMock()
            message.content = '{"ok": true}'
            message.tool_calls = []
            choice = MagicMock()
            choice.message = message
            choice.finish_reason = "stop"
            usage = MagicMock()
            usage.prompt_tokens = 3
            usage.completion_tokens = 2
            usage.total_tokens = 5
            completion = MagicMock()
            completion.choices = [choice]
            completion.usage = usage
            mock_groq.chat.completions.create = AsyncMock(return_value=completion)

            with patch("app.llm.audit.log_llm_call", new_callable=AsyncMock) as mock_log:
                await client.chat(
                    [{"role": "user", "content": "hi"}],
                    purpose="test_purpose",
                )
                mock_log.assert_awaited_once()
                assert mock_log.await_args.kwargs["purpose"] == "test_purpose"
                assert mock_log.await_args.kwargs["outcome"] == "success"
