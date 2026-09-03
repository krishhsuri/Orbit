import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.agents.schemas import AgentRunResult
from app.models.agent_run import AgentRun
from app.models.application import Application

logger = logging.getLogger(__name__)


def default_follow_up_draft(app: Application) -> str:
    role = app.role_title or "the role"
    return (
        f"Hi {app.company_name} team,\n\n"
        f"I wanted to follow up on my application for {role}. "
        f"I'm still very interested and happy to share any additional materials.\n\n"
        f"Best regards"
    )


class FollowUpAgent:
    """Decides if a follow-up is appropriate, drafts it, and queues a send for review."""

    def __init__(self, orchestrator: AgentOrchestrator | None = None):
        self.orchestrator = orchestrator or AgentOrchestrator()

    async def evaluate_application(
        self, db: AsyncSession, application_id: UUID
    ) -> dict[str, Any]:
        app = await db.get(Application, application_id)
        if not app:
            return {"error": "Application not found"}

        result = await self.orchestrator.run(
            db,
            user_id=app.user_id,
            application_id=application_id,
            trigger="scan",
        )

        await self._ensure_queued(db, app, result)

        response = result.to_follow_up_response()
        if result.error and result.status == "failed":
            response["error"] = result.error
        await db.commit()
        return response

    async def _ensure_queued(
        self,
        db: AsyncSession,
        app: Application,
        result: AgentRunResult,
    ) -> None:
        """Rules fallback and incomplete LLM loops never call schedule_send — queue here."""
        if result.decision.action not in ("follow_up", "escalate"):
            return
        if result.decision.outreach_action_id or result.policy_vetoes:
            return

        from app.agents.tools.context import ToolContext
        from app.agents.tools.handlers import ScheduleSendArgs, schedule_send

        draft = result.decision.email_draft or default_follow_up_draft(app)
        ctx = ToolContext(
            db=db,
            user_id=app.user_id,
            application_id=app.id,
            run_id=result.run_id,
            groq=self.orchestrator.groq,
            policy=self.orchestrator.policy,
            queue=self.orchestrator.queue,
        )
        try:
            queued = await schedule_send(
                ctx,
                ScheduleSendArgs(
                    app_id=str(app.id),
                    draft=draft,
                    risk_tier="high" if result.decision.action == "escalate" else "low",
                ),
                requires_approval=True,
            )
        except Exception:
            logger.exception("Failed to queue follow-up for %s", app.id)
            return

        if queued.get("policy_vetoes"):
            result.policy_vetoes.extend(queued["policy_vetoes"])
            return
        if queued.get("status") == "vetoed":
            return

        outreach_id = queued.get("outreach_action_id")
        if not outreach_id:
            return

        result.decision.outreach_action_id = UUID(str(outreach_id))
        result.decision.email_draft = draft
        run = await db.get(AgentRun, result.run_id)
        if run:
            run.final_decision = result.decision.model_dump(mode="json")
            await db.flush()
