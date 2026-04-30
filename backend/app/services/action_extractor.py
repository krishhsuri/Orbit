import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.llm.groq_client import GroqClient
from app.config import get_settings
from app.models.event import Event

logger = logging.getLogger(__name__)

class ActionExtractor:
    """
    Agent A: Extracts actionable tasks from job emails and records them as events.
    """
    
    def __init__(self):
        settings = get_settings()
        self.llm = GroqClient(api_key=settings.groq_api_key)

    async def extract_and_record(self, db: AsyncSession, application_id: UUID, email_subject: str, email_body: str, email_id: str | None = None) -> List[Dict[str, Any]]:
        """
        Extract actions from email and save them as events for the application.
        """
        logger.info(f"Extracting actions for application {application_id}")
        
        result = await self.llm.extract_actions_from_email(
            subject=email_subject,
            body=email_body
        )
        
        if not result or not result.get("is_job_related"):
            logger.info("Email not job-related or no actions extracted.")
            return []

        extracted_actions = result.get("actions", [])
        recorded_actions = []

        for action in extracted_actions:
            # Create a timeline event for each action
            event = Event(
                application_id=application_id,
                event_type="action_required",
                title=f"Action Required: {action['action_type'].replace('_', ' ').title()}",
                description=action.get("reasoning"),
                data={
                    "email_id": email_id,
                    "action_type": action["action_type"],
                    "deadline": action.get("deadline"),
                    "urgency": action.get("urgency"),
                    "confidence": action.get("confidence"),
                    "source_text": action.get("source_text")
                },
                scheduled_at=self._parse_deadline(action.get("deadline"))
            )
            db.add(event)
            recorded_actions.append({**action, "email_id": email_id})
        
        await db.flush() # Flush to ensure they are added to the session
            
        logger.info(f"Extracted {len(recorded_actions)} actions for application {application_id}")
        return recorded_actions

    def _parse_deadline(self, deadline_str: Optional[str]) -> Optional[datetime]:
        if not deadline_str:
            return None
        try:
            return datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
