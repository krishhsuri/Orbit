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
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except ImportError:
                logger.warning("Groq library not installed")

    async def extract_job_details(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured job details from text using Groq LLM.
        """
        if not self.client:
            return None

        try:
            chat_completion = self.client.chat.completions.create(
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
            chat_completion = self.client.chat.completions.create(
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
            logger.error(f"LLM analysis failed: {e}")
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
            chat_completion = self.client.chat.completions.create(
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

