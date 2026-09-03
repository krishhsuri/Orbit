"""
Bounded ReAct orchestrator for follow-up decisions.

Hard bounds: max iterations, tool calls, token budget, wall-clock timeout,
and a circuit breaker after consecutive failures.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.policy import PolicyEngine
from app.agents.rules_baseline import (
    days_since_last_contact as days_since_last_contact_from_app,
)
from app.agents.rules_baseline import (
    rules_baseline_decision,
)
from app.agents.schemas import AgentDecision, AgentRunResult, ToolTraceEntry
from app.agents.tools.context import ToolContext
from app.agents.tools.registry import ToolRegistry, build_registry
from app.config import Settings, get_settings
from app.llm.audit import estimate_cost_usd
from app.llm.client import LLMClient, ModelTier
from app.llm.errors import LLMSchemaError, LLMUnavailable
from app.ml.llm.groq_client import GroqClient
from app.models.agent_run import AgentRun
from app.models.application import Application

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Orbit's follow-up agent for job applications.

Goal: decide whether to follow up, escalate to a human, or take no action.

Process:
1. Call get_application_state and get_pending_actions first.
2. Optionally consult get_thread_history, get_outreach_history, get_reply_priors, get_policy_budget.
3. If follow-up is appropriate AND not blocked by policy pre-flight, call draft_followup then schedule_send.
4. If uncertain or high-risk, call escalate_to_human.
5. If no follow-up is warranted, call mark_no_action with a clear reason.

You MUST end by calling exactly one terminal tool: schedule_send, escalate_to_human, or mark_no_action.
Never guess — use tools to gather facts before deciding.
If POLICY PRE-FLIGHT says follow-up is blocked, do NOT call draft_followup or schedule_send."""


class AgentOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        registry: ToolRegistry | None = None,
        policy: PolicyEngine | None = None,
        queue: object | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm or LLMClient(settings=self.settings)
        self.registry = registry or build_registry()
        self.policy = policy or PolicyEngine(self.settings)
        self.queue = queue
        self.groq = GroqClient(api_key=self.settings.groq_api_key) if self.settings.groq_api_key else None

    async def run(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        application_id: UUID,
        trigger: str = "manual",
    ) -> AgentRunResult:
        run_id = uuid4()
        started = time.perf_counter()
        trace: list[ToolTraceEntry] = []
        policy_vetoes: list[str] = []
        iterations = 0
        tool_call_count = 0
        prompt_tokens = 0
        completion_tokens = 0
        consecutive_failures = 0
        degraded = False
        error_msg: str | None = None
        days_since = 0

        app = await db.get(
            Application,
            application_id,
            options=[selectinload(Application.events)],
        )
        if not app or app.user_id != user_id:
            return self._failed_result(
                run_id, application_id, "Application not found", started
            )

        agent_run = AgentRun(
            id=run_id,
            user_id=user_id,
            application_id=application_id,
            trigger=trigger,
            status="running",
        )
        db.add(agent_run)
        await db.flush()

        ctx = ToolContext(
            db=db,
            user_id=user_id,
            application_id=application_id,
            run_id=run_id,
            groq=self.groq,
            policy=self.policy,
            queue=self.queue,
        )

        if not self.llm.is_configured:
            decision = await self._rules_fallback(db, user_id, app)
            days_since = days_since_last_contact_from_app(app)
            return await self._finalize(
                db,
                agent_run,
                run_id,
                application_id,
                decision,
                trace,
                policy_vetoes,
                iterations,
                tool_call_count,
                prompt_tokens,
                completion_tokens,
                started,
                status="degraded",
                error="LLM not configured; used rules baseline",
                days_since=days_since,
            )

        user_content = (
            f"Evaluate application {application_id} "
            f"({app.company_name} — {app.role_title}). "
            f"User ID: {user_id}."
        )

        # Cheap pre-flight: avoid burning a draft call when follow-up is already blocked.
        preflight = await self.policy.check_follow_up_eligibility(db, user_id, app)
        if not preflight.allowed:
            policy_vetoes.extend(preflight.vetoes)
            user_content += (
                f"\n\nPOLICY PRE-FLIGHT: follow-up is blocked "
                f"({', '.join(preflight.vetoes)}). "
                "Do NOT call draft_followup or schedule_send. "
                "Call escalate_to_human or mark_no_action instead."
            )

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        tools_spec = self.registry.openai_specs()
        terminal_decision: AgentDecision | None = None
        deadline = started + self.settings.agent_timeout_seconds

        try:
            while iterations < self.settings.agent_max_iterations:
                if time.perf_counter() > deadline:
                    degraded = True
                    error_msg = "Wall-clock timeout exceeded"
                    break
                if tool_call_count >= self.settings.agent_max_tool_calls:
                    degraded = True
                    error_msg = "Tool call budget exhausted"
                    break
                if prompt_tokens + completion_tokens >= self.settings.agent_token_budget:
                    degraded = True
                    error_msg = "Token budget exhausted"
                    break
                if consecutive_failures >= self.settings.agent_circuit_breaker_threshold:
                    degraded = True
                    error_msg = "Circuit breaker tripped after consecutive failures"
                    break

                iterations += 1
                try:
                    response = await self.llm.chat(
                        messages,
                        purpose="agent_orchestrator",
                        run_id=run_id,
                        tier=ModelTier.REASONING,
                        temperature=0.2,
                        max_tokens=800,
                        tools=tools_spec,
                        tool_choice="auto",
                    )
                except (LLMUnavailable, LLMSchemaError) as exc:
                    consecutive_failures += 1
                    degraded = True
                    error_msg = str(exc)
                    break

                consecutive_failures = 0
                prompt_tokens += response.usage.prompt_tokens
                completion_tokens += response.usage.completion_tokens

                if not response.tool_calls:
                    if response.content:
                        messages.append({"role": "assistant", "content": response.content})
                    continue

                remaining = self.settings.agent_max_tool_calls - tool_call_count
                batch = list(response.tool_calls[:remaining])
                if len(batch) < len(response.tool_calls):
                    degraded = True
                    error_msg = "Tool call budget exhausted mid-response"

                # One assistant message holding all tool_calls we will answer
                # (OpenAI/Groq protocol), preserving any reasoning content.
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in batch
                        ],
                    }
                )

                for tc in batch:
                    tool_call_count += 1
                    t0 = time.perf_counter()
                    result = await self.registry.execute(ctx, tc.name, tc.arguments)
                    latency = (time.perf_counter() - t0) * 1000
                    trace.append(
                        ToolTraceEntry(
                            iteration=iterations,
                            tool=tc.name,
                            arguments=tc.arguments,
                            result=result,
                            latency_ms=latency,
                            error=result.get("error"),
                        )
                    )

                    if result.get("policy_vetoes"):
                        policy_vetoes.extend(result["policy_vetoes"])

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result),
                        }
                    )

                    tool = self.registry.get(tc.name)
                    if tool and tool.is_terminal and result.get("terminal"):
                        terminal_decision = self._decision_from_terminal(result)
                        break

                if terminal_decision:
                    break
                if error_msg == "Tool call budget exhausted mid-response":
                    break

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Agent run failed")
            degraded = True
            error_msg = str(exc)

        state = await self.registry.execute(
            ctx, "get_application_state", {"app_id": str(application_id)}
        )
        days_since = state.get("days_since_last_contact", 0)

        if terminal_decision is None:
            decision = await self._rules_fallback(db, user_id, app)
            degraded = True
            if not error_msg:
                error_msg = "Agent did not reach a terminal tool; used rules baseline"
        else:
            decision = terminal_decision
            if policy_vetoes and decision.action == "follow_up":
                decision = AgentDecision(
                    action="no_action",
                    reason=f"Policy veto: {', '.join(policy_vetoes)}",
                    email_draft=decision.email_draft,
                )

        status = "degraded" if degraded else "completed"
        return await self._finalize(
            db,
            agent_run,
            run_id,
            application_id,
            decision,
            trace,
            policy_vetoes,
            iterations,
            tool_call_count,
            prompt_tokens,
            completion_tokens,
            started,
            status=status,
            error=error_msg,
            days_since=days_since,
        )

    async def _rules_fallback(
        self,
        db: AsyncSession,
        user_id: UUID,
        app: Application,
    ) -> AgentDecision:
        outcome = await rules_baseline_decision(db, user_id, app, self.policy)
        return AgentDecision(
            action=outcome["action"],
            reason=outcome["reason"],
            email_draft=outcome.get("email_draft"),
        )

    @staticmethod
    def _decision_from_terminal(result: dict) -> AgentDecision:
        action_map = {
            "follow_up": "follow_up",
            "no_action": "no_action",
            "escalate": "escalate",
        }
        raw = result.get("decision", "no_action")
        return AgentDecision(
            action=action_map.get(raw, "no_action"),
            reason=result.get("reason") or f"Agent chose {raw}",
            email_draft=result.get("draft"),
            risk_tier=result.get("risk_tier"),
            outreach_action_id=UUID(result["outreach_action_id"])
            if result.get("outreach_action_id")
            else None,
        )

    async def _finalize(
        self,
        db: AsyncSession,
        agent_run: AgentRun,
        run_id: UUID,
        application_id: UUID,
        decision: AgentDecision,
        trace: list[ToolTraceEntry],
        policy_vetoes: list[str],
        iterations: int,
        tool_call_count: int,
        prompt_tokens: int,
        completion_tokens: int,
        started: float,
        *,
        status: str,
        error: str | None,
        days_since: int = 0,
    ) -> AgentRunResult:
        latency_ms = (time.perf_counter() - started) * 1000
        # Aggregate run cost against the reasoning-tier model (orchestrator primary).
        estimated_cost = estimate_cost_usd(
            self.settings.groq_model_reasoning,
            prompt_tokens,
            completion_tokens,
        )
        agent_run.status = status
        agent_run.tool_trace = [t.model_dump() for t in trace]
        agent_run.iterations = iterations
        agent_run.tool_call_count = tool_call_count
        agent_run.prompt_tokens = prompt_tokens
        agent_run.completion_tokens = completion_tokens
        agent_run.estimated_cost_usd = estimated_cost
        agent_run.latency_ms = Decimal(str(round(latency_ms, 3)))
        agent_run.final_decision = decision.model_dump(mode="json")
        agent_run.policy_vetoes = policy_vetoes
        agent_run.error_message = error
        agent_run.completed_at = datetime.now(timezone.utc)
        await db.flush()

        return AgentRunResult(
            run_id=run_id,
            application_id=application_id,
            status=status,  # type: ignore[arg-type]
            decision=decision,
            days_since_last_contact=days_since,
            tool_trace=trace,
            policy_vetoes=policy_vetoes,
            iterations=iterations,
            tool_call_count=tool_call_count,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            error=error,
        )

    @staticmethod
    def _failed_result(
        run_id: UUID,
        application_id: UUID,
        reason: str,
        started: float,
    ) -> AgentRunResult:
        return AgentRunResult(
            run_id=run_id,
            application_id=application_id,
            status="failed",
            decision=AgentDecision(action="no_action", reason=reason),
            latency_ms=(time.perf_counter() - started) * 1000,
            error=reason,
        )
