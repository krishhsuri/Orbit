"""
Digest Email Parser
Detects job digest/newsletter emails and extracts individual job listings
using Groq LLM. Each listing becomes a separate Lead record.

Handles emails like:
- Unstop weekly digest
- Internshala job alerts
- LinkedIn job digest (non-personal)
- Hirist curated lists
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DIGEST_EXTRACT_PROMPT = """You are a job listing extractor. You will receive the body of a job digest email.

Extract ALL individual job listings from the email. For each job, extract:
- company: company name (string)
- role: job title / role name (string)
- stipend: stipend or salary if mentioned, e.g. "INR 25,000/month" or "USD 80k" (string or null)
- location: work location, e.g. "Bengaluru", "Work From Home", "Remote" (string or null)
- job_url: application URL if present (string or null)

Return ONLY a valid JSON array. No explanation, no markdown, no code blocks. Example:
[
  {"company": "Wipro", "role": "Software Development Intern", "stipend": "INR 25,000", "location": "Bengaluru", "job_url": null},
  {"company": "Masters Union", "role": "AI Campus Leader", "stipend": "INR 15,000", "location": "Work From Home", "job_url": null}
]

If the email is NOT a job digest (e.g. it's a personal reply or application status), return an empty array: []

Email body:
{body}
"""


class DigestParser:
    """
    Detects and parses job digest emails using LLM to extract individual listings.
    """

    def __init__(self):
        from app.ml.llm.groq_client import GroqClient
        self.llm = GroqClient()

    def is_digest_email(self, sender: str, subject: str, body: str) -> bool:
        """
        Returns True if this email looks like a job digest (multiple listings).
        Checked before hitting the LLM.
        """
        sender_lower = sender.lower()
        body_lower = body.lower()

        # Known digest senders
        DIGEST_SENDER_SIGNALS = [
            'unstop.news', 'hirist.tech', 'apexearlycareers.com',
            'jobalerts-noreply@', 'jobs-noreply@',
            'mail.internshala', 'resumeworded.com',
        ]
        for signal in DIGEST_SENDER_SIGNALS:
            if signal in sender_lower:
                return True

        # Body structural signals — multiple listings pattern
        # A digest typically has 3+ of: stipend mentions, location mentions, "apply now"
        stipend_count = len(re.findall(r'stipend|salary|lpa|lakhs|inr|usd|\$/month', body_lower))
        location_count = len(re.findall(r'bengaluru|mumbai|delhi|hyderabad|remote|work from home|wfh|pune|chennai', body_lower))
        apply_count = len(re.findall(r'apply now|explore|view job|see more', body_lower))
        company_count = len(re.findall(r'(pvt\. ltd\.|limited|technologies|solutions|services)', body_lower))

        # Heuristic: if 3+ different companies or 3+ stipend mentions → likely a digest
        if stipend_count >= 3 or company_count >= 3 or (location_count >= 3 and apply_count >= 2):
            return True

        return False

    async def extract_leads(
        self,
        email_id: str,
        sender: str,
        body: str,
        email_date,
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to extract individual job listings from a digest email body.

        Returns list of dicts with keys: company, role, stipend, location, job_url, source_email_id, date
        """
        if not body or len(body.strip()) < 100:
            logger.warning(f"[DIGEST] Body too short for email {email_id}, skipping")
            return []

        # Truncate to LLM context limit
        truncated_body = body[:3000]

        try:
            if not self.llm.client:
                logger.warning("[DIGEST] Groq client not initialized, skipping digest extraction")
                return []

            chat_completion = self.llm.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": DIGEST_EXTRACT_PROMPT.format(body=truncated_body)},
                    {"role": "user", "content": "Extract all job listings from the email above."}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=1500,
                # NOTE: Can't use json_object format here because the response is an array not object
            )

            raw_response = chat_completion.choices[0].message.content
            if not raw_response:
                return []

            # Strip any accidental markdown
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                cleaned = re.sub(r'\n?```$', '', cleaned)

            listings = json.loads(cleaned)

            if not isinstance(listings, list):
                logger.warning(f"[DIGEST] LLM returned non-list for email {email_id}")
                return []

            results = []
            for item in listings:
                company = (item.get('company') or '').strip()
                role = (item.get('role') or '').strip()

                if not company or not role:
                    continue  # Skip malformed entries

                results.append({
                    'company': company,
                    'role': role,
                    'stipend': (item.get('stipend') or '').strip() or None,
                    'location': (item.get('location') or '').strip() or None,
                    'job_url': item.get('job_url') or None,
                    'source_email_id': email_id,
                    'recruiter_email': sender,
                    'date': email_date,
                    'is_from_digest': True,
                    'job_site': _infer_job_site(sender),
                })

            logger.info(f"[DIGEST] Extracted {len(results)} leads from email {email_id}")
            return results

        except json.JSONDecodeError as e:
            logger.error(f"[DIGEST] JSON parse error for email {email_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"[DIGEST] Extraction failed for email {email_id}: {e}")
            return []


def _infer_job_site(sender: str) -> Optional[str]:
    """Infer the job platform from the digest sender email."""
    sender_lower = sender.lower()
    if 'unstop' in sender_lower:
        return 'Unstop'
    if 'hirist' in sender_lower:
        return 'Hirist'
    if 'internshala' in sender_lower:
        return 'Internshala'
    if 'linkedin' in sender_lower:
        return 'LinkedIn'
    if 'wellfound' in sender_lower or 'angellist' in sender_lower:
        return 'Wellfound'
    if 'apexearlycareers' in sender_lower:
        return 'Apex Early Careers'
    return None
