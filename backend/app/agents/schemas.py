"""Shared schemas for agent runs and decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ToolTraceEntry(BaseModel):
    iteration: int
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None


class AgentDecision(BaseModel):
    action: Literal["follow_up", "no_action", "escalate"]
    reason: str
    email_draft: str | None = None
    risk_tier: Literal["low", "high"] | None = None
    scheduled_at: datetime | None = None
    outreach_action_id: UUID | None = None


class AgentRunResult(BaseModel):
    run_id: UUID
    application_id: UUID
    status: Literal["completed", "degraded", "failed"]
    decision: AgentDecision
    days_since_last_contact: int = 0
    tool_trace: list[ToolTraceEntry] = Field(default_factory=list)
    policy_vetoes: list[str] = Field(default_factory=list)
    iterations: int = 0
    tool_call_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    error: str | None = None

    def to_follow_up_response(self) -> dict[str, Any]:
        """Backward-compatible shape for FollowUpResult / scan-now."""
        should = self.decision.action in ("follow_up", "escalate")
        return {
            "application_id": str(self.application_id),
            "should_follow_up": should and not self.policy_vetoes,
            "days_since_last_contact": self.days_since_last_contact,
            "decision_reason": self.decision.reason,
            "email_draft": self.decision.email_draft,
            "agent_run_id": str(self.run_id),
            "risk_tier": self.decision.risk_tier,
            "needs_approval": self.decision.action == "escalate",
        }
