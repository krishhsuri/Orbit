"""
Layer 2: NLP Analyzer
Extracts entities and job-related signals using spaCy.
Runs in ~10-50ms per email.
"""

import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Job-related keywords with weights
JOB_KEYWORDS = {
    'application': 2,
    'interview': 3,
    'offer': 3,
    'position': 2,
    'role': 2,
    'candidate': 2,
    'hiring': 2,
    'recruiter': 2,
    'opportunity': 1,
    'resume': 2,
    'cv': 2,
    'assessment': 2,
    'coding challenge': 3,
    'technical interview': 3,
    'phone screen': 2,
    'onsite': 2,
    'next steps': 2,
    'applied': 2,
    'submitted': 1,
    'congratulations': 2,
    'unfortunately': 2,
    'regret': 2,
    'rejected': 3,
    'offer letter': 3,
    'compensation': 2,
    'salary': 2,
}

# Email type detection patterns
EMAIL_TYPE_PATTERNS = {
    'application_received': [
        r'application.*received',
        r'thank you for applying',
        r'we have received your application',
        r'application submitted',
        r'successfully applied',
    ],
    'interview': [
        r'interview.*schedule',
        r'schedule.*interview',
        r'phone screen',
        r'technical interview',
        r'onsite interview',
        r'video interview',
        r'next round',
        r'meet.*team',
    ],
    'offer': [
        r'offer letter',
        r'job offer',
        r'pleased to offer',
        r'extend.*offer',
        r'congratulations.*offer',
        r'compensation package',
    ],
    'rejection': [
        r'unfortunately',
        r'regret to inform',
        r'not moving forward',
        r'decided not to proceed',
        r'other candidates',
        r'not selected',
    ],
    'assessment': [
        r'coding challenge',
        r'coding test',
        r'assessment',
        r'hackerrank',
        r'codility',
        r'take-home',
    ],
}


class NLPAnalyzer:
    """
    Layer 2: NLP Analyzer
    Extracts entities and job-related signals using spaCy.
    """
    
    def __init__(self):
        self._nlp = None

    def _get_nlp(self):
        """Lazy load spaCy model."""
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load('en_core_web_sm')
                logger.info("spaCy model loaded successfully")
            except OSError:
                logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
                self._nlp = None
        return self._nlp

    def analyze_email(self, email: dict) -> Dict[str, Any]:
        """
        Analyze email using NLP to extract entities and signals.
        
        Args:
            email: dict with 'subject', 'body_preview', 'from_address', 'from_name'
        
        Returns:
            Dict with entities, keyword_score, detected_type, etc.
        """
        subject = email.get('subject', '')
        body = email.get('body_preview', '')[:1000]  # Limit body length
        from_addr = email.get('from_address', '')
        from_name = email.get('from_name', '')
        
        text = f"{subject} {body}"
        text_lower = text.lower()
        
        result = {
            'entities': {
                'organizations': [],
                'persons': [],
                'dates': [],
            },
            'keyword_score': 0,
            'detected_type': None,
            'type_confidence': 0,
            'sender_signals': {},
            'is_likely_job_related': False,
            # Add company/role/relevance_score keys to match AIParser expectations
            'company': None,
            'role': None,
            'relevance_score': 0.0
        }
        
        # Extract entities with spaCy
        nlp = self._get_nlp()
        if nlp:
            try:
                doc = nlp(text[:2000])  # Limit for performance
                for ent in doc.ents:
                    if ent.label_ == 'ORG':
                        result['entities']['organizations'].append(ent.text)
                    elif ent.label_ == 'PERSON':
                        result['entities']['persons'].append(ent.text)
                    elif ent.label_ in ('DATE', 'TIME'):
                        result['entities']['dates'].append(ent.text)
            except Exception as e:
                logger.error(f"spaCy processing failed: {e}")
        
        # Calculate keyword score
        for keyword, weight in JOB_KEYWORDS.items():
            if keyword in text_lower:
                result['keyword_score'] += weight
        
        # Detect email type using patterns
        for email_type, patterns in EMAIL_TYPE_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    # Pattern length indicates confidence
                    confidence = min(0.95, 0.7 + len(pattern) / 100)
                    if confidence > result['type_confidence']:
                        result['detected_type'] = email_type
                        result['type_confidence'] = confidence
                    break
        
        # Analyze sender
        result['sender_signals'] = self.analyze_sender(from_addr, from_name)
        
        # Determine if likely job-related
        result['is_likely_job_related'] = (
            result['keyword_score'] >= 3 or
            result['detected_type'] is not None or
            result['sender_signals'].get('is_recruiter', False) or
            result['sender_signals'].get('is_job_platform', False)
        )
        
        # Calculate a normalized relevance score for AIParser
        result['relevance_score'] = min(1.0, result['keyword_score'] / 10.0)
        if result['is_likely_job_related']:
            result['relevance_score'] = max(result['relevance_score'], 0.5)
            
        # Try to guess company and role
        result['company'] = self.extract_company_from_email(from_addr)
        # If company not from domain, try first ORG
        if not result['company'] and result['entities']['organizations']:
            result['company'] = result['entities']['organizations'][0]
            
        # Use first PERSON as role? No, likely not. Role extraction is hard without specialized NER.
        # We leave role None for now or try to match JOB_KEYWORDS
        
        return result


    def analyze_sender(self, email_addr: str, name: str) -> Dict[str, bool]:
        """Analyze sender to detect recruiter/HR signals."""
        email_lower = email_addr.lower()
        name_lower = (name or '').lower()
        
        recruiter_patterns = ['recruiter', 'recruiting', 'talent', 'hr', 'hiring', 'careers', 'people']
        is_recruiter = any(p in email_lower or p in name_lower for p in recruiter_patterns)
        
        job_platforms = [
            'greenhouse.io', 'lever.co', 'workable.com', 'ashbyhq.com',
            'smartrecruiters.com', 'myworkdayjobs.com', 'taleo.net',
            'icims.com', 'jobvite.com', 'workday.com', 'bamboohr.com'
        ]
        is_job_platform = any(p in email_lower for p in job_platforms)
        
        big_tech = ['@google.com', '@meta.com', '@amazon.com', '@microsoft.com', '@apple.com']
        is_big_tech = any(p in email_lower for p in big_tech)
        
        is_automated = 'noreply' in email_lower or 'donotreply' in email_lower or 'no-reply' in email_lower
        
        return {
            'is_recruiter': is_recruiter,
            'is_job_platform': is_job_platform,
            'is_big_tech': is_big_tech,
            'is_automated': is_automated,
        }


    def extract_company_from_email(self, email_addr: str) -> Optional[str]:
        """Extract company name from email domain."""
        try:
            domain = email_addr.split('@')[1]
            company = domain.split('.')[0]
            
            # Filter common providers
            common_providers = ['gmail', 'yahoo', 'outlook', 'hotmail', 'icloud', 'proton', 'aol']
            if company.lower() in common_providers:
                return None
            
            # Filter job platforms
            job_platforms = ['greenhouse', 'lever', 'workable', 'ashby', 'icims', 'taleo']
            if company.lower() in job_platforms:
                return None
            
            return company.title()
        except Exception:
            return None
