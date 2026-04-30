import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ml.llm.groq_client import GroqClient
from app.config import get_settings
from app.models.application import Application

logger = logging.getLogger(__name__)

class FollowUpAgent:
    """
    Agent B: Decides if a follow-up is appropriate and drafts the email.
    """
    
    def __init__(self):
        settings = get_settings()
        self.llm = GroqClient(api_key=settings.groq_api_key)

    async def evaluate_application(self, db: AsyncSession, application_id: UUID) -> Dict[str, Any]:
        """
        Evaluate application state and decide on follow-up.
        """
        application = await db.get(
            Application, 
            application_id,
            options=[
                selectinload(Application.events),
                selectinload(Application.notes)
            ]
        )
        if not application:
            return {"error": "Application not found"}

        # 1. Deterministic Logic

        # Compute days since last contact (always included in response)
        # We use the OLDER of status_updated_at and applied_date because
        # status_updated_at defaults to record-creation time (datetime.utcnow()),
        # which can be much later than the actual application date when emails
        # are ingested retroactively (e.g., March email processed in April).
        now = datetime.now(timezone.utc)

        last_interaction = application.status_updated_at
        if last_interaction.tzinfo is None:
            last_interaction = last_interaction.replace(tzinfo=timezone.utc)

        # Also consider the applied_date as a potential "last contact" anchor
        applied_dt = datetime.combine(
            application.applied_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        # Use whichever is older — that reflects the true last meaningful contact
        last_interaction = min(last_interaction, applied_dt)

        days_since_last_contact = (now - last_interaction).days
        
        # Check status (Do not follow up if Rejected or Offer/Accepted)
        if application.status in ["rejected", "offer", "accepted", "withdrawn"]:
            return {
                "application_id": str(application_id),
                "should_follow_up": False,
                "days_since_last_contact": days_since_last_contact,
                "decision_reason": f"Application is in '{application.status}' stage."
            }

        if days_since_last_contact < 7:
            return {
                "application_id": str(application_id),
                "should_follow_up": False,
                "days_since_last_contact": days_since_last_contact,
                "decision_reason": f"Only {days_since_last_contact} days since last interaction (threshold: 7)."
            }

        # Check for pending actions
        has_pending_actions = False
        for event in application.events:
            if event.event_type == "action_required":
                deadline = event.scheduled_at
                if deadline:
                    if deadline.tzinfo is None:
                        deadline = deadline.replace(tzinfo=timezone.utc)
                    if deadline > now:
                        has_pending_actions = True
                        break
        
        if has_pending_actions:
            return {
                "application_id": str(application_id),
                "should_follow_up": False,
                "days_since_last_contact": days_since_last_contact,
                "decision_reason": "An action is still pending and its deadline has not passed."
            }

        # 2. LLM Drafting (if follow-up is appropriate)
        logger.info(f"Generating follow-up draft for {application.company_name}")
        
        # Gather context from notes if available
        context = ""
        if application.notes:
            context = f"Recent notes: {application.notes[0].content[:200]}"

        draft = await self.llm.generate_follow_up_draft(
            company=application.company_name,
            role=application.role_title,
            last_interaction_days=days_since_last_contact,
            context=context,
            source=application.source
        )

        return {
            "application_id": str(application_id),
            "should_follow_up": True,
            "days_since_last_contact": days_since_last_contact,
            "decision_reason": "No response since last interaction and no pending actions.",
            "email_draft": draft
        }
