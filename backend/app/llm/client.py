"""
Unified Groq LLM client with model tiers, typed errors, structured output, and tool calling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.llm.errors import LLMSchemaError, LLMUnavailable

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _unique_models(primary: str, fallbacks: str, *, limit: int = 3) -> list[str]:
    ordered: list[str] = []
    for raw in [primary, *fallbacks.split(",")]:
        name = raw.strip()
        if name and name not in ordered:
            ordered.append(name)
        if len(ordered) >= limit:
            break
    return ordered or [primary.strip()]


class ModelTier(str, Enum):
    FAST = "fast"
    REASONING = "reasoning"


class ToolCallingMode(str, Enum):
    NATIVE = "native"
    JSON_DISPATCH = "json_dispatch"


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    model: str = ""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: LLMUsage = field(default_factory=LLMUsage)
    finish_reason: str | None = None


@dataclass
class ModelAvailability:
    configured_models: list[str]
    available_models: set[str]
    missing_models: list[str]

    @property
    def all_available(self) -> bool:
        return not self.missing_models


class LLMClient:
    """
    Low-level Groq wrapper. Domain-specific helpers live in groq_client.py.
    """

    _REPAIR_SYSTEM = (
        "Your previous JSON response failed schema validation. "
        "Return corrected JSON only — no markdown, no explanation."
    )

    def __init__(self, api_key: str | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.api_key = api_key if api_key is not None else self.settings.groq_api_key
        self._client = None
        self._native_tool_calling: bool | None = None

        if self.api_key:
            try:
                from groq import AsyncGroq

                self._client = AsyncGroq(api_key=self.api_key)
            except ImportError:
                logger.warning("Groq library not installed")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self._client)

    def model_for_tier(self, tier: ModelTier) -> str:
        return self.models_for_tier(tier)[0]

    def models_for_tier(self, tier: ModelTier) -> list[str]:
        """Primary plus up to two fallbacks (max 3 unique models)."""
        if tier == ModelTier.REASONING:
            primary = self.settings.groq_model_reasoning
            extras = self.settings.groq_model_reasoning_fallbacks
        else:
            primary = self.settings.groq_model_fast
            extras = self.settings.groq_model_fast_fallbacks
        return _unique_models(primary, extras)

    def configured_models(self) -> list[str]:
        models: list[str] = []
        for tier in (ModelTier.FAST, ModelTier.REASONING):
            for model in self.models_for_tier(tier):
                if model not in models:
                    models.append(model)
        return models

    async def list_available_models(self) -> set[str]:
        if not self._client:
            raise LLMUnavailable("Groq API key not configured")
        try:
            response = await self._client.models.list()
            return {m.id for m in response.data}
        except Exception as exc:
            raise LLMUnavailable(f"Failed to list Groq models: {exc}", cause=exc) from exc

    async def verify_models(self, *, strict: bool | None = None) -> ModelAvailability:
        """
        Confirm configured model IDs exist on Groq.
        Raises LLMUnavailable when strict=True (default from settings) and any are missing.
        """
        if strict is None:
            strict = self.settings.llm_strict_startup

        configured = self.configured_models()
        if not self.is_configured:
            availability = ModelAvailability(configured, set(), configured)
            if strict:
                raise LLMUnavailable("Groq API key not configured")
            logger.warning("LLM startup check skipped: no Groq API key")
            return availability

        available = await self.list_available_models()
        missing = [m for m in configured if m not in available]
        result = ModelAvailability(configured, available, missing)

        fast_ok = any(m in available for m in self.models_for_tier(ModelTier.FAST))
        reasoning_ok = any(m in available for m in self.models_for_tier(ModelTier.REASONING))
        if missing:
            logger.warning("Some Groq models unavailable (will skip): %s", ", ".join(missing))
        if not fast_ok or not reasoning_ok:
            dead = []
            if not fast_ok:
                dead.append("fast")
            if not reasoning_ok:
                dead.append("reasoning")
            msg = f"No available Groq model for tier(s): {', '.join(dead)}"
            if strict:
                raise LLMUnavailable(msg)
            logger.error("LLM DEGRADED: %s", msg)
        else:
            logger.info(
                "LLM startup check passed. Fast chain=%s reasoning chain=%s",
                self.models_for_tier(ModelTier.FAST),
                self.models_for_tier(ModelTier.REASONING),
            )

        return result

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        purpose: str = "chat",
        run_id: UUID | None = None,
        tier: ModelTier = ModelTier.FAST,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
        response_format: dict[str, str] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        if not self._client:
            raise LLMUnavailable("Groq API key not configured")

        candidates = [model] if model else self.models_for_tier(tier)
        started = time.perf_counter()
        last_exc: LLMUnavailable | None = None
        resolved_model = candidates[0]

        for index, candidate in enumerate(candidates):
            resolved_model = candidate
            remaining = index < len(candidates) - 1
            kwargs: dict[str, Any] = {
                "messages": messages,
                "model": candidate,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format
            if tools is not None:
                kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice

            per_model_retries = (
                min(2, max(1, self.settings.llm_max_retries))
                if remaining
                else None
            )
            try:
                completion = await self._call_with_retry(
                    **kwargs, max_retries=per_model_retries
                )
                break
            except LLMUnavailable as exc:
                last_exc = exc
                latency_ms = (time.perf_counter() - started) * 1000
                if self.settings.llm_audit_enabled:
                    from app.llm.audit import log_llm_call

                    await log_llm_call(
                        purpose=purpose,
                        model=candidate,
                        messages=messages,
                        outcome="error",
                        error_class=type(exc).__name__,
                        latency_ms=latency_ms,
                        run_id=run_id,
                    )
                if remaining:
                    nxt = candidates[index + 1]
                    logger.warning(
                        "Model %s failed (%s); falling back to %s",
                        candidate,
                        exc,
                        nxt,
                    )
                    continue
                raise
        else:
            raise last_exc or LLMUnavailable("All Groq models failed")

        latency_ms = (time.perf_counter() - started) * 1000

        choice = completion.choices[0]
        message = choice.message
        usage = completion.usage

        tool_calls: list[ToolCall] = []
        if getattr(message, "tool_calls", None):
            for tc in message.tool_calls:
                raw_args = tc.function.arguments
                try:
                    parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    parsed_args = {"_raw": raw_args}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=parsed_args or {})
                )

        response = LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            usage=LLMUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
                latency_ms=latency_ms,
                model=resolved_model,
            ),
            finish_reason=getattr(choice, "finish_reason", None),
        )

        if self.settings.llm_audit_enabled:
            from app.llm.audit import log_llm_call

            await log_llm_call(
                purpose=purpose,
                model=resolved_model,
                messages=messages,
                usage=response.usage,
                outcome="success",
                run_id=run_id,
            )

        return response

    async def structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        *,
        purpose: str = "structured_output",
        run_id: UUID | None = None,
        tier: ModelTier = ModelTier.FAST,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> T:
        """JSON completion with Pydantic validation and one repair retry."""
        try:
            response = await self.chat(
                messages,
                purpose=purpose,
                run_id=run_id,
                tier=tier,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except LLMUnavailable:
            raise

        raw = response.content
        if not raw:
            await self._log_schema_error(
                purpose=purpose,
                model=response.usage.model,
                messages=messages,
                error_class="LLMSchemaError",
                run_id=run_id,
            )
            raise LLMSchemaError("LLM returned empty content")

        try:
            return schema.model_validate_json(raw)
        except ValidationError as first_err:
            repair_messages = [
                *messages,
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"{self._REPAIR_SYSTEM}\nValidation errors:\n{first_err}\n"
                        f"Expected schema: {schema.model_json_schema()}"
                    ),
                },
            ]
            try:
                repair = await self.chat(
                    repair_messages,
                    purpose=f"{purpose}_repair",
                    run_id=run_id,
                    tier=tier,
                    temperature=0.0,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
            except LLMUnavailable:
                raise

            if not repair.content:
                await self._log_schema_error(
                    purpose=purpose,
                    model=repair.usage.model,
                    messages=messages,
                    error_class="LLMSchemaError",
                    run_id=run_id,
                )
                raise LLMSchemaError(
                    "LLM repair attempt returned empty content", raw_content=raw
                ) from first_err
            try:
                return schema.model_validate_json(repair.content)
            except ValidationError as second_err:
                await self._log_schema_error(
                    purpose=purpose,
                    model=repair.usage.model,
                    messages=messages,
                    error_class="LLMSchemaError",
                    run_id=run_id,
                )
                raise LLMSchemaError(
                    f"Schema validation failed after repair: {second_err}",
                    raw_content=repair.content,
                ) from second_err

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        purpose: str = "complete_json",
        run_id: UUID | None = None,
        tier: ModelTier = ModelTier.FAST,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> dict[str, Any]:
        """Unstructured JSON object completion (legacy callers)."""
        try:
            response = await self.chat(
                messages,
                purpose=purpose,
                run_id=run_id,
                tier=tier,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except LLMUnavailable:
            raise

        if not response.content:
            await self._log_schema_error(
                purpose=purpose,
                model=response.usage.model,
                messages=messages,
                error_class="LLMSchemaError",
                run_id=run_id,
            )
            raise LLMSchemaError("LLM returned empty JSON content")
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError as exc:
            await self._log_schema_error(
                purpose=purpose,
                model=response.usage.model,
                messages=messages,
                error_class="LLMSchemaError",
                run_id=run_id,
            )
            raise LLMSchemaError(
                f"Invalid JSON: {exc}", raw_content=response.content
            ) from exc
        if not isinstance(parsed, dict):
            await self._log_schema_error(
                purpose=purpose,
                model=response.usage.model,
                messages=messages,
                error_class="LLMSchemaError",
                run_id=run_id,
            )
            raise LLMSchemaError(
                f"Expected JSON object, got {type(parsed).__name__}",
                raw_content=response.content,
            )
        return parsed

    async def complete_text(
        self,
        messages: list[dict[str, str]],
        *,
        purpose: str = "complete_text",
        run_id: UUID | None = None,
        tier: ModelTier = ModelTier.REASONING,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        try:
            response = await self.chat(
                messages,
                purpose=purpose,
                run_id=run_id,
                tier=tier,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMUnavailable:
            raise

        if not response.content:
            await self._log_schema_error(
                purpose=purpose,
                model=response.usage.model,
                messages=messages,
                error_class="LLMSchemaError",
                run_id=run_id,
            )
            raise LLMSchemaError("LLM returned empty text content")
        return response.content.strip()

    async def call_tool(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        *,
        purpose: str = "call_tool",
        run_id: UUID | None = None,
        tier: ModelTier = ModelTier.REASONING,
        temperature: float = 0.1,
        max_tokens: int = 800,
    ) -> ToolCall:
        """
        Request a single tool invocation.
        Uses native tool calling when supported, else JSON-dispatch fallback.
        """
        mode = await self._resolve_tool_calling_mode(tier)

        if mode == ToolCallingMode.NATIVE:
            response = await self.chat(
                messages,
                purpose=purpose,
                run_id=run_id,
                tier=tier,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice="required",
            )
            if response.tool_calls:
                return response.tool_calls[0]
            await self._log_schema_error(
                purpose=purpose,
                model=response.usage.model,
                messages=messages,
                error_class="LLMSchemaError",
                run_id=run_id,
            )
            raise LLMSchemaError("Native tool call returned no tool_calls")

        # JSON-dispatch fallback: model emits {"tool": "...", "args": {...}}
        tool_names = [
            t.get("function", {}).get("name", "")
            for t in tools
            if t.get("function", {}).get("name")
        ]
        dispatch_prompt = (
            "You must respond with JSON only: "
            '{"tool": "<tool_name>", "args": {<arguments object>}}. '
            f"Available tools: {', '.join(tool_names)}"
        )
        dispatch_messages = [
            {"role": "system", "content": dispatch_prompt},
            *messages,
        ]
        payload = await self.complete_json(
            dispatch_messages,
            purpose=f"{purpose}_json_dispatch",
            run_id=run_id,
            tier=tier,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        name = payload.get("tool")
        args = payload.get("args", {})
        if not name or not isinstance(args, dict):
            await self._log_schema_error(
                purpose=purpose,
                model=self.model_for_tier(tier),
                messages=messages,
                error_class="LLMSchemaError",
                run_id=run_id,
            )
            raise LLMSchemaError(
                'JSON dispatch expected {"tool": "...", "args": {...}}',
                raw_content=json.dumps(payload),
            )
        return ToolCall(id="json-dispatch", name=name, arguments=args)

    async def probe_native_tool_calling(self, *, tier: ModelTier = ModelTier.REASONING) -> bool:
        """Spike helper: returns True if Groq accepts native tool calling on the reasoning model."""
        if not self.is_configured:
            raise LLMUnavailable("Groq API key not configured")

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "ping",
                    "description": "Return a pong acknowledgement",
                    "parameters": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"],
                    },
                },
            }
        ]
        try:
            response = await self.chat(
                [
                    {
                        "role": "user",
                        "content": "Call the ping tool with message hello",
                    }
                ],
                purpose="probe_native_tool_calling",
                tier=tier,
                tools=tools,
                tool_choice="required",
                max_tokens=100,
            )
            ok = bool(response.tool_calls and response.tool_calls[0].name == "ping")
            self._native_tool_calling = ok
            return ok
        except Exception as exc:
            logger.info("Native tool calling probe failed: %s", exc)
            self._native_tool_calling = False
            return False

    async def _resolve_tool_calling_mode(self, tier: ModelTier) -> ToolCallingMode:
        configured = self.settings.llm_tool_calling_mode.lower()
        if configured == ToolCallingMode.JSON_DISPATCH.value:
            return ToolCallingMode.JSON_DISPATCH
        if configured == ToolCallingMode.NATIVE.value:
            if self._native_tool_calling is False:
                return ToolCallingMode.JSON_DISPATCH
            if self._native_tool_calling is True:
                return ToolCallingMode.NATIVE
            if await self.probe_native_tool_calling(tier=tier):
                return ToolCallingMode.NATIVE
            return ToolCallingMode.JSON_DISPATCH
        # auto: probe once
        if self._native_tool_calling is None:
            await self.probe_native_tool_calling(tier=tier)
        return (
            ToolCallingMode.NATIVE
            if self._native_tool_calling
            else ToolCallingMode.JSON_DISPATCH
        )

    async def _call_with_retry(self, *, max_retries: int | None = None, **kwargs: Any) -> Any:
        retries = max(1, max_retries if max_retries is not None else self.settings.llm_max_retries)
        for attempt in range(retries):
            try:
                return await self._client.chat.completions.create(**kwargs)
            except Exception as exc:
                err_str = str(exc)
                non_retryable = (
                    "404" in err_str
                    or "model_not_found" in err_str
                    or "does not exist" in err_str.lower()
                    or "tool calling` is not supported" in err_str
                    or "json_validate_failed" in err_str
                )
                if non_retryable:
                    raise LLMUnavailable(
                        f"Groq API call failed: {exc}",
                        cause=exc,
                    ) from exc
                is_rate_limit = "429" in err_str or "rate limit" in err_str.lower()
                if is_rate_limit:
                    if attempt < retries - 1:
                        wait_time = 10.0
                        match = re.search(r"Please try again in ([0-9.]+)s", err_str)
                        if match:
                            wait_time = float(match.group(1)) + 1.0
                        else:
                            wait_time = min((2**attempt) * 5.0, 30.0)
                        logger.warning(
                            "Groq rate limit; retry in %.2fs (attempt %d/%d)",
                            wait_time,
                            attempt + 1,
                            retries,
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise LLMUnavailable(
                        f"Groq rate limit exceeded: {exc}",
                        cause=exc,
                    ) from exc
                if attempt == retries - 1:
                    raise LLMUnavailable(
                        f"Groq API call failed after {retries} attempts: {exc}",
                        cause=exc,
                    ) from exc
                logger.error("Groq API call failed (attempt %d): %s", attempt + 1, exc)
        raise LLMUnavailable("Groq API call failed with no response")

    async def _log_schema_error(
        self,
        *,
        purpose: str,
        model: str,
        messages: list[dict[str, str]],
        error_class: str,
        run_id: UUID | None = None,
    ) -> None:
        if not self.settings.llm_audit_enabled:
            return
        from app.llm.audit import log_llm_call

        await log_llm_call(
            purpose=purpose,
            model=model,
            messages=messages,
            outcome="error",
            error_class=error_class,
            run_id=run_id,
        )
