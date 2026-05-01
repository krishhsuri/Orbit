"""
LLM Client (Groq)
Handles email analysis using Groq LLM for job application tracking.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Prompt for extracting job details from email
EXTRACT_PROMPT = """You are an AI that extracts job application information from emails.
Extract the following from the email text if present:
- company: The company name
- role: The job title/role
- job_url: Any application or job listing URL

Return JSON only: {"company": "...", "role": "...", "job_url": "..."}
Use null for fields not found."""

# Prompt for deciding what to do with an email
ANALYZE_PROMPT = """You are an AI that helps track job applications. Analyze this email and decide what to do.

Your task:
1. Determine if this email is related to a job application (interview invites, application confirmations, rejections, assessments, offers, etc.)
2. If job-related, extract company name, role, and current status
3. Decide: "add_to_tracker" for job-related emails, "discard" for non-job emails

Status should be one of: applied, screening, interview, oa (online assessment), offer, rejected

IMPORTANT RULES:
- Newsletters, marketing emails, and promotional content should ALWAYS be discarded
- Emails listing multiple candidates (e.g. "list of shortlisted students") should be discarded unless they are specifically addressed to the recipient
- Job platform notification emails like "X new jobs match your profile" are NOT applications — discard them
- Only track emails about a SPECIFIC application the user submitted or a SPECIFIC interview/offer

Here are examples:

Example 1 - TRACK (application confirmation):
Subject: "Thank you for applying to Software Engineer at Google"
→ {"action": "add_to_tracker", "company": "Google", "role": "Software Engineer", "status": "applied", "reason": "Application confirmation email"}

Example 2 - TRACK (interview invite):
Subject: "Interview Invitation - Data Analyst Position"
Body: "We'd like to schedule a technical interview for the Data Analyst role at Meta..."
→ {"action": "add_to_tracker", "company": "Meta", "role": "Data Analyst", "status": "interview", "reason": "Interview invitation"}

Example 3 - DISCARD (newsletter):
Subject: "This week's top jobs in tech"
Body: "Check out 50 new openings matching your profile..."
→ {"action": "discard", "company": null, "role": null, "status": null, "reason": "Newsletter/digest, not a specific application"}

Example 4 - DISCARD (marketing from job platform):
Subject: "Companies are looking for people like you!"
Body: "Your profile was viewed by 5 recruiters. Upgrade to Premium..."
→ {"action": "discard", "company": null, "role": null, "status": null, "reason": "Marketing/promotional email from job platform"}

Example 5 - DISCARD (mass candidate list):
Subject: "List of shortlisted candidates for Summer Internship 2025"
Body: "Please find below the names of selected aspirants..."
→ {"action": "discard", "company": null, "role": null, "status": null, "reason": "Mass email listing multiple candidates, not a personal application update"}

Return JSON only:
{
  "action": "add_to_tracker" or "discard",
  "company": "company name or null",
  "role": "job role or null", 
  "status": "applied/screening/interview/oa/offer/rejected or null",
  "reason": "brief reason for decision"
}"""


class GroqClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        if self.api_key:
            try:
                from groq import AsyncGroq
                self.client = AsyncGroq(api_key=self.api_key)
            except ImportError:
                logger.warning("Groq library not installed")

    async def extract_job_details(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured job details from text using Groq LLM.
        """
        if not self.client:
            return None

        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": EXTRACT_PROMPT},
                    {"role": "user", "content": f"Email text:\n\n{text[:1500]}"}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            
            result_json = chat_completion.choices[0].message.content
            return json.loads(result_json)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    async def _call_with_retry(self, **kwargs):
        """Wrapper around chat.completions.create with rate limit retry logic."""
        import asyncio
        import re
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await self.client.chat.completions.create(**kwargs)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate limit" in err_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = 10.0
                        match = re.search(r'Please try again in ([0-9.]+)s', err_str)
                        if match:
                            wait_time = float(match.group(1)) + 1.0
                        else:
                            wait_time = (2 ** attempt) * 5.0
                        logger.warning(f"[GROQ] Rate limit hit. Retrying in {wait_time:.2f}s (Attempt {attempt+1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                        continue
                logger.error(f"[GROQ] API call failed on attempt {attempt+1}: {e}")
                if attempt == max_retries - 1:
                    raise e

    async def analyze_email_for_tracking(self, subject: str, body: str) -> Optional[Dict[str, Any]]:
        """
        Analyze an email and decide whether to add it to the job tracker.
        
        Returns:
            Dict with action ('add_to_tracker' or 'discard'), company, role, status, reason
        """
        if not self.client:
            logger.warning("Groq client not initialized")
            return None

        email_text = f"Subject: {subject}\n\nBody:\n{body[:2000]}"
        
        try:
            chat_completion = await self._call_with_retry(
                messages=[
                    {"role": "system", "content": ANALYZE_PROMPT},
                    {"role": "user", "content": email_text}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
            
            result_json = chat_completion.choices[0].message.content
            result = json.loads(result_json)
            
            logger.info(f"[GROQ] Decision: {result.get('action')}")
            return result
            
        except Exception as e:
            logger.error(f"LLM analysis failed completely: {e}")
            return None

    async def extract_note_from_email(self, subject: str, body: str) -> Optional[Dict[str, Any]]:
        """
        Extract key information from an email for populating notes.
        
        Returns:
            Dict with key_dates, requirements, action_items, salary_info, summary
        """
        if not self.client:
            logger.warning("Groq client not initialized")
            return None

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

        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": email_text}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            
            result_json = chat_completion.choices[0].message.content
            result = json.loads(result_json)
            
            logger.debug("[GROQ] Note extracted successfully")
            return result
            
        except Exception as e:
            logger.error(f"LLM note extraction failed: {e}")
            return None

    async def extract_actions_from_email(
        self, subject: str, body: str,
        company: str | None = None, role: str | None = None,
        email_timestamp: str | None = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract explicit/implicit applicant actions from job-related emails.
        Accepts optional metadata (company, role, timestamp) for better context.
        """
        if not self.client:
            return None

        prompt = """You are an AI Agent that extracts actionable tasks from job-related emails.
Your job is to find actions that a COMPANY or RECRUITER is asking the APPLICANT to perform.

CRITICAL: This email may be part of a thread with multiple messages. You MUST distinguish between:
- Messages FROM the company/recruiter TO the applicant → THESE contain actions to extract
- Messages FROM the applicant TO the company → IGNORE these completely, they are NOT actions

How to tell the difference:
- If the text says "I wanted to apply", "I came across your role", "Resume attached", "Happy to connect", 
  "I'll have it ready" → This is the APPLICANT speaking. DO NOT extract this as an action.
- If the text says "Please complete", "We'd like to schedule", "You have been shortlisted",
  "Find attached your assignment" → This is the COMPANY speaking. Extract this.

Supported Action Types:
- online_assessment: The COMPANY asks the applicant to complete an online test or assessment.
- interview_scheduling: The COMPANY asks the applicant to schedule, confirm, or attend an interview.
- document_upload: The COMPANY asks the applicant to submit documents.
- coding_test: The COMPANY asks the applicant to complete a coding challenge or take-home assignment.
- general_response_required: The COMPANY asks the applicant to reply or confirm something.

Rules:
1. ONLY extract actions where the COMPANY/RECRUITER is requesting something from the applicant.
2. NEVER extract the applicant's own statements, promises, or self-introductions as actions.
3. If the email is just a confirmation ("Thank you for applying", "We received your application"), return actions: [].
4. If "Feel free to contact us for questions" is the only ask, return actions: [] — this is a courtesy line, not a real action.
5. Maximum 2 actions per email. Pick the most important ones.
6. If no deadline is present, infer urgency:
   - "high": words like "ASAP", "immediately", "within 24 hours"
   - "medium": "this week", "at your earliest convenience"
   - "low": general update with a soft ask
7. Confidence scores:
   - 0.9-1.0: Explicit, unambiguous action from the company
   - 0.7-0.89: Likely action but slightly ambiguous
   - 0.5-0.69: Possible action, needs interpretation
   - Below 0.5: Weak signal, likely false positive
8. source_text MUST be an exact excerpt from the COMPANY'S message, not the applicant's.
9. If the email is not job-related, return is_job_related: false.

Return JSON only:
{
  "actions": [
    {
      "action_type": "online_assessment | interview_scheduling | document_upload | coding_test | general_response_required",
      "deadline": "ISO-8601 timestamp | null",
      "urgency": "low | medium | high",
      "confidence": 0.0 to 1.0,
      "source_text": "exact excerpt from the COMPANY's message",
      "reasoning": "short explanation"
    }
  ],
  "is_job_related": true
}"""

        # Build user message with optional metadata context
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
        email_text = '\n'.join(parts)

        try:
            chat_completion = await self._call_with_retry(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": email_text}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            
            result_json = chat_completion.choices[0].message.content
            return json.loads(result_json)
            
        except Exception as e:
            logger.error(f"LLM action extraction failed completely: {e}")
            return None

    async def generate_follow_up_draft(self, company: str, role: str, last_interaction_days: int, context: str = "", source: Optional[str] = None) -> Optional[str]:
        """
        Generate a professional follow-up email draft.
        """
        if not self.client:
            return None

        cold_email_instruction = ""
        if source == "cold_email":
            cold_email_instruction = "\n- Note: The initial interaction was a cold email outreach, not a standard job portal application. The follow-up should reflect this (e.g., 'following up on my previous email regarding...')."

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

        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a professional career coach."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=500,
            )
            
            return chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM follow-up drafting failed: {e}")
            return None

