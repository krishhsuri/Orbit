from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.ml.filters.quick_filter import QuickFilter
from app.ml.analyzers.nlp_analyzer import NLPAnalyzer
from app.ml.classifiers.email_classifier import EmailClassifier
from app.ml.llm.groq_client import GroqClient
from app.config import get_settings

logger = logging.getLogger(__name__)

class AIParser:
    def __init__(self):
        self.quick_filter = QuickFilter()
        self.nlp = NLPAnalyzer()
        self.classifier = EmailClassifier()
        settings = get_settings()
        self.llm = GroqClient(api_key=settings.groq_api_key)

    async def parse_job_email(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process an email through the ML pipeline.
        Returns parsed data or None if filtered out/irrelevant.
        """
        subject = email_data.get('subject', '')
        sender = email_data.get('from_address', '')
        snippet = email_data.get('snippet', '')
        body_preview = email_data.get('body_preview', '')

        print(f"[PARSER] Processing: {subject[:50]}")

        # 1. Layer 1: Quick Filter (Fastest)
        # Check if it's potentially job-related
        if not self.quick_filter.initial_filter(sender, subject):
            print(f"[PARSER] BLOCKED by QuickFilter: {subject[:40]}")
            return None

        print(f"[PARSER] Passed QuickFilter")

        # 2. Layer 2: NLP Analysis (Fast, Local)
        # Extract entities and get relevance score
        nlp_result = self.nlp.analyze_email(email_data)
        print(f"[PARSER] NLP: relevance={nlp_result.get('relevance_score')}, company={nlp_result.get('company')}")
        
        if nlp_result['relevance_score'] < 0.3:
            pass  # Don't filter here, let classifier decide

        # 3. Layer 3: Pattern Classification (Fast, Local)
        # Classify email type (interview, offer, rejection, etc.)
        classification = self.classifier.classify(email_data, nlp_result)
        print(f"[PARSER] Classification: {classification}")
        
        # 4. Decision Logic
        # If we have high confidence from local models, use them
        confidence = classification.get('confidence', 0.0)
        category = classification.get('category', 'unknown')

        parsed_result = {
            'company': nlp_result.get('company'),
            'role': nlp_result.get('role'),
            'status': category,
            'job_url': None,
            'confidence': confidence,
            'source': 'local'
        }

        # If ambiguous or high value, use LLM (Slower, Cost)
        if confidence < 0.7 or (not parsed_result['company']):
            print(f"[PARSER] Trying LLM extraction (confidence={confidence}, company={parsed_result['company']})")
            try:
                llm_result = await self.llm.extract_job_details(body_preview)
                if llm_result:
                    parsed_result.update(llm_result)
                    parsed_result['source'] = 'llm'
                    parsed_result['confidence'] = max(confidence, 0.8)
                    print(f"[PARSER] LLM result: {llm_result}")
            except Exception as e:
                print(f"[PARSER] LLM failed: {e}")

        # Final check: Is it actually a job application update?
        if not parsed_result.get('company') and parsed_result.get('confidence', 0) < 0.5:
            print(f"[PARSER] FILTERED OUT: no company and confidence={parsed_result.get('confidence')}")
            return None
        
        print(f"[PARSER] SUCCESS: company={parsed_result.get('company')}, confidence={parsed_result.get('confidence')}")
        return parsed_result
