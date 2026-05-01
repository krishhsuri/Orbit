import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.ml.llm.groq_client import GroqClient
from app.config import get_settings
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
        
        result = await self.llm.extract_actions_from_email(
            subject=email_subject,
            body=email_body,
            company=company,
            role=role,
            email_timestamp=email_timestamp,
        )
        
        if not result or not result.get("is_job_related"):
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

        # Build a set of (action_type, source_text_fingerprint) for fast lookup
        existing_fingerprints: set[tuple[str, str]] = set()
        for evt in existing_events:
            d = evt.data or {}
            src = (d.get("source_text") or "").strip().lower()[:80]
            existing_fingerprints.add((d.get("action_type", ""), src))

        # Track within-batch duplicates too
        batch_fingerprints: set[tuple[str, str]] = set()

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

            # Dedup check: skip if this action already exists
            action_type = action.get("action_type", "unknown")
            source_fp = (action.get("source_text") or "").strip().lower()[:80]
            fingerprint = (action_type, source_fp)

            if fingerprint in existing_fingerprints or fingerprint in batch_fingerprints:
                logger.info(
                    f"Skipping duplicate action: {action_type} "
                    f"(source_text already recorded for application {application_id})"
                )
                continue

            batch_fingerprints.add(fingerprint)
            needs_review = confidence < CONFIDENCE_THRESHOLD

            # Create a timeline event for each qualifying action
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
                scheduled_at=self._parse_deadline(action.get("deadline"))
            )
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
