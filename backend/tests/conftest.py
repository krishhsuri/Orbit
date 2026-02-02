"""
Pytest configuration and shared fixtures for Orbit backend tests.
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4
from typing import List, Dict, Any


# Sample application data for testing
@pytest.fixture
def sample_applications() -> List[Dict[str, Any]]:
    """Generate sample application data for testing."""
    now = datetime.utcnow()
    
    return [
        {
            'id': str(uuid4()),
            'company_name': 'Google',
            'role_title': 'Software Engineer',
            'status': 'interview',
            'source': 'referral',
            'applied_date': (now - timedelta(days=10)).date(),
            'status_updated_at': now - timedelta(days=5),
        },
        {
            'id': str(uuid4()),
            'company_name': 'Meta',
            'role_title': 'Frontend Developer',
            'status': 'applied',
            'source': 'direct',
            'applied_date': (now - timedelta(days=20)).date(),
            'status_updated_at': now - timedelta(days=20),
        },
        {
            'id': str(uuid4()),
            'company_name': 'Amazon',
            'role_title': 'SDE Intern',
            'status': 'rejected',
            'source': 'direct',
            'applied_date': (now - timedelta(days=15)).date(),
            'status_updated_at': now - timedelta(days=7),
        },
        {
            'id': str(uuid4()),
            'company_name': 'Microsoft',
            'role_title': 'PM Intern',
            'status': 'ghosted',
            'source': 'linkedin',
            'applied_date': (now - timedelta(days=30)).date(),
            'status_updated_at': now - timedelta(days=30),
        },
        {
            'id': str(uuid4()),
            'company_name': 'Apple',
            'role_title': 'iOS Developer',
            'status': 'offer',
            'source': 'referral',
            'applied_date': (now - timedelta(days=25)).date(),
            'status_updated_at': now - timedelta(days=2),
        },
    ]


@pytest.fixture
def sample_emails() -> List[Dict[str, Any]]:
    """Generate sample email data for testing."""
    return [
        {
            'id': 'email_1',
            'from_address': 'recruiter@google.com',
            'from_name': 'John from Google',
            'subject': 'Interview Request - Software Engineer',
            'body_preview': 'We would like to schedule an interview...',
        },
        {
            'id': 'email_2',
            'from_address': 'noreply@greenhouse.io',
            'from_name': 'Meta Careers',
            'subject': 'Thanks for applying to Meta',
            'body_preview': 'We received your application for Frontend Developer...',
        },
        {
            'id': 'email_3',
            'from_address': 'hr@amazon.com',
            'from_name': 'Amazon HR',
            'subject': 'Update on your Amazon application',
            'body_preview': 'Unfortunately, we will not be moving forward...',
        },
        {
            'id': 'email_4',
            'from_address': 'john@gmail.com',
            'from_name': 'John Doe',
            'subject': 'Random personal email',
            'body_preview': 'Hey, how are you doing?',
        },
    ]


@pytest.fixture
def old_applied_application() -> Dict[str, Any]:
    """Application that's been in 'applied' status for over 14 days."""
    now = datetime.utcnow()
    return {
        'id': str(uuid4()),
        'company_name': 'Stale Company',
        'role_title': 'Developer',
        'status': 'applied',
        'source': 'direct',
        'applied_date': (now - timedelta(days=20)).date(),
        'status_updated_at': now - timedelta(days=16),
    }


@pytest.fixture
def recent_applied_application() -> Dict[str, Any]:
    """Application that's been in 'applied' status for less than 14 days."""
    now = datetime.utcnow()
    return {
        'id': str(uuid4()),
        'company_name': 'Recent Company',
        'role_title': 'Engineer',
        'status': 'applied',
        'source': 'linkedin',
        'applied_date': (now - timedelta(days=7)).date(),
        'status_updated_at': now - timedelta(days=7),
    }
