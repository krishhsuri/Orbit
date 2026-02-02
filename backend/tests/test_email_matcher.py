"""
Tests for EmailMatcher - matches emails to existing applications.
"""

import pytest
from app.ml.matching.email_matcher import EmailMatcher


@pytest.fixture
def matcher():
    return EmailMatcher()


@pytest.fixture
def google_application():
    return {
        'id': 'app-google-123',
        'company_name': 'Google',
    }


@pytest.fixture
def meta_application():
    return {
        'id': 'app-meta-456',
        'company_name': 'Meta',
    }


class TestEmailMatcher:
    """Tests for EmailMatcher class."""
    
    def test_exact_company_match(self, matcher, google_application, sample_applications):
        """Should match email from google.com to Google application."""
        email = {
            'from_address': 'recruiter@google.com',
            'from_name': 'Google Recruiter',
            'subject': 'Interview Request',
            'body_preview': 'We would like to schedule...',
        }
        nlp_result = {
            'entities': {'organizations': ['Google']},
            'company': 'Google',
        }
        
        applications = [google_application]
        app_id, confidence = matcher.match(email, applications, nlp_result)
        
        assert app_id == 'app-google-123'
        assert confidence >= 0.9
    
    def test_fuzzy_match(self, matcher, google_application):
        """Should match slightly misspelled company names."""
        email = {
            'from_address': 'hr@alphabet.com',
            'from_name': 'HR Team',
            'subject': 'Update from Googl',  # Typo
            'body_preview': 'Thanks for your interest in Googl...',
        }
        nlp_result = {
            'entities': {'organizations': ['Googl']},
            'company': 'Googl',
        }
        
        applications = [google_application]
        app_id, confidence = matcher.match(email, applications, nlp_result)
        
        # Should match with lower confidence due to fuzzy match
        assert app_id == 'app-google-123'
        assert 0.75 <= confidence < 0.95
    
    def test_domain_match(self, matcher, meta_application):
        """Should extract company from email domain."""
        email = {
            'from_address': 'careers@meta.com',
            'from_name': 'Meta Careers',
            'subject': 'Application Update',
            'body_preview': 'Thank you for applying...',
        }
        nlp_result = {
            'entities': {'organizations': []},
            'company': None,
        }
        
        applications = [meta_application]
        app_id, confidence = matcher.match(email, applications, nlp_result)
        
        assert app_id == 'app-meta-456'
        assert confidence >= 0.75
    
    def test_no_match_returns_none(self, matcher, google_application):
        """Should return None when no match found."""
        email = {
            'from_address': 'hr@netflix.com',
            'from_name': 'Netflix HR',
            'subject': 'Application Status',
            'body_preview': 'Netflix update...',
        }
        nlp_result = {
            'entities': {'organizations': ['Netflix']},
            'company': 'Netflix',
        }
        
        applications = [google_application]  # Only Google, not Netflix
        app_id, confidence = matcher.match(email, applications, nlp_result)
        
        assert app_id is None
        assert confidence == 0.0
    
    def test_ignores_common_email_providers(self, matcher, google_application):
        """Should not match gmail.com, yahoo.com, etc."""
        email = {
            'from_address': 'john@gmail.com',
            'from_name': 'John Doe',
            'subject': 'Random email',
            'body_preview': 'Hey...',
        }
        nlp_result = {
            'entities': {'organizations': []},
            'company': None,
        }
        
        applications = [google_application]
        app_id, confidence = matcher.match(email, applications, nlp_result)
        
        # Gmail domain should be ignored, no match
        assert app_id is None
        assert confidence == 0.0
    
    def test_empty_applications_returns_none(self, matcher):
        """Should return None when no applications exist."""
        email = {
            'from_address': 'hr@google.com',
            'from_name': 'Google HR',
            'subject': 'Interview',
            'body_preview': '...',
        }
        nlp_result = {'entities': {'organizations': ['Google']}, 'company': 'Google'}
        
        app_id, confidence = matcher.match(email, [], nlp_result)
        
        assert app_id is None
        assert confidence == 0.0
