"""
Layer 1: Quick Filter
Fast filtering to eliminate spam, newsletters, and promotional emails.
Runs in ~0.1ms per email, filters out ~80% of inbox.
"""

from typing import Set, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Domains/patterns that indicate PURE spam (not job platforms)
BLOCKED_SENDER_PATTERNS: Set[str] = {
    'newsletter', 'marketing', 'promo', 'deals', 'offers', 
    'digest', 'weekly-digest', 'recommendation', 'news',
    'unsubscribe', 'mailer-daemon',
}

# Promotional subject patterns (ONLY pure spam, not job alerts)
PROMO_SUBJECT_PATTERNS = [
    'unsubscribe',
    'newsletter',
    'weekly digest',
    'sale',
    'discount',
    '% off',
    'limited time',
    'act now',
    'free trial',
    'click here',
]

# Known JOB PLATFORMS - these should ALWAYS pass through
JOB_PLATFORM_SENDERS = [
    'linkedin.com', 'indeed.com', 'glassdoor.com', 'monster.com',
    'ziprecruiter.com', 'greenhouse.io', 'lever.co', 'workable.com',
    'ashbyhq.com', 'smartrecruiters.com', 'myworkdayjobs.com',
    'taleo.net', 'icims.com', 'jobvite.com', 'workday.com',
    'wellfound.com', 'angellist.com', 'angel.co', 'hired.com',
    'triplebyte.com', 'otta.com', 'huntr.co', 'builtin.com',
    'hire.', 'careers.', 'jobs.', 'recruiting.', 'talent.',
]


class QuickFilter:
    """
    Layer 1: Quick Filter
    Fast filtering to eliminate spam, newsletters, and promotional emails.
    """
    
    def initial_filter(self, sender: str, subject: str) -> bool:
        """
        Returns True if email should be processed further.
        Returns False if email is likely spam/promotional.
        """
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        
        logger.debug(f"QuickFilter checking: sender='{sender}', subject='{subject}'")
        
        # FIRST: Check if it's from a known job platform - ALWAYS ALLOW
        for platform in JOB_PLATFORM_SENDERS:
            if platform in sender_lower:
                logger.info(f"QuickFilter PASSED (job platform): {sender}")
                return True
        
        # Check for positive job signals in subject - ALLOW these
        job_signals = [
            'application', 'applied', 'interview', 'offer',
            'position', 'role', 'opportunity', 'candidate',
            'assessment', 'coding', 'next steps', 'thank you for',
            'regarding your', 'following up', 'recruiter',
            'hiring', 'job', 'career', 'resume', 'cv',
            'shortlisted', 'profile', 'vacancy', 'opening',
            'talent', 'screening', 'onboarding', 'background check',
            'hackerrank', 'codesignal', 'codility', 'leetcode',
            'technical', 'phone screen', 'video call', 'zoom',
            'calendly', 'schedule', 'availability', 'meet',
            'congratulations', 'unfortunately', 'regret',
            'selected', 'moving forward', 'proceed',
        ]
        for signal in job_signals:
            if signal in subject_lower:
                logger.info(f"QuickFilter PASSED (job signal in subject): {subject}")
                return True
        
        # Check for blocked patterns in sender address (spam senders)
        for pattern in BLOCKED_SENDER_PATTERNS:
            if pattern in sender_lower:
                logger.debug(f"QuickFilter BLOCKED (spam sender pattern '{pattern}'): {sender}")
                return False
        
        # Check subject for promotional patterns
        for pattern in PROMO_SUBJECT_PATTERNS:
            if pattern in subject_lower:
                logger.debug(f"QuickFilter BLOCKED (promo subject pattern '{pattern}'): {subject}")
                return False
                
        # Default: ALLOW through (let NLP/classifier decide)
        logger.info(f"QuickFilter PASSED (default allow): {sender} - {subject}")
        return True

    def is_potential_job_email(self, sender: str, subject: str) -> bool:
        """
        Quick positive check - does this look like it COULD be job-related?
        """
        sender = sender.lower()
        subject = subject.lower()
        
        # Positive signals in subject
        job_signals = [
            'application', 'applied', 'interview', 'offer',
            'position', 'role', 'opportunity', 'candidate',
            'assessment', 'coding', 'next steps', 'thank you for',
            'regarding your', 'following up', 'recruiter',
        ]
        
        for signal in job_signals:
            if signal in subject:
                return True
        
        # Positive signals in sender
        sender_signals = ['recruit', 'talent', 'hiring', 'careers', 'hr@', 'jobs@']
        for signal in sender_signals:
            if signal in sender:
                return True
        
        # Known job platforms
        for platform in JOB_PLATFORM_SENDERS:
            if platform in sender:
                return True
        
        return False
