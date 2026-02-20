from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.ml.filters.quick_filter import QuickFilter
from app.ml.analyzers.nlp_analyzer import NLPAnalyzer
from app.ml.classifiers.email_classifier import EmailClassifier
from app.ml.llm.groq_client import GroqClient
from app.config import get_settings

logger = logging.getLogger(__name__)

# Map LLM decisions to Application model statuses
STATUS_MAPPING = {
    'applied': 'applied',
    'application_received': 'applied',
    'rejected': 'rejected',
    'application_rejected': 'rejected',
    'interview': 'interview',
    'interview_invite': 'interview',
    'assessment': 'oa',
    'assessment_invite': 'oa',
    'oa': 'oa',
    'offer': 'offer',
    'offer_letter': 'offer',
    'screening': 'screening',
}


class AIParser:
    """
    Two-stage AI Parser:
    1. quick_parse - Fast local ML for initial email intake (no LLM)
    2. process_with_llm - Deep LLM analysis for final decision
    """
    
    def __init__(self):
        self.quick_filter = QuickFilter()
        self.nlp = NLPAnalyzer()
        self.classifier = EmailClassifier()
        settings = get_settings()
        self.llm = GroqClient(api_key=settings.groq_api_key)

    async def quick_parse(self, email_data: Dict[str, Any], user_email: str = None) -> Optional[Dict[str, Any]]:
        """
        Stage 1: Fast local ML parsing for email intake.
        Returns basic parsed data for display in emails section.
        NO LLM calls here - this is just for quick visibility.
        
        Args:
            email_data: Email dict with subject, from_address, body_preview, etc.
            user_email: Optional user's email for multi-candidate email verification
        """
        subject = email_data.get('subject', '')
        sender = email_data.get('from_address', '')
        snippet = email_data.get('body_preview', '')

        print(f"[QUICK_PARSE] Processing: {subject[:50]}")

        # Layer 0: Learned Filter (self-learning from user feedback)
        from app.ml.classifiers.learned_filter import learned_filter, CONFIDENCE_THRESHOLD
        if learned_filter.is_ready:
            label, confidence = learned_filter.predict(subject, snippet, sender)
            if label and confidence >= CONFIDENCE_THRESHOLD:
                if label == "negative":
                    print(f"[QUICK_PARSE] BLOCKED by LearnedFilter ({confidence:.0%}): {subject[:40]}")
                    return None
                else:
                    print(f"[QUICK_PARSE] LearnedFilter says POSITIVE ({confidence:.0%}): {subject[:40]}")

        # Layer 1: Quick Filter (blocks obvious spam)
        if not self.quick_filter.initial_filter(sender, subject):
            print(f"[QUICK_PARSE] BLOCKED by QuickFilter: {subject[:40]}")
            return None

        # Layer 2: NLP Analysis (extract entities)
        nlp_result = self.nlp.analyze_email(email_data)
        
        # Layer 3: Pattern Classification (pass user_email for multi-candidate detection)
        classification = self.classifier.classify(email_data, nlp_result, user_email=user_email)
        
        confidence = classification.get('confidence', 0.0)
        category = classification.get('category', 'unknown')

        print(f"[QUICK_PARSE] Result: {category} ({confidence:.0%}), company={nlp_result.get('company')}")

        return {
            'company': nlp_result.get('company'),
            'role': nlp_result.get('role'),
            'status': category,
            'job_url': None,
            'confidence': confidence,
            'source': 'local'
        }

    async def process_with_llm(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 2: Deep LLM analysis to decide what to do with the email.
        
        Returns:
            Dict with:
            - action: 'add_to_tracker' | 'discard'
            - company: extracted company name
            - role: extracted role
            - status: application status (applied, interview, rejected, etc.)
            - job_url: if found
            - reason: why this decision was made
        """
        subject = email_data.get('subject', '')
        snippet = email_data.get('snippet', '')
        body_preview = email_data.get('body_preview', snippet)

        print(f"[LLM_PROCESS] Analyzing: {subject[:50]}")

        try:
            # Send to Groq for intelligent analysis
            llm_result = await self.llm.analyze_email_for_tracking(
                subject=subject,
                body=body_preview
            )
            
            if llm_result:
                # Map the status to our Application model
                raw_status = llm_result.get('status', 'applied')
                mapped_status = STATUS_MAPPING.get(raw_status.lower(), 'applied')
                llm_result['status'] = mapped_status
                
                print(f"[LLM_PROCESS] Decision: {llm_result.get('action')} - {llm_result.get('company')}")
                return llm_result
                
        except Exception as e:
            print(f"[LLM_PROCESS] Error: {e}")
        
        # Fallback if LLM fails
        return {
            'action': 'discard',
            'reason': 'LLM analysis failed',
            'company': None,
            'role': None,
            'status': 'applied'
        }

    async def batch_process_with_llm(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple emails with LLM.
        Returns list of results with email_id and decision.
        """
        results = []
        for email_data in emails:
            result = await self.process_with_llm(email_data)
            result['email_id'] = email_data.get('id')
            results.append(result)
        return results
