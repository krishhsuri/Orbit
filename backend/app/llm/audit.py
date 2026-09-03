"""Persist LLM call metadata to the llm_calls audit table."""

from __future__ import annotations

import hashlib
import json
import logging
from contextvars import ContextVar
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.llm.client import LLMUsage

logger = logging.getLogger(__name__)

llm_run_id: ContextVar[UUID | None] = ContextVar("llm_run_id", default=None)

# USD per 1M tokens (input, output). Best-effort from Groq public pricing (2026).
_MODEL_COST_PER_MILLION: dict[str, tuple[float, float]] = {
    "groq/compound-mini": (0.075, 0.30),
    "groq/compound": (0.15, 0.60),
    "qwen/qwen3.8-27b": (0.60, 3.00),
    "qwen/qwen3.6-27b": (0.60, 3.00),
    "qwen/qwen3-32b": (0.29, 0.59),
    "openai/gpt-oss-20b": (0.075, 0.30),
    "openai/gpt-oss-120b": (0.15, 0.60),
}
_DEFAULT_COST_PER_MILLION = (0.10, 0.10)


def hash_prompt(messages: list[dict[str, Any]]) -> str:
    payload = json.dumps(messages, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    input_rate, output_rate = _MODEL_COST_PER_MILLION.get(
        model, _DEFAULT_COST_PER_MILLION
    )
    cost = (
        prompt_tokens * input_rate + completion_tokens * output_rate
    ) / 1_000_000
    return Decimal(str(cost)).quantize(Decimal("0.00000001"))


async def log_llm_call(
    *,
    purpose: str,
    model: str,
    messages: list[dict[str, Any]],
    usage: LLMUsage | None = None,
    outcome: str,
    error_class: str | None = None,
    latency_ms: float = 0.0,
    run_id: UUID | None = None,
) -> None:
    """Best-effort audit write; never raises to callers."""
    try:
        from app.database import get_db_context
        from app.models.llm_call import LLMCall

        resolved_run_id = run_id if run_id is not None else llm_run_id.get()
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0
        resolved_latency = usage.latency_ms if usage else latency_ms

        record = LLMCall(
            run_id=resolved_run_id,
            purpose=purpose,
            model=model or (usage.model if usage else "unknown"),
            prompt_hash=hash_prompt(messages),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=Decimal(str(resolved_latency)).quantize(Decimal("0.001")),
            estimated_cost_usd=estimate_cost_usd(
                model or (usage.model if usage else "unknown"),
                prompt_tokens,
                completion_tokens,
            ),
            outcome=outcome,
            error_class=error_class,
        )

        async with get_db_context() as db:
            db.add(record)
    except Exception as exc:
        logger.error("Failed to persist llm_calls audit row: %s", exc)
