import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.ml.llm.groq_client import GroqClient
from app.config import get_settings
from app.llm.errors import LLMUnavailable, LLMSchemaError
from app.models.event import Event

logger = logging.getLogger(__name__)

# Actions with confidence below this threshold are flagged as needing manual review
CONFIDENCE_THRESHOLD = 0.8
# Actions below this threshold are discarded entirely as likely false positives
DISCARD_THRESHOLD = 0.4


class ActionExtractor:
    """
    Agent A: Extracts actionable tasks from job emails and records them as events.
    
    Responsibilities (per spec):
    - Identify whether the email contains any applicant action
    - Extract all relevant actions
    - Normalize them into a structured format
    - Reject false positives (newsletters, marketing, generic updates)
    
    Output schema matches the assignment's Required Output Schema.
    """
    
    def __init__(self):
        settings = get_settings()
        self.llm = GroqClient(api_key=settings.groq_api_key)

    async def extract_and_record(
        self,
        db: AsyncSession,
        application_id: UUID,
        email_subject: str,
        email_body: str,
        email_id: str | None = None,
        company: str | None = None,
        role: str | None = None,
        email_timestamp: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract actions from email and save them as events for the application.
        
        Args:
            db: Database session
            application_id: UUID of the parent Application
            email_subject: Email subject line
            email_body: Full email body text
            email_id: Optional Gmail message ID
            company: Optional company name (improves LLM context)
            role: Optional role title (improves LLM context)
            email_timestamp: Optional ISO-8601 email date (improves LLM context)
        
        Returns:
            List of extracted action dicts matching the assignment's output schema.
        """
        logger.info(f"Extracting actions for application {application_id}")
        
        try:
            result = await self.llm.extract_actions_from_email(
                subject=email_subject,
                body=email_body,
                company=company,
                role=role,
                email_timestamp=email_timestamp,
            )
        except (LLMUnavailable, LLMSchemaError) as exc:
            logger.error("Action extraction failed for application %s: %s", application_id, exc)
            return []
        
        if not result.get("is_job_related"):
            logger.info("Email not job-related or no actions extracted.")
            return []

        extracted_actions = result.get("actions", [])
        recorded_actions = []

        # ── Deduplication layer ──
        # Load existing action events for this application to avoid duplicates
        # caused by email threads (quoted replies repeat the same action text)
        existing_stmt = (
            select(Event)
            .where(Event.application_id == application_id)
            .where(Event.event_type == "action_required")
        )
        existing_events = (await db.execute(existing_stmt)).scalars().all()

        # Build a set of source_text_fingerprints for fast lookup
        existing_source_fingerprints: set[str] = set()
        for evt in existing_events:
            d = evt.data or {}
            src = (d.get("source_text") or "").strip().lower()[:100]
            if src:
                existing_source_fingerprints.add(src)

        # Track within-batch duplicates too
        batch_source_fingerprints: set[str] = set()

        for action in extracted_actions:
            confidence = action.get("confidence", 0)

            # Quality gate (two-tier, per whiteboard architecture):
            # - Below DISCARD_THRESHOLD (0.4): drop entirely
            # - Between DISCARD and CONFIDENCE (0.4-0.8): store for manual review
            # - Above CONFIDENCE_THRESHOLD (0.8): store as confirmed action
            if confidence < DISCARD_THRESHOLD:
                logger.info(
                    f"Discarding action: {action.get('action_type')} "
                    f"(confidence={confidence:.2f} < {DISCARD_THRESHOLD})"
                )
                continue

            # Dedup check: skip if this source text already exists
            source_fp = (action.get("source_text") or "").strip().lower()[:100]

            if source_fp and (source_fp in existing_source_fingerprints or source_fp in batch_source_fingerprints):
                logger.info(
                    f"Skipping duplicate action: {action.get('action_type')} "
                    f"(source_text already recorded for application {application_id})"
                )
                continue

            if source_fp:
                batch_source_fingerprints.add(source_fp)
            needs_review = confidence < CONFIDENCE_THRESHOLD

            event_created_at = None
            if email_timestamp:
                try:
                    event_created_at = datetime.fromisoformat(email_timestamp.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    pass

            # Create a timeline event for each qualifying action
            event_created_at = self._parse_iso_date(email_timestamp) or datetime.utcnow()
            
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
                    "confidence": confidence,
                    "source_text": action.get("source_text"),
                    "needs_review": needs_review,
                },
                scheduled_at=self._parse_deadline(action.get("deadline")),
                created_at=event_created_at
            )
            if event_created_at:
                event.created_at = event_created_at
            db.add(event)
            recorded_actions.append({**action, "email_id": email_id})
        
        await db.flush()
            
        logger.info(f"Extracted {len(recorded_actions)} actions for application {application_id}")
        return recorded_actions

    def _parse_deadline(self, deadline_str: Optional[str]) -> Optional[datetime]:
        if not deadline_str:
            return None
        try:
            return datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None

    def _parse_iso_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            # Handle various formats, including space instead of T
            d = date_str.replace('Z', '+00:00')
            if ' ' in d and 'T' not in d:
                return datetime.fromisoformat(d)
            return datetime.fromisoformat(d)
        except (ValueError, TypeError):
            return None
