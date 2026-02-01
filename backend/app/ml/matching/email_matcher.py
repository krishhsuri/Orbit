"""
Email Matcher - Links emails to existing applications
Uses company name fuzzy matching and sender domain analysis.
"""

from typing import Optional, Tuple, List, Dict, Any
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)


class EmailMatcher:
    """
    Matches incoming emails to existing job applications.
    Uses multiple strategies:
    1. Exact company name match
    2. Fuzzy company name match
    3. Sender domain matching
    """
    
    # Minimum fuzzy match ratio to consider a match
    FUZZY_THRESHOLD = 0.75
    
    # Common email providers to ignore for domain matching
    IGNORED_DOMAINS = {
        'gmail', 'yahoo', 'outlook', 'hotmail', 'icloud',
        'protonmail', 'aol', 'mail', 'zoho', 'yandex'
    }
    
    def __init__(self):
        pass
    
    def match(
        self,
        email_data: Dict[str, Any],
        applications: List[Dict[str, Any]],
        nlp_result: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], float]:
        """
        Match an email to an existing application.
        
        Args:
            email_data: Email dict with 'from_address', 'subject', 'body_preview'
            applications: List of application dicts with 'id', 'company_name'
            nlp_result: Optional NLP analysis result with extracted entities
            
        Returns:
            Tuple of (application_id, confidence) or (None, 0.0)
        """
        if not applications:
            return None, 0.0
        
        # Get company names mentioned in email
        email_companies = self._extract_companies_from_email(email_data, nlp_result)
        
        if not email_companies:
            logger.debug("No companies extracted from email")
            return None, 0.0
        
        best_match_id = None
        best_score = 0.0
        
        for app in applications:
            app_company = app.get('company_name', '').lower().strip()
            app_id = app.get('id')
            
            if not app_company or not app_id:
                continue
            
            for email_company in email_companies:
                # Strategy 1: Exact match
                if app_company == email_company:
                    logger.info(f"Exact match: {email_company} -> {app_id}")
                    return str(app_id), 0.95
                
                # Strategy 2: Fuzzy match
                ratio = self._fuzzy_match(app_company, email_company)
                if ratio > best_score and ratio >= self.FUZZY_THRESHOLD:
                    best_score = ratio
                    best_match_id = app_id
        
        if best_match_id:
            logger.info(f"Fuzzy match: score={best_score:.2f} -> {best_match_id}")
            return str(best_match_id), best_score
        
        return None, 0.0
    
    def _extract_companies_from_email(
        self,
        email_data: Dict[str, Any],
        nlp_result: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Extract possible company names from email."""
        companies = set()
        
        # 1. From NLP result (organizations detected by spaCy)
        if nlp_result:
            orgs = nlp_result.get('entities', {}).get('organizations', [])
            for org in orgs:
                companies.add(org.lower().strip())
            
            # Also check the extracted company field
            if nlp_result.get('company'):
                companies.add(nlp_result['company'].lower().strip())
        
        # 2. From sender email domain
        from_address = email_data.get('from_address', '')
        domain_company = self._extract_company_from_domain(from_address)
        if domain_company:
            companies.add(domain_company.lower())
        
        # 3. From sender name (e.g., "John from Google")
        from_name = email_data.get('from_name', '')
        if 'from ' in from_name.lower():
            parts = from_name.lower().split('from ')
            if len(parts) > 1:
                company = parts[1].strip()
                # Clean up common suffixes
                company = re.sub(r'\s*(inc|llc|corp|ltd|limited)\.?$', '', company, flags=re.I)
                if company and len(company) > 2:
                    companies.add(company)
        
        return list(companies)
    
    def _extract_company_from_domain(self, email_address: str) -> Optional[str]:
        """Extract company name from email domain."""
        try:
            if not email_address or '@' not in email_address:
                return None
            
            domain = email_address.split('@')[1].lower()
            # Get first part of domain (e.g., 'google' from 'google.com')
            company = domain.split('.')[0]
            
            # Filter out common email providers
            if company in self.IGNORED_DOMAINS:
                return None
            
            # Filter out common ATS/HR systems
            ats_domains = {'greenhouse', 'lever', 'workday', 'icims', 'taleo', 'jobvite'}
            if company in ats_domains:
                return None
            
            return company.title()  # Capitalize
            
        except Exception:
            return None
    
    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Calculate fuzzy match ratio between two strings."""
        return SequenceMatcher(None, s1, s2).ratio()


# Singleton instance for easy import
email_matcher = EmailMatcher()
