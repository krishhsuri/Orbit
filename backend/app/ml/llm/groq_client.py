"""
Domain-specific Groq LLM helpers built on app.llm.client.LLMClient.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from app.llm.client import LLMClient, ModelTier
from app.llm.errors import LLMSchemaError, LLMUnavailable

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are an AI that extracts job application information from emails.
Extract the following from the email text if present:
- company: The company name
- role: The job title/role
- job_url: Any application or job listing URL

Return JSON only: {"company": "...", "role": "...", "job_url": "..."}
Use null for fields not found."""

ANALYZE_PROMPT = """You are an AI that helps track job applications. Analyze this email and decide what to do.

Your task:
1. Determine if this email is related to a job application (interview invites, application confirmations, rejections, assessments, offers, OR outbound cold emails where the candidate is applying/sending their resume).
2. If job-related, extract company name, role, and current status
3. Decide: "add_to_tracker" for job-related emails, "discard" for non-job emails

Status should be one of: applied, screening, interview, oa (online assessment), offer, rejected

IMPORTANT RULES:
- Newsletters, marketing emails, and promotional content should ALWAYS be discarded
- Emails listing multiple candidates (e.g. "list of shortlisted students") should be discarded unless they are specifically addressed to the recipient
- Job platform notification emails like "X new jobs match your profile" are NOT applications — discard them
- Only track emails about a SPECIFIC application the user submitted or a SPECIFIC interview/offer
- Outbound cold emails (where the sender is expressing interest, applying, or attaching their resume to recruiters) MUST be tracked with status "applied".

Return JSON only:
{
  "action": "add_to_tracker" or "discard",
  "company": "company name or null",
  "role": "job role or null", 
  "status": "applied/screening/interview/oa/offer/rejected or null",
  "reason": "brief reason for decision"
}"""


class JobDetails(BaseModel):
    company: str | None = None
    role: str | None = None
    job_url: str | None = None


class EmailTrackingDecision(BaseModel):
    action: str
    company: str | None = None
    role: str | None = None
    status: str | None = None
    reason: str | None = None


class NoteExtraction(BaseModel):
    key_dates: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    salary_info: str | None = None
    contact_info: str | None = None
    summary: str | None = None


class ExtractedAction(BaseModel):
    action_type: str
    deadline: str | None = None
    urgency: str | None = None
    confidence: float = 0.0
    source_text: str | None = None
    reasoning: str | None = None


class ActionExtractionResult(BaseModel):
    actions: list[ExtractedAction] = Field(default_factory=list)
    is_job_related: bool = True


class GroqClient:
    """Backward-compatible facade over LLMClient for existing services."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._llm: LLMClient | None = None
        if api_key:
            self._llm = LLMClient(api_key=api_key)

    @property
    def client(self):
        """Legacy accessor used by digest_parser — returns underlying AsyncGroq or None."""
        if self._llm and self._llm._client:
            return self._llm._client
        return None

    def _require_llm(self) -> LLMClient:
        if not self._llm or not self._llm.is_configured:
            raise LLMUnavailable("Groq API key not configured")
        return self._llm

    async def extract_job_details(self, text: str) -> dict[str, Any]:
        llm = self._require_llm()
        result = await llm.structured_output(
            [
                {"role": "system", "content": EXTRACT_PROMPT},
                {"role": "user", "content": f"Email text:\n\n{text[:1500]}"},
            ],
            JobDetails,
            purpose="extract_job_details",
            tier=ModelTier.FAST,
            max_tokens=200,
        )
        return result.model_dump()

    async def analyze_email_for_tracking(self, subject: str, body: str) -> dict[str, Any]:
        llm = self._require_llm()
        email_text = f"Subject: {subject}\n\nBody:\n{body[:2000]}"
        result = await llm.structured_output(
            [
                {"role": "system", "content": ANALYZE_PROMPT},
                {"role": "user", "content": email_text},
            ],
            EmailTrackingDecision,
            purpose="analyze_email_for_tracking",
            tier=ModelTier.FAST,
            max_tokens=300,
        )
        payload = result.model_dump()
        logger.info("[GROQ] Decision: %s", payload.get("action"))
        return payload

    async def extract_note_from_email(self, subject: str, body: str) -> dict[str, Any]:
        llm = self._require_llm()
        prompt = """You are an AI that extracts key information from job-related emails for note-taking.

Extract the following information if present:
- key_dates: Any important dates mentioned (deadlines, interview dates, etc.)
- requirements: Any requirements or qualifications mentioned
- action_items: Things the recipient needs to do
- salary_info: Any compensation/salary details mentioned
- contact_info: Recruiter name, email, or phone if mentioned
- summary: A 1-2 sentence summary of the email

Return JSON only:
{
  "key_dates": ["date1", "date2"] or [],
  "requirements": ["req1", "req2"] or [],
  "action_items": ["action1", "action2"] or [],
  "salary_info": "salary details or null",
  "contact_info": "contact details or null",
  "summary": "brief summary"
}"""
        email_text = f"Subject: {subject}\n\nBody:\n{body[:2500]}"
        result = await llm.structured_output(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": email_text},
            ],
            NoteExtraction,
            purpose="extract_note_from_email",
            tier=ModelTier.FAST,
            max_tokens=500,
        )
        logger.debug("[GROQ] Note extracted successfully")
        return result.model_dump()

    async def extract_actions_from_email(
        self,
        subject: str,
        body: str,
        company: str | None = None,
        role: str | None = None,
        email_timestamp: str | None = None,
    ) -> dict[str, Any]:
        llm = self._require_llm()
        from datetime import datetime

        current_date_str = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""You are an AI Agent that extracts actionable tasks from job-related emails.
Your job is to find actions that a COMPANY or RECRUITER is asking the APPLICANT to perform.

CRITICAL: This email may be part of a thread with multiple messages. You MUST distinguish between:
- Messages FROM the company/recruiter TO the applicant → THESE contain actions to extract
- Messages FROM the applicant TO the company → IGNORE these completely, they are NOT actions

Supported Action Types:
- online_assessment
- interview_scheduling
- document_upload
- coding_test
- general_response_required

Rules:
1. ONLY extract actions where the COMPANY/RECRUITER is requesting something from the applicant.
2. NEVER extract the applicant's own statements as actions.
3. If the email is just a confirmation, return actions: [].
4. Maximum 2 actions per email.
5. The current date is {current_date_str}. Do not extract actions whose deadlines are already in the past.
6. If the email is not job-related, return is_job_related: false.

Return JSON only:
{{
  "actions": [
    {{
      "action_type": "online_assessment | interview_scheduling | document_upload | coding_test | general_response_required",
      "deadline": "ISO-8601 timestamp | null",
      "urgency": "low | medium | high",
      "confidence": 0.0 to 1.0,
      "source_text": "exact excerpt from the COMPANY's message",
      "reasoning": "short explanation"
    }}
  ],
  "is_job_related": true
}}"""

        parts = [f"Subject: {subject}"]
        if company or role:
            meta = []
            if company:
                meta.append(f"Company: {company}")
            if role:
                meta.append(f"Role: {role}")
            if email_timestamp:
                meta.append(f"Email Date: {email_timestamp}")
            parts.append(f"Metadata: {', '.join(meta)}")
        parts.append(f"\nBody:\n{body[:3000]}")
        email_text = "\n".join(parts)

        result = await llm.structured_output(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": email_text},
            ],
            ActionExtractionResult,
            purpose="extract_actions_from_email",
            tier=ModelTier.FAST,
            max_tokens=800,
        )
        return result.model_dump()

    async def generate_follow_up_draft(
        self,
        company: str,
        role: str,
        last_interaction_days: int,
        context: str = "",
        source: str | None = None,
    ) -> str:
        llm = self._require_llm()
        cold_email_instruction = ""
        if source == "cold_email":
            cold_email_instruction = (
                "\n- Note: The initial interaction was a cold email outreach. "
                "The follow-up should reflect this."
            )

        prompt = f"""You are an AI assistant helping a job seeker follow up on an application.
Context:
- Company: {company}
- Role: {role}
- Days since last contact: {last_interaction_days}
- Additional Context: {context}{cold_email_instruction}

Requirements:
- Personalized, polite, and concise.
- Professional tone.
- No assumptions or pressure.
- Focus on expressing continued interest and asking for an update.

Return ONLY the email draft text."""

        return await llm.complete_text(
            [
                {"role": "system", "content": "You are a professional career coach."},
                {"role": "user", "content": prompt},
            ],
            purpose="generate_follow_up_draft",
            tier=ModelTier.REASONING,
            temperature=0.7,
            max_tokens=500,
        )

    async def complete_raw_json_array(
        self,
        messages: list[dict[str, str]],
        *,
        tier: ModelTier = ModelTier.FAST,
        max_tokens: int = 1500,
    ) -> list[dict[str, Any]]:
        """For digest parsing where the model returns a JSON array, not an object."""
        llm = self._require_llm()
        response = await llm.chat(
            messages,
            purpose="digest_extract_leads",
            tier=tier,
            temperature=0.1,
            max_tokens=max_tokens,
        )
        raw = response.content
        if not raw:
            raise LLMSchemaError("LLM returned empty content for JSON array")

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)

        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            raise LLMSchemaError(
                f"Expected JSON array, got {type(parsed).__name__}", raw_content=raw
            )
        return parsed
