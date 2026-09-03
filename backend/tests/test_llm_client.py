"""Unit tests for the rebuilt LLM layer."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from app.llm.client import LLMClient, ModelTier
from app.llm.errors import LLMUnavailable


class SampleSchema(BaseModel):
    action: str
    score: float


def _completion(content: str, *, tool_calls=None):
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []

    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "stop"

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    usage.total_tokens = 15

    completion = MagicMock()
    completion.choices = [choice]
    completion.usage = usage
    return completion


@pytest.fixture
def llm_client():
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
        mock_settings.return_value.llm_audit_enabled = False
        mock_settings.return_value.llm_max_retries = 6
        mock_settings.return_value.groq_api_key = "test-key"

        with patch("groq.AsyncGroq") as mock_groq_cls:
            mock_groq = MagicMock()
            mock_groq_cls.return_value = mock_groq
            client = LLMClient(api_key="test-key")
            client._client = mock_groq
            yield client, mock_groq


@pytest.mark.asyncio
async def test_structured_output_validates_json(llm_client):
    client, groq = llm_client
    groq.chat.completions.create = AsyncMock(
        return_value=_completion('{"action": "discard", "score": 0.9}')
    )

    result = await client.structured_output(
        [{"role": "user", "content": "test"}],
        SampleSchema,
    )
    assert result.action == "discard"
    assert result.score == 0.9


@pytest.mark.asyncio
async def test_structured_output_repairs_invalid_payload(llm_client):
    client, groq = llm_client
    groq.chat.completions.create = AsyncMock(
        side_effect=[
            _completion('{"action": "discard", "score": "not-a-number"}'),
            _completion('{"action": "discard", "score": 0.5}'),
        ]
    )

    result = await client.structured_output(
        [{"role": "user", "content": "test"}],
        SampleSchema,
    )
    assert result.score == 0.5
    assert groq.chat.completions.create.await_count == 2


@pytest.mark.asyncio
async def test_chat_raises_unavailable_without_client():
    client = LLMClient(api_key="")
    client._client = None
    with pytest.raises(LLMUnavailable):
        await client.chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_verify_models_strict_raises_when_missing(llm_client):
    client, groq = llm_client
    model = MagicMock()
    model.id = "some-other-model"
    groq.models.list = AsyncMock(return_value=MagicMock(data=[model]))

    with pytest.raises(LLMUnavailable, match="No available Groq model"):
        await client.verify_models(strict=True)


@pytest.mark.asyncio
async def test_verify_models_ok_if_fallback_present(llm_client):
    client, groq = llm_client
    models = []
    for mid in ("groq/compound-mini", "qwen/qwen3.6-27b"):
        m = MagicMock()
        m.id = mid
        models.append(m)
    groq.models.list = AsyncMock(return_value=MagicMock(data=models))

    result = await client.verify_models(strict=True)
    assert "groq/compound-mini" in result.available_models
    assert "openai/gpt-oss-20b" in result.missing_models


def test_models_for_tier_returns_three(llm_client):
    client, _ = llm_client
    fast = client.models_for_tier(ModelTier.FAST)
    reasoning = client.models_for_tier(ModelTier.REASONING)
    assert fast == [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "groq/compound-mini",
    ]
    assert reasoning == [
        "qwen/qwen3.8-27b",
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-120b",
    ]


@pytest.mark.asyncio
async def test_chat_falls_back_on_model_not_found(llm_client):
    client, groq = llm_client
    groq.chat.completions.create = AsyncMock(
        side_effect=[
            Exception("404 model_not_found openai/gpt-oss-20b does not exist"),
            _completion('{"ok": true}'),
        ]
    )

    response = await client.chat([{"role": "user", "content": "hi"}])
    assert response.content == '{"ok": true}'
    assert response.usage.model == "openai/gpt-oss-120b"
    assert groq.chat.completions.create.await_count == 2
    assert groq.chat.completions.create.await_args.kwargs["model"] == "openai/gpt-oss-120b"


@pytest.mark.asyncio
async def test_chat_falls_back_on_rate_limit(llm_client):
    client, groq = llm_client
    groq.chat.completions.create = AsyncMock(
        side_effect=[
            Exception("429 rate limit exceeded"),
            Exception("429 rate limit exceeded"),
            _completion("ok"),
        ]
    )

    with patch("app.llm.client.asyncio.sleep", new_callable=AsyncMock):
        response = await client.chat([{"role": "user", "content": "hi"}])
    assert response.content == "ok"
    assert response.usage.model == "openai/gpt-oss-120b"


@pytest.mark.asyncio
async def test_json_dispatch_tool_call(llm_client):
    client, groq = llm_client
    client._native_tool_calling = False
    groq.chat.completions.create = AsyncMock(
        return_value=_completion(json.dumps({"tool": "ping", "args": {"message": "hello"}}))
    )

    tool_call = await client.call_tool(
        [{"role": "user", "content": "ping"}],
        [
            {
                "type": "function",
                "function": {
                    "name": "ping",
                    "description": "pong",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        tier=ModelTier.REASONING,
    )
    assert tool_call.name == "ping"
    assert tool_call.arguments["message"] == "hello"
