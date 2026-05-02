import re
from typing import Dict, Any, Optional

class ColdEmailDetector:
    """
    Lightweight, regex-based classifier for detecting outgoing cold emails.
    Identifies emails where the user is applying for a job directly via email.
    """

    # Strong signals that this is a job application
    SUBJECT_APP_PATTERNS = [
        r'application\s+for',
        r'applying\s+for',
        r'interest\s+in\s+(?:the\s+)?(?:position|role|opening|opportunity)',
        r'job\s+application',
        r'candidature\s+for',
        r'application\s+[-:–]', # Added en-dash
        r'inquiry\s+about',
        r'regarding\s+(?:the\s+)?(?:position|role|opening|opportunity)',
        r'following\s+up\s+on\s+my\s+application',
        r'application\b',
    ]

    # Additional signals to boost confidence
    SUBJECT_BOOST_PATTERNS = [
        r'resume',
        r'cv\b',
        r'cover\s+letter',
        r'portfolio',
        r'intern',
        r'software',
        r'developer',
        r'engineer',
        r'designer',
        r'manager',
        r'analyst',
        r'associate',
        r'quantitative',
    ]

    # Common recruiter/HR email prefixes or domains
    RECIPIENT_HR_PATTERNS = [
        r'^hr@',
        r'^careers@',
        r'^jobs@',
        r'^hiring@',
        r'^recruitment@',
        r'^recruiting@',
        r'^talent@',
        r'^people@',
        r'^apply@',
        r'greenhouse\.io',
        r'lever\.co',
        r'workable\.com',
        r'breezy\.hr',
        r'ashbyhq\.com',
    ]

    # Patterns in the body that indicate a cold application
    BODY_APP_PATTERNS = [
        r'attached\s+(?:my\s+)?(?:resume|cv)',
        r'apply(?:ing)?\s+for\s+(?:the\s+)?(?:position|role|opening)',
        r'interest(?:ed)?\s+in\s+(?:the\s+)?(?:position|role|opening)',
        r'saw\s+the\s+(?:job|opening|posting)',
        r'would\s+love\s+to\s+join',
        r'looking\s+for\s+new\s+opportunities',
        r'reach(?:ing)?\s+out\s+regarding',
        r'expressing\s+interest',
    ]

    # Patterns that indicate this is NOT a new cold email
    NEGATIVE_SUBJECT_PATTERNS = [
        r'^re:',
        r'^fwd:',
        r'out\s+of\s+office',
        r'auto-?reply',
        r'calendar\s+invitation',
        r'accepted:',
        r'declined:',
    ]

    def detect(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a sent email to determine if it's a cold application.
        
        Returns:
            Dict containing:
                - is_cold_email: bool
                - confidence: float
                - company: extracted company name (if any)
                - role: extracted role (if any)
        """
        subject = email_data.get('subject', '').strip()
        recipient = email_data.get('to_address', '').strip()
        body = email_data.get('body_preview', '').strip()

        if not subject and not body:
            return {'is_cold_email': False, 'confidence': 0.0, 'company': None, 'role': None}

        subject_lower = subject.lower()
        recipient_lower = recipient.lower()
        body_lower = body.lower()

        # Step 1: Check negative patterns (skip replies, forwards, etc)
        # Exception: "Following up on my application" is technically a RE: but we might want to track it
        # However, for initial discovery of COLD emails, we usually want the first one.
        for neg_pattern in self.NEGATIVE_SUBJECT_PATTERNS:
            if re.search(neg_pattern, subject_lower):
                return {'is_cold_email': False, 'confidence': 0.0, 'company': None, 'role': None}

        # Step 2: Check for strong application intent in subject or body
        has_app_intent_subject = any(re.search(pat, subject_lower) for pat in self.SUBJECT_APP_PATTERNS)
        has_app_intent_body = any(re.search(pat, body_lower) for pat in self.BODY_APP_PATTERNS)
        
        if not (has_app_intent_subject or has_app_intent_body):
            # If no direct intent, check if it's an HR recipient + boost keywords
            is_hr_recipient = any(re.search(pat, recipient_lower) for pat in self.RECIPIENT_HR_PATTERNS)
            has_boost = any(re.search(pat, subject_lower) for pat in self.SUBJECT_BOOST_PATTERNS)
            if not (is_hr_recipient and has_boost):
                return {'is_cold_email': False, 'confidence': 0.0, 'company': None, 'role': None}

        # Base confidence
        confidence = 0.50
        if has_app_intent_subject: confidence += 0.20
        if has_app_intent_body: confidence += 0.15

        # Step 3: Boost confidence based on recipient and additional keywords
        is_hr_recipient = any(re.search(pat, recipient_lower) for pat in self.RECIPIENT_HR_PATTERNS)
        if is_hr_recipient:
            confidence += 0.20
            
        boost_count = sum(1 for pat in self.SUBJECT_BOOST_PATTERNS if re.search(pat, subject_lower))
        confidence += min(0.15, boost_count * 0.05)

        # Step 4: Extract Company and Role using simple heuristics
        company, role = self._extract_company_and_role(subject)
        
        # If not in subject, maybe try body? (Heuristic: "at [Company]")
        if not company:
            company_match = re.search(r'(?i)(?:at|with|for)\s+([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+){0,2})', body)
            if company_match:
                company = company_match.group(1).strip()

        # Only classify as cold email if confidence is high enough
        is_cold = confidence >= 0.55

        return {
            'is_cold_email': is_cold,
            'confidence': min(0.99, confidence),
            'company': company,
            'role': role
        }

    def _extract_company_and_role(self, subject: str) -> tuple[Optional[str], Optional[str]]:
        """
        Attempt to extract company and role from standard application subjects.
        e.g., 'Application for SDE Intern at Acme Corp'
        """
        company = None
        role = None

        # Common separator formats
        # "Application for [Role] at [Company]"
        # "Application: [Role] - [Company]"
        
        # Try finding role BEFORE "at | - | | | –" and company AFTER
        at_match = re.search(r'(?i)(?:application\s+for\s+)?(.*?)\s+(?:at|@|-|\||–)\s+(.*)', subject)
        if at_match:
            role = at_match.group(1).strip()
            # Clean up role (remove "Application for" if it was captured)
            role = re.sub(r'(?i)^application\s+for\s+', '', role).strip()
            company = at_match.group(2).strip()
            return company, role

        # Try colon separator
        colon_match = re.search(r'(?i)(?:application\s+for\s+)?(.*?)\s*:\s*(.*)', subject)
        if colon_match:
            role = colon_match.group(1).strip()
            role = re.sub(r'(?i)^application\s+for\s+', '', role).strip()
            company = colon_match.group(2).strip()
            return company, role

        # Fallback 1: Just extract role if "application for [Role]"
        for pat in self.SUBJECT_APP_PATTERNS:
            role_match = re.search(f'(?i){pat}\\s+([^\\-\\|@]+)', subject)
            if role_match:
                extracted = role_match.group(1).strip()
                # Clean up dangling words
                extracted = re.sub(r'(?i)\b(?:at|for|with)\b.*?$', '', extracted).strip()
                if 3 <= len(extracted) <= 50:
                    role = extracted
                break

        return company, role
