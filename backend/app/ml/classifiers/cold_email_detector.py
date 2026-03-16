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
        r'application\s+[-:]',
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
    ]

    # Common recruiter/HR email prefixes or domains
    RECIPIENT_HR_PATTERNS = [
        r'^hr@',
        r'^careers@',
        r'^jobs@',
        r'^hiring@',
        r'^recruitment@',
        r'^talent@',
        r'greenhouse\.io',
        r'lever\.co',
        r'workable\.com',
    ]

    # Patterns that indicate this is NOT a new cold email
    NEGATIVE_SUBJECT_PATTERNS = [
        r'^re:',
        r'^fwd:',
        r'out\s+of\s+office',
        r'auto-?reply',
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

        if not subject:
            return {'is_cold_email': False, 'confidence': 0.0, 'company': None, 'role': None}

        subject_lower = subject.lower()
        recipient_lower = recipient.lower()

        # Step 1: Check negative patterns (skip replies, forwards, etc)
        for neg_pattern in self.NEGATIVE_SUBJECT_PATTERNS:
            if re.search(neg_pattern, subject_lower):
                return {'is_cold_email': False, 'confidence': 0.0, 'company': None, 'role': None}

        # Step 2: Check for strong application intent in subject
        has_app_intent = any(re.search(pat, subject_lower) for pat in self.SUBJECT_APP_PATTERNS)
        
        if not has_app_intent:
            return {'is_cold_email': False, 'confidence': 0.0, 'company': None, 'role': None}

        # Base confidence if intent is found
        confidence = 0.60

        # Step 3: Boost confidence based on recipient and additional keywords
        is_hr_recipient = any(re.search(pat, recipient_lower) for pat in self.RECIPIENT_HR_PATTERNS)
        if is_hr_recipient:
            confidence += 0.25
            
        boost_count = sum(1 for pat in self.SUBJECT_BOOST_PATTERNS if re.search(pat, subject_lower))
        confidence += min(0.15, boost_count * 0.05)

        # Step 4: Extract Company and Role using simple heuristics
        company, role = self._extract_company_and_role(subject)

        # Only classify as cold email if confidence is high enough
        is_cold = confidence >= 0.60

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
        
        # Try finding role BEFORE "at | - | |" and company AFTER
        at_match = re.search(r'(?i)application\s+for\s+(.*?)\s+(?:at|@|-|\|)\s+(.*)', subject)
        if at_match:
            role = at_match.group(1).strip()
            company = at_match.group(2).strip()
            return company, role

        # Try colon separator
        colon_match = re.search(r'(?i)application(?:\s+for)?\s*:\s*(.*?)(?:\s+(?:at|@|-|\|)\s+(.*))', subject)
        if colon_match:
            role = colon_match.group(1).strip()
            if colon_match.group(2):
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
